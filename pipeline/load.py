from typing import List
from supabase import Client
from models.schema import EnrichedResource

def batch_upsert(client: Client, items: List[EnrichedResource], table_name: str = "new_resources") -> None:
    if not items:
        return
    payload = [item.model_dump(exclude_unset=True) for item in items]
    client.table(table_name).upsert(payload).execute()