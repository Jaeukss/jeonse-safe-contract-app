from src.input_layer.detect_conflict import detect_conflicts
from src.input_layer.merge_data import merge_records


def test_conflict_detects_ocr_vs_manual_correction():
    records = [
        {"input_id": "OCR-1", "session_id": "S-1", "source": "registry_ocr", "data": {"mortgage_flag": True}, "ocr_confidence": 0.8},
        {"input_id": "RAW-1", "session_id": "S-1", "source": "manual_correction", "data": {"mortgage_flag": False}},
    ]

    conflicts = detect_conflicts(
        {
            "mortgage_flag": [
                {"value": True, "source": "registry_ocr", "confidence": 0.8},
                {"value": False, "source": "manual_correction", "confidence": 0.9},
            ]
        }
    )
    fields, merge_conflicts = merge_records(records)

    assert conflicts[0]["field"] == "mortgage_flag"
    assert merge_conflicts
    assert fields["mortgage_flag"].status == "conflict"
