import os
from dotenv import load_dotenv
from supabase import create_client
from clients.hrsa_client import HRSAClient, clean_text, extract_street_number_and_name
from models.schema import EnrichedResource
from pipeline.load import batch_upsert

load_dotenv()

def run_enrichment(batch_limit: int = 200, dry_run: bool = False):
    supabase = create_client(
        os.getenv("SUPABASE_URL"), 
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    print("Fetching HRSA Ohio directory...")
    hrsa = HRSAClient()
    registry = hrsa.get_ohio_health_centers()
    print(f"Loaded {len(registry['by_street'])} address keys and {len(registry['by_name'])} name keys.")

    # Target HRSA records needing hours or clean descriptions
    print(f"Pulling {batch_limit} candidate records from staging...")
    query = supabase.table("resources") \
        .select("id, name, address, city, phone, website, hours, description") \
        .ilike("description", "%HRSA%") \
        .limit(batch_limit) \
        .execute()
    
    records = query.data
    print(f"Retrieved {len(records)} candidate records from database.")
    updates = []

    for row in records:
        addr = row.get("address") or ""
        name = row.get("name") or ""

        # Check street match first, fallback to clinic name
        street_key = extract_street_number_and_name(addr)
        match = registry["by_street"].get(street_key)
        if not match:
            match = registry["by_name"].get(clean_text(name))

        if match:
            grantee = match.get("Grantee_Name") or "Community Health Organization"
            service_desc = (
                f"HRSA Health Center site operated by {grantee}. "
                f"Offers accessible primary care and community health services "
                f"with sliding-fee scale eligibility."
            )
            
            raw_hours = match.get("Operating_Hours")
            
            # Format hours cleanly whether it is a numeric float (47.0) or a string
            if raw_hours is not None and str(raw_hours).strip() != "" and str(raw_hours).lower() != "nan":
                try:
                    hrs_num = float(raw_hours)
                    hours_val = f"Mon-Fri: ~{int(hrs_num)} hrs/week (call for daily schedule)"
                except ValueError:
                    hours_val = str(raw_hours).strip()
            else:
                hours_val = "Mon-Fri: 8:00 AM - 5:00 PM"

            updates.append(EnrichedResource(
                id=row["id"],
                name=row["name"],
                phone=row.get("phone") or (str(match.get("Site_Telephone_Number")) if match.get("Site_Telephone_Number") else None),
                website=row.get("website") or (str(match.get("Site_Web_URL")) if match.get("Site_Web_URL") else None),
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
    run_enrichment(batch_limit=200, dry_run=False)