from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import shutil
import subprocess
from typing import BinaryIO, Iterable


@dataclass(frozen=True)
class TextExtractionResult:
    text: str
    confidence: float
    method: str
    ocr_error: str | None = None


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
    registry_terms = sum(
        text.count(term)
        for term in (
            "등기",
            "갑구",
            "을구",
            "근저당",
            "채권최고액",
            "압류",
            "가압류",
            "신탁",
            "전세권",
            "소유권",
            "가등기",
            "경매",
            "가처분",
        )
    )
    replacement = text.count("\ufffd") + text.count("?")
    return korean * 5 + digits * 0.5 + registry_terms * 18 + min(len(text), 20_000) / 200 - replacement * 3


def _best_text(candidates: list[str]) -> str:
    repaired = [repair_mojibake(candidate).strip() for candidate in candidates if candidate and candidate.strip()]
    return max(repaired, key=_text_quality, default="")


def check_tesseract_ready() -> tuple[bool, str]:
    """Return whether image OCR can run in this environment."""

    if not shutil.which("tesseract"):
        return False, "tesseract executable not found"
    try:
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except Exception as exc:
        return False, f"tesseract check failed: {type(exc).__name__}"
    if result.returncode != 0:
        return False, f"tesseract check failed: exit {result.returncode}"
    languages = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    missing = sorted({"kor", "eng"} - languages)
    if missing:
        return False, f"tesseract language pack missing: {', '.join(missing)}"
    return True, "ok"


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


def _upscale_if_small(image: object, *, min_width: int = 1600) -> object:
    from PIL import Image

    width, height = image.size  # type: ignore[attr-defined]
    if width >= min_width:
        return image
    ratio = min_width / max(width, 1)
    return image.resize((int(width * ratio), int(height * ratio)), Image.Resampling.LANCZOS)  # type: ignore[attr-defined]


def _image_variants(image: object) -> Iterable[object]:
    """Generate OCR variants for noisy scans without requiring OpenCV.

    The variants target common Korean registry uploads: low contrast camera
    photos, grey backgrounds, skewed brightness, and thin table text. Keeping
    this in PIL avoids extra deployment packages on Streamlit Cloud.
    """

    from PIL import ImageEnhance, ImageFilter, ImageOps

    base = ImageOps.exif_transpose(image)  # type: ignore[arg-type]
    base = _upscale_if_small(base)
    gray = base.convert("L")  # type: ignore[attr-defined]
    autocontrast = ImageOps.autocontrast(gray)

    yield base
    yield gray
    yield autocontrast
    yield ImageEnhance.Contrast(autocontrast).enhance(1.8)
    yield ImageEnhance.Sharpness(ImageEnhance.Contrast(autocontrast).enhance(1.6)).enhance(1.5)
    yield autocontrast.filter(ImageFilter.MedianFilter(size=3))

    # Simple binary threshold variants. Different scans need different cutoffs.
    for threshold in (145, 165, 185, 205):
        yield autocontrast.point(lambda pixel, t=threshold: 255 if pixel > t else 0)


def _ocr_pil_image(image: object) -> tuple[str, str | None]:
    ready, status = check_tesseract_ready()
    if not ready:
        return "", status
    try:
        import pytesseract

        candidates: list[str] = []
        errors: list[str] = []
        configs = (
            "--oem 3 --psm 6",
            "--oem 3 --psm 4",
            "--oem 3 --psm 11",
            "--oem 3 --psm 12",
        )
        for variant_index, variant in enumerate(_image_variants(image)):
            for config in configs:
                try:
                    candidates.append(pytesseract.image_to_string(variant, lang="kor+eng", config=config))
                except Exception as exc:
                    errors.append(f"variant {variant_index} {config}: {type(exc).__name__}")

        text = _best_text(candidates)
        if not text.strip():
            return "", "; ".join(errors[:3]) or "tesseract returned empty text"
        return text, None
    except Exception as exc:
        return "", f"tesseract OCR failed: {type(exc).__name__}"


def extract_image_text(data: bytes) -> str:
    text, _ = extract_image_text_with_error(data)
    return text


def extract_image_text_with_error(data: bytes) -> tuple[str, str | None]:
    try:
        from PIL import Image

        image = Image.open(BytesIO(data))
        return _ocr_pil_image(image)
    except Exception as exc:
        return "", f"image open failed: {type(exc).__name__}"


def extract_pdf_image_text(data: bytes, *, max_pages: int = 5) -> str:
    text, _ = extract_pdf_image_text_with_error(data, max_pages=max_pages)
    return text


def extract_pdf_image_text_with_error(data: bytes, *, max_pages: int = 5) -> tuple[str, str | None]:
    ready, status = check_tesseract_ready()
    if not ready:
        return "", status
    try:
        import fitz  # PyMuPDF

        page_texts: list[str] = []
        errors: list[str] = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for page_index in range(min(len(doc), max_pages)):
                page = doc[page_index]
                # 3x improves small Korean table text. If rendering is too heavy,
                # fall back to 2x for the same page.
                page_text = ""
                page_error = None
                for scale in (3, 2):
                    try:
                        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                        page_text, page_error = extract_image_text_with_error(pixmap.tobytes("png"))
                        if page_text.strip():
                            break
                    except Exception as exc:
                        page_error = f"render scale {scale}: {type(exc).__name__}"
                page_texts.append(page_text)
                if page_error:
                    errors.append(f"page {page_index + 1}: {page_error}")
        text = _best_text(page_texts)
        if text.strip():
            return text, None
        return "", "; ".join(errors) or "pdf OCR returned empty text"
    except Exception as exc:
        return "", f"pdf render failed: {type(exc).__name__}"


def extract_text_with_diagnostics(file_or_path: str | Path | bytes | BinaryIO, *, filename: str | None = None) -> TextExtractionResult:
    data, inferred_name = _read_bytes(file_or_path)
    name = (filename or inferred_name or "").lower()

    if name.endswith(".pdf"):
        text = extract_pdf_text(data)
        if text.strip():
            return TextExtractionResult(text.strip(), 0.88, "pdf_text_best")
        image_text, ocr_error = extract_pdf_image_text_with_error(data)
        return TextExtractionResult(image_text.strip(), 0.56 if image_text.strip() else 0.0, "pdf_ocr_multi_preprocess", ocr_error)

    if name.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        text, ocr_error = extract_image_text_with_error(data)
        return TextExtractionResult(text.strip(), 0.62 if text.strip() else 0.0, "image_ocr_multi_preprocess", ocr_error)

    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return TextExtractionResult(repair_mojibake(data.decode(encoding)).strip(), 0.95, "text")
        except UnicodeDecodeError:
            continue
    return TextExtractionResult(repair_mojibake(data.decode("utf-8", errors="ignore")).strip(), 0.5, "text_lossy")


def extract_text(file_or_path: str | Path | bytes | BinaryIO, *, filename: str | None = None) -> tuple[str, float, str]:
    result = extract_text_with_diagnostics(file_or_path, filename=filename)
    return result.text, result.confidence, result.method
