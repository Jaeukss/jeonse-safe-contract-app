from __future__ import annotations

from io import BytesIO
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


def repair_mojibake(text: str) -> str:
    """Recover common UTF-8 text that was decoded as latin-1/cp1252 by PDF extractors."""
    if not text:
        return ""
    original_korean = sum(1 for char in text if "가" <= char <= "힣")
    candidates = [text]
    for encoding in ("latin1", "cp1252"):
        try:
            candidates.append(text.encode(encoding, errors="strict").decode("utf-8", errors="strict"))
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return max(candidates, key=lambda candidate: _text_quality(candidate) - original_korean / 2)


def _text_quality(text: str) -> float:
    if not text:
        return 0.0
    korean = sum(1 for char in text if "가" <= char <= "힣")
    digits = sum(1 for char in text if char.isdigit())
    replacement = text.count("\ufffd") + text.count("?")
    return korean * 5 + digits * 0.5 + min(len(text), 20_000) / 200 - replacement * 3


def _best_text(candidates: list[str]) -> str:
    repaired = [repair_mojibake(candidate).strip() for candidate in candidates if candidate and candidate.strip()]
    return max(repaired, key=_text_quality, default="")


def _stringify_pdf_tables(tables: list[list[list[object]]]) -> str:
    lines: list[str] = []
    for table in tables:
        for row in table:
            values = [str(cell).strip() for cell in row if cell not in (None, "")]
            if values:
                lines.append(" | ".join(values))
        if lines and lines[-1]:
            lines.append("")
    return "\n".join(lines)


def extract_pdf_text(data: bytes) -> str:
    candidates: list[str] = []

    try:
        import fitz  # PyMuPDF

        with fitz.open(stream=data, filetype="pdf") as doc:
            candidates.append("\n".join(page.get_text("text") for page in doc))
    except Exception:
        pass

    try:
        import pdfplumber

        with pdfplumber.open(BytesIO(data)) as pdf:
            candidates.append("\n".join(page.extract_text() or "" for page in pdf.pages))
            table_texts = []
            for page in pdf.pages:
                table_texts.append(_stringify_pdf_tables(page.extract_tables() or []))
            candidates.append("\n".join(table_texts))
    except Exception:
        pass

    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        candidates.append("\n".join(page.extract_text() or "" for page in reader.pages))
    except Exception:
        pass

    return _best_text(candidates)


def _ocr_pil_image(image: object) -> str:
    try:
        import pytesseract
        from PIL import ImageEnhance, ImageOps

        raw_text = pytesseract.image_to_string(image, lang="kor+eng", config="--oem 3")

        processed = image.convert("L")  # type: ignore[attr-defined]
        processed = ImageOps.autocontrast(processed)
        processed = ImageEnhance.Contrast(processed).enhance(1.6)
        processed = ImageEnhance.Sharpness(processed).enhance(1.4)
        processed_text = pytesseract.image_to_string(processed, lang="kor+eng", config="--oem 3 --psm 6")
        return _best_text([raw_text, processed_text])
    except Exception:
        return ""


def extract_image_text(data: bytes) -> str:
    try:
        from PIL import Image

        image = Image.open(BytesIO(data))
        return _ocr_pil_image(image)
    except Exception:
        return ""


def extract_pdf_image_text(data: bytes, *, max_pages: int = 5) -> str:
    try:
        import fitz  # PyMuPDF

        page_texts: list[str] = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for page_index in range(min(len(doc), max_pages)):
                page = doc[page_index]
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                page_texts.append(extract_image_text(pixmap.tobytes("png")))
        return _best_text(page_texts)
    except Exception:
        return ""


def extract_text(file_or_path: str | Path | bytes | BinaryIO, *, filename: str | None = None) -> tuple[str, float, str]:
    data, inferred_name = _read_bytes(file_or_path)
    name = (filename or inferred_name or "").lower()

    if name.endswith(".pdf"):
        text = extract_pdf_text(data)
        if text.strip():
            return text.strip(), 0.88, "pdf_text_best"
        image_text = extract_pdf_image_text(data)
        return image_text.strip(), 0.52 if image_text.strip() else 0.0, "pdf_ocr"

    if name.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        text = extract_image_text(data)
        return text.strip(), 0.58 if text.strip() else 0.0, "image_ocr"

    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return repair_mojibake(data.decode(encoding)).strip(), 0.95, "text"
        except UnicodeDecodeError:
            continue
    return repair_mojibake(data.decode("utf-8", errors="ignore")).strip(), 0.5, "text_lossy"
