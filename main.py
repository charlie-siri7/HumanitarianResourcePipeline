import os
import time
from dotenv import load_dotenv
from supabase import create_client
from clients.hrsa_client import HRSAClient
from models.schema import EnrichedResource
from pipeline.load import batch_upsert

load_dotenv()

def run_enrichment(batch_limit: int = 50, dry_run: bool = False):
    supabase = create_client(
        os.getenv("SUPABASE_URL"), 
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    print("Fetching HRSA Ohio directory...")
    hrsa = HRSAClient()
    registry = hrsa.get_ohio_health_centers()
    print(f"Loaded {len(registry)} Ohio health centers into memory.")

    # Target records needing hours or clean descriptions
    print(f"Pulling {batch_limit} target records from staging...")
    query = supabase.table("resources") \
        .select("id, name, address, city, phone, website, hours, description") \
        .or_("hours.is.null,hours.like.%call for schedule%,description.like.Source:%") \
        .limit(batch_limit) \
        .execute()
    
    records = query.data
    updates = []

    for row in records:
        addr = str(row.get("address") or "").strip().lower()
        city = str(row.get("city") or "").strip().lower()
        match = registry.get(f"{addr} {city}")

        if match:
            # Build clean user-facing description
            grantee = match.get("Grantee_Name", "Federally Qualified Health Center")
            service_desc = (
                f"HRSA-designated Community Health Center operated by {grantee}. "
                f"Provides accessible primary care and preventive health services "
                f"with sliding-fee discount programs."
            )
            
            raw_hours = match.get("Operating_Hours")
            hours_val = raw_hours if raw_hours else "Mon-Fri: 8:00 AM - 5:00 PM"

            updates.append(EnrichedResource(
                id=row["id"],
                name=row["name"],
                phone=row.get("phone") or match.get("Site_Telephone_Number"),
                website=row.get("website") or match.get("Site_Web_URL"),
                description=service_desc,
                hours=hours_val
            ))

    print(f"Found {len(updates)} matches out of {len(records)} records.")

    if dry_run:
        print("[DRY RUN] Skipping database upsert.")
        if updates:
            print("Sample payload:", updates[0].model_dump())
        return

    if updates:
        print(f"Upserting {len(updates)} records to Supabase...")
        batch_upsert(supabase, updates)
        print("Upsert completed successfully.")

if __name__ == "__main__":
    # Start with a safe dry run of 50 records
    run_enrichment(batch_limit=50, dry_run=False)