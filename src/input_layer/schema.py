from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


FieldStatus = Literal["confirmed", "unknown", "conflict"]


class FieldValue(BaseModel):
    value: Any = None
    source: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: FieldStatus = "unknown"


class DiagnosisSnapshot(BaseModel):
    snapshot_id: str
    session_id: str
    created_at: str
    fields: dict[str, FieldValue]
    confirmed_data: dict[str, Any]
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
