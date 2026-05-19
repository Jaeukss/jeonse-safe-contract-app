from __future__ import annotations

from pathlib import Path
from typing import BinaryIO


def _read_bytes(file_or_path: str | Path | bytes | BinaryIO) -> tuple[bytes, str]:
    if isinstance(file_or_path, bytes):
        return file_or_path, ""
    if isinstance(file_or_path, (str, Path)):
        path = Path(file_or_path)
        return path.read_bytes(), path.name
    name = getattr(file_or_path, "name", "")
    data = file_or_path.read()
    if hasattr(file_or_path, "seek"):
        file_or_path.seek(0)
    return data, str(name)


def extract_pdf_text(data: bytes) -> str:
    try:
        import fitz  # PyMuPDF

        with fitz.open(stream=data, filetype="pdf") as doc:
            text = "\n".join(page.get_text("text") for page in doc)
        if text.strip():
            return text
    except Exception:
        pass

    try:
        from pypdf import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def extract_image_text(data: bytes) -> str:
    try:
        from io import BytesIO

        import pytesseract
        from PIL import Image

        image = Image.open(BytesIO(data))
        return pytesseract.image_to_string(image, lang="kor+eng")
    except Exception:
        return ""


def extract_text(file_or_path: str | Path | bytes | BinaryIO, *, filename: str | None = None) -> tuple[str, float, str]:
    data, inferred_name = _read_bytes(file_or_path)
    name = (filename or inferred_name or "").lower()

    if name.endswith(".pdf"):
        text = extract_pdf_text(data)
        if text.strip():
            return text.strip(), 0.86, "pdf_text"
        image_text = extract_image_text(data)
        return image_text.strip(), 0.45 if image_text.strip() else 0.0, "pdf_ocr"

    if name.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        text = extract_image_text(data)
        return text.strip(), 0.55 if text.strip() else 0.0, "image_ocr"

    for encoding in ("utf-8", "cp949"):
        try:
            return data.decode(encoding).strip(), 0.95, "text"
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore").strip(), 0.5, "text_lossy"
