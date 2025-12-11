from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class NormalizedOffer(BaseModel):
    """
    Canonical normalized offer schema for provider ingestion and API responses.
    Validates types and coerces common primitives to ensure consistency.
    """

    provider: str = Field(..., min_length=1)
    region: str = Field(..., min_length=1)
    gpu_type: str = Field(..., min_length=1)
    price_per_hour: float = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    availability_status: str = Field("available")
    compliance_tags: List[str] = Field(default_factory=list)
    gpu_memory_gb: int = Field(0, ge=0)
    cpu_cores: int = Field(0, ge=0)
    ram_gb: int = Field(0, ge=0)
    storage_gb: int = Field(0, ge=0)
    external_id: str = Field(..., min_length=1)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # Optional performance metrics
    tokens_per_second: Optional[float] = Field(None, ge=0)

    @field_validator("availability_status")
    def _availability_enum(cls, v: str) -> str:
        allowed = {"available", "limited", "unavailable", "busy"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid availability_status: {v}")
        return v.lower()

    @field_validator("compliance_tags", mode="before")
    def _coerce_tags(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return [str(tag) for tag in v]
