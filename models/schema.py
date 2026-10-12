from pydantic import BaseModel
from typing import Optional

class EnrichedResource(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    hours: Optional[str] = None
    description: Optional[str] = None
    updated_at: str = "now()"
    updated_by: str = "hrsa_enrichment_v1"