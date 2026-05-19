from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .merge_data import merge_records
from .schema import DiagnosisSnapshot


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = ROOT / "data" / "snapshots"


def create_snapshot(session_id: str, records: list[dict[str, Any]], resolutions: dict[str, Any] | None = None) -> DiagnosisSnapshot:
    fields, conflicts = merge_records(records, resolutions)
    confirmed_data = {
        field: item.value
        for field, item in fields.items()
        if item.status == "confirmed" and item.value is not None
    }
    snapshot = DiagnosisSnapshot(
        snapshot_id=f"SNAP-{uuid4().hex[:8].upper()}",
        session_id=session_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        fields=fields,
        confirmed_data=confirmed_data,
        conflicts=conflicts,
    )
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{snapshot.session_id}_{snapshot.snapshot_id}.json"
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    return snapshot


def load_snapshots(session_id: str) -> list[DiagnosisSnapshot]:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for path in SNAPSHOT_DIR.glob(f"{session_id}_SNAP-*.json"):
        snapshots.append(DiagnosisSnapshot.model_validate(json.loads(path.read_text(encoding="utf-8"))))
    return sorted(snapshots, key=lambda item: item.created_at)
