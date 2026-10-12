from pydantic import BaseModel, field_validator
from typing import Optional, Any

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

    @field_validator("hours", "phone", "website", mode="before")
    @classmethod
    def coerce_to_string(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        # Handle pandas NaN floats
        if isinstance(v, float) and v != v:
            return None
        return str(v)