import os
import pandas as pd
from typing import Dict, Any

class HRSAClient:
    LOCAL_CSV = "data/hrsa_all_sites.csv"
    CACHE_OHIO = "hrsa_ohio_sites.csv"

    def get_ohio_health_centers(self) -> Dict[str, Any]:
        # 1. Use pre-filtered Ohio cache if already generated
        if os.path.exists(self.CACHE_OHIO):
            print(f"Loading cached Ohio sites from {self.CACHE_OHIO}...")
            df_oh = pd.read_csv(self.CACHE_OHIO, low_memory=False)
        else:
            if not os.path.exists(self.LOCAL_CSV):
                raise FileNotFoundError(
                    f"'{self.LOCAL_CSV}' not found in the project root. "
                    "Download the CSV from data.hrsa.gov, place it in "
                    "C:\\Users\\charl\\Desktop\\ResourcePipeline\\data, and rename it to 'hrsa_all_sites.csv'."
                )

            print(f"Reading {self.LOCAL_CSV}...")
            try:
                df = pd.read_csv(self.LOCAL_CSV, encoding="utf-8", low_memory=False)
            except UnicodeDecodeError:
                df = pd.read_csv(self.LOCAL_CSV, encoding="cp1252", low_memory=False)

            # Normalize column names for flexible matching
            col_map = {col: col.strip().lower().replace(" ", "_") for col in df.columns}
            df.rename(columns=col_map, inplace=True)

            # Locate State column
            state_col = next((c for c in df.columns if "state" in c), None)
            if not state_col:
                raise KeyError(f"Could not identify a State column. Available columns: {list(df.columns)}")

            # Filter for Ohio records
            df_oh = df[df[state_col].astype(str).str.strip().str.upper() == "OH"].copy()
            df_oh.to_csv(self.CACHE_OHIO, index=False)
            print(f"Filtered {len(df_oh)} Ohio sites and cached to {self.CACHE_OHIO}.")

        # Identify attribute columns dynamically
        cols = list(df_oh.columns)
        name_col = next((c for c in cols if "site_name" in c or "name" in c), cols[0])
        addr_col = next((c for c in cols if "address" in c or "street" in c), None)
        city_col = next((c for c in cols if "city" in c), None)
        phone_col = next((c for c in cols if "phone" in c or "tel" in c), None)
        web_col = next((c for c in cols if "web" in c or "url" in c), None)
        grantee_col = next((c for c in cols if "grantee" in c or "org" in c), None)
        hours_col = next((c for c in cols if "hour" in c or "schedule" in c), None)

        cache = {}
        for _, row in df_oh.iterrows():
            addr = str(row[addr_col]).strip().lower() if addr_col and pd.notnull(row[addr_col]) else ""
            city = str(row[city_col]).strip().lower() if city_col and pd.notnull(row[city_col]) else ""

            if addr and city:
                key = f"{addr} {city}"
                cache[key] = {
                    "Site_Name": row[name_col] if pd.notnull(row[name_col]) else None,
                    "Site_Telephone_Number": row[phone_col] if phone_col and pd.notnull(row[phone_col]) else None,
                    "Site_Web_URL": row[web_col] if web_col and pd.notnull(row[web_col]) else None,
                    "Grantee_Name": row[grantee_col] if grantee_col and pd.notnull(row[grantee_col]) else None,
                    "Operating_Hours": row[hours_col] if hours_col and pd.notnull(row[hours_col]) else None,
                }

        return cache