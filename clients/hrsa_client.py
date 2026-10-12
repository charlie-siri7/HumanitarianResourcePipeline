import os
import re
import pandas as pd
from typing import Dict, Any

def clean_text(text: str) -> str:
    if not text or pd.isna(text):
        return ""
    # Lowercase and strip punctuation/extra whitespace
    text = re.sub(r"[^\w\s]", " ", str(text).lower())
    return " ".join(text.split())

def extract_street_number_and_name(addr: str) -> str:
    cleaned = clean_text(addr)
    # Extract leading digits and first street word (e.g., "600 w 3rd" -> "600 3rd")
    tokens = [t for t in cleaned.split() if t not in ("w", "e", "n", "s", "st", "ave", "rd", "blvd", "dr", "suite", "ste")]
    return " ".join(tokens[:3]) if tokens else cleaned

class HRSAClient:
    LOCAL_CSV = "data/hrsa_all_sites.csv"
    CACHE_OHIO = "hrsa_ohio_sites.csv"

    def get_ohio_health_centers(self) -> Dict[str, Any]:
        if os.path.exists(self.CACHE_OHIO):
            df_oh = pd.read_csv(self.CACHE_OHIO, low_memory=False)
        else:
            try:
                df = pd.read_csv(self.LOCAL_CSV, encoding="utf-8", low_memory=False)
            except UnicodeDecodeError:
                df = pd.read_csv(self.LOCAL_CSV, encoding="cp1252", low_memory=False)

            col_map = {col: col.strip().lower().replace(" ", "_") for col in df.columns}
            df.rename(columns=col_map, inplace=True)
            state_col = next((c for c in df.columns if "state" in c), "site_state_abbreviation")
            df_oh = df[df[state_col].astype(str).str.strip().str.upper() == "OH"].copy()
            df_oh.to_csv(self.CACHE_OHIO, index=False)

        cols = list(df_oh.columns)
        name_col = next((c for c in cols if "site_name" in c or "name" in c), cols[0])
        addr_col = next((c for c in cols if "address" in c or "street" in c), None)
        phone_col = next((c for c in cols if "phone" in c or "tel" in c), None)
        web_col = next((c for c in cols if "web" in c or "url" in c), None)
        grantee_col = next((c for c in cols if "grantee" in c or "org" in c), None)
        hours_col = next((c for c in cols if "hour" in c or "schedule" in c), None)

        registry = {"by_street": {}, "by_name": {}}
        for _, row in df_oh.iterrows():
            record = {
                "Site_Name": row[name_col] if pd.notnull(row[name_col]) else None,
                "Site_Telephone_Number": row[phone_col] if phone_col and pd.notnull(row[phone_col]) else None,
                "Site_Web_URL": row[web_col] if web_col and pd.notnull(row[web_col]) else None,
                "Grantee_Name": row[grantee_col] if grantee_col and pd.notnull(row[grantee_col]) else None,
                "Operating_Hours": row[hours_col] if hours_col and pd.notnull(row[hours_col]) else None,
            }

            raw_addr = str(row[addr_col]) if addr_col and pd.notnull(row[addr_col]) else ""
            raw_name = str(row[name_col]) if pd.notnull(row[name_col]) else ""

            # Primary key: street token
            street_key = extract_street_number_and_name(raw_addr)
            if street_key:
                registry["by_street"][street_key] = record

            # Secondary key: cleaned facility name
            name_key = clean_text(raw_name)
            if name_key:
                registry["by_name"][name_key] = record

        return registry