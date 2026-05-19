from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
RAW_INPUT_DIR = ROOT / "data" / "raw_inputs"
OCR_RESULT_DIR = ROOT / "data" / "ocr_results"

RawSource = Literal[
    "user_input",
    "user_checklist",
    "registry_ocr",
    "building_ocr",
    "explanation_ocr",
    "public_building_data",
    "market_data",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_store_dirs() -> None:
    RAW_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OCR_RESULT_DIR.mkdir(parents=True, exist_ok=True)


def save_raw_input(
    session_id: str,
    source: RawSource,
    data: dict[str, Any],
    *,
    file_name: str | None = None,
    ocr_confidence: float | None = None,
) -> dict[str, Any]:
    ensure_store_dirs()
    prefix = "OCR" if source.endswith("_ocr") else "RAW"
    record = {
        "input_id": f"{prefix}-{uuid4().hex[:8].upper()}",
        "session_id": session_id,
        "source": source,
        "created_at": utc_now(),
        "data": data,
    }
    if file_name:
        record["file_name"] = file_name
    if ocr_confidence is not None:
        record["ocr_confidence"] = round(float(ocr_confidence), 3)

    target_dir = OCR_RESULT_DIR if source.endswith("_ocr") else RAW_INPUT_DIR
    path = target_dir / f"{session_id}_{record['input_id']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def load_session_records(session_id: str) -> list[dict[str, Any]]:
    ensure_store_dirs()
    records: list[dict[str, Any]] = []
    for directory in (RAW_INPUT_DIR, OCR_RESULT_DIR):
        for path in directory.glob(f"{session_id}_*.json"):
            records.append(json.loads(path.read_text(encoding="utf-8")))
    return sorted(records, key=lambda row: row.get("created_at", ""))


def latest_by_source(session_id: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in load_session_records(session_id):
        latest[record["source"]] = record
    return latest
