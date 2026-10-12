import os
import re
import pandas as pd
from typing import Dict, Any

def clean_text(text: str) -> str:
    if not text or pd.isna(text):
        return ""
    text = re.sub(r"[^\w\s]", " ", str(text).lower())
    return " ".join(text.split())

def extract_street_number_and_name(addr: str) -> str:
    cleaned = clean_text(addr)
    tokens = [t for t in cleaned.split() if t not in ("w", "e", "n", "s", "st", "ave", "rd", "blvd", "dr", "suite", "ste")]
    return " ".join(tokens[:3]) if tokens else cleaned

class HRSAClient:
    LOCAL_CSV = "data/hrsa_all_sites.csv"

    def get_all_health_centers(self) -> Dict[str, Any]:
        # Fall back to root folder if data/ subfolder is not used
        csv_path = self.LOCAL_CSV if os.path.exists(self.LOCAL_CSV) else "hrsa_all_sites.csv"
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Could not find HRSA CSV at '{self.LOCAL_CSV}' or 'hrsa_all_sites.csv'")

        print(f"Indexing nationwide HRSA sites from {csv_path}...")
        try:
            df = pd.read_csv(csv_path, encoding="utf-8", low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, encoding="cp1252", low_memory=False)

        col_map = {col: col.strip().lower().replace(" ", "_") for col in df.columns}
        df.rename(columns=col_map, inplace=True)

        cols = list(df.columns)
        name_col = next((c for c in cols if "site_name" in c or "name" in c), cols[0])
        addr_col = next((c for c in cols if "address" in c or "street" in c), None)
        phone_col = next((c for c in cols if "phone" in c or "tel" in c), None)
        web_col = next((c for c in cols if "web" in c or "url" in c), None)
        grantee_col = next((c for c in cols if "grantee" in c or "org" in c), None)
        hours_col = next((c for c in cols if "hour" in c or "schedule" in c), None)

        registry = {"by_street": {}, "by_name": {}}
        for _, row in df.iterrows():
            record = {
                "Site_Name": row[name_col] if pd.notnull(row[name_col]) else None,
                "Site_Telephone_Number": row[phone_col] if phone_col and pd.notnull(row[phone_col]) else None,
                "Site_Web_URL": row[web_col] if web_col and pd.notnull(row[web_col]) else None,
                "Grantee_Name": row[grantee_col] if grantee_col and pd.notnull(row[grantee_col]) else None,
                "Operating_Hours": row[hours_col] if hours_col and pd.notnull(row[hours_col]) else None,
            }

            raw_addr = str(row[addr_col]) if addr_col and pd.notnull(row[addr_col]) else ""
            raw_name = str(row[name_col]) if pd.notnull(row[name_col]) else ""

            street_key = extract_street_number_and_name(raw_addr)
            if street_key:
                registry["by_street"][street_key] = record

            name_key = clean_text(raw_name)
            if name_key:
                registry["by_name"][name_key] = record

        return registry