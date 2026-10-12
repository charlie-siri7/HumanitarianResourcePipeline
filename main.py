import os
import time
from dotenv import load_dotenv
from supabase import create_client
from clients.hrsa_client import HRSAClient, clean_text, extract_street_number_and_name
from models.schema import EnrichedResource
from pipeline.load import batch_upsert

load_dotenv()

TARGET_TABLE = "new_resources"

def run_enrichment():
    supabase = create_client(
        os.getenv("SUPABASE_URL"), 
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    
    hrsa = HRSAClient()
    registry = hrsa.get_all_health_centers()
    print(f"Loaded {len(registry['by_street'])} address keys and {len(registry['by_name'])} name keys across the US.")

    batch_size = 500
    offset = 0

    while True:
        # Pull candidate rows directly from the staging table
        query = supabase.table(TARGET_TABLE) \
            .select("id, name, address, city, phone, website, hours, description") \
            .ilike("description", "%HRSA%") \
            .neq("updated_by", "hrsa_enrichment_v1") \
            .range(offset, offset + batch_size - 1) \
            .execute()
        
        records = query.data
        if not records:
            print(f"No remaining candidate records found in {TARGET_TABLE}. Enrichment complete.")
            break

        updates = []
        for row in records:
            addr = row.get("address") or ""
            name = row.get("name") or ""

            # Check street match first, then clinic name
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
                if raw_hours is not None and str(raw_hours).strip() != "" and str(raw_hours).lower() != "nan":
                    try:
                        hrs_num = float(raw_hours)
                        hours_val = f"Mon-Fri: ~{int(hrs_num)} hrs/week (call for daily schedule)"
                    except ValueError:
                        hours_val = str(raw_hours).strip()
                else:
                    hours_val = "Mon-Fri: 8:00 AM - 5:00 PM"

                updates.append(EnrichedResource(
                    id=row["id"],  # Preserves exact primary key
                    name=row["name"],
                    phone=row.get("phone") or (str(match.get("Site_Telephone_Number")) if match.get("Site_Telephone_Number") else None),
                    website=row.get("website") or (str(match.get("Site_Web_URL")) if match.get("Site_Web_URL") else None),
                    description=service_desc,
                    hours=hours_val
                ))

        if updates:
            print(f"Updating {len(updates)} records for batch {offset} to {offset + len(records)}...")
            batch_upsert(supabase, updates, table_name=TARGET_TABLE)

        offset += batch_size
        time.sleep(0.2)

if __name__ == "__main__":
    run_enrichment()