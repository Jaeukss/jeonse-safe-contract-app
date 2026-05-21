from __future__ import annotations

import json
import os
import shutil
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
LOCAL_ZIP = ROOT / "artifacts" / "gwanak_gangseo_final_used_files.zip"
CACHE_ZIP = ROOT / "artifacts" / "downloaded_gwanak_gangseo_final_used_files.zip"

CORE_FILES = [
    ROOT / "data" / "processed" / "ganak_rent_clean.csv",
    ROOT / "data" / "processed" / "ganak_sale_clean.csv",
    ROOT / "data" / "processed" / "ganak_building_clean.csv",
]

ENRICHED_FILES = [
    ROOT / "data" / "processed" / "gwanak_gangseo_official_house_price_latest.csv",
    ROOT / "data" / "rag_docs" / "processed" / "rag_corpus_gwanak_gangseo.jsonl",
    ROOT / "data" / "rag_docs" / "processed" / "rag_source_manifest_gwanak_gangseo.json",
]

ALLOWED_PREFIXES = (
    "data/processed/",
    "data/rag_docs/processed/",
    "data/models/",
    "data/model_diagnostics/",
    "data/model_improvements/",
    "artifacts/gwanak_gangseo_processing_report.json",
)


@dataclass
class DataBootstrapStatus:
    ready: bool
    source: str | None
    extracted: bool
    downloaded: bool
    core_missing: list[str]
    enriched_missing: list[str]
    message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _missing(paths: list[Path]) -> list[str]:
    return [_relative(path) for path in paths if not path.exists()]


def _zip_source() -> tuple[Path | None, bool]:
    if LOCAL_ZIP.exists():
        return LOCAL_ZIP, False

    url = os.environ.get("JEONSE_DATA_ZIP_URL", "").strip()
    if not url:
        return None, False

    CACHE_ZIP.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response, CACHE_ZIP.open("wb") as target:
        shutil.copyfileobj(response, target)
    return CACHE_ZIP, True


def _safe_extract(zip_path: Path) -> None:
    with ZipFile(zip_path) as zf:
        for member in zf.infolist():
            name = member.filename.replace("\\", "/")
            if member.is_dir():
                continue
            if name.startswith("/") or ".." in Path(name).parts:
                continue
            if not any(name.startswith(prefix) for prefix in ALLOWED_PREFIXES):
                continue

            target = (ROOT / name).resolve()
            if not str(target).startswith(str(ROOT.resolve())):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def ensure_data_available(*, force: bool = False) -> DataBootstrapStatus:
    auto_enabled = os.environ.get("JEONSE_AUTO_BOOTSTRAP", "1").strip().lower() not in {"0", "false", "no"}
    core_missing_before = _missing(CORE_FILES)
    enriched_missing_before = _missing(ENRICHED_FILES)

    if not auto_enabled and not force:
        return DataBootstrapStatus(
            ready=not core_missing_before,
            source=None,
            extracted=False,
            downloaded=False,
            core_missing=core_missing_before,
            enriched_missing=enriched_missing_before,
            message="자동 데이터 준비가 비활성화되어 있습니다.",
        )

    extracted = False
    downloaded = False
    source_path: Path | None = None
    if force or core_missing_before or enriched_missing_before:
        source_path, downloaded = _zip_source()
        if source_path and source_path.exists():
            _safe_extract(source_path)
            extracted = True

    core_missing_after = _missing(CORE_FILES)
    enriched_missing_after = _missing(ENRICHED_FILES)
    ready = not core_missing_after
    if ready and not enriched_missing_after:
        message = "전체 데이터가 준비되었습니다."
    elif ready:
        message = "핵심 진단 데이터는 준비되었고, 보조/RAG 데이터 일부가 없습니다."
    else:
        message = "핵심 진단 데이터가 부족합니다. 최종 zip 또는 JEONSE_DATA_ZIP_URL이 필요합니다."

    return DataBootstrapStatus(
        ready=ready,
        source=str(source_path) if source_path else None,
        extracted=extracted,
        downloaded=downloaded,
        core_missing=core_missing_after,
        enriched_missing=enriched_missing_after,
        message=message,
    )


def main() -> None:
    status = ensure_data_available(force=True)
    print(json.dumps(status.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
