from __future__ import annotations

import pytest

from src.document_ai.text_extractor import check_tesseract_ready


def test_tesseract_missing_is_reported(monkeypatch):
    monkeypatch.setattr("src.document_ai.text_extractor.shutil.which", lambda _name: None)

    ready, message = check_tesseract_ready()

    assert ready is False
    assert "tesseract executable not found" in message


def test_tesseract_engine_available_when_running_ocr_demo():
    ready, message = check_tesseract_ready()
    if not ready:
        pytest.skip(f"Image OCR engine is not installed in this environment: {message}")

    assert message == "ok"
