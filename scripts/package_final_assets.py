from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "gwanak_gangseo_final_used_files.zip"


EXPLICIT_FILES = [
    "artifacts/gwanak_gangseo_processing_report.json",
    "data/models/best_price_model_seoul_multi_year.json",
    "data/models/gwanak_gangseo_price_model_eval.json",
    "data/models/selected_price_model_summary.json",
    "data/models/segmented_price_model_summary.json",
    "data/models/seoul_multi_year_ml_dl_benchmark_summary.json",
    "docs/MODELING_AND_DATA_REPORT.md",
    "docs/MODEL_ERROR_ANALYSIS.md",
    "docs/SEGMENT_MODEL_IMPROVEMENT_REPORT.md",
    "docs/01_mvp_scope.md",
    "docs/business_plan_workflow.md",
    "docs/DATA_ACQUISITION_STATUS.md",
    "docs/DATA_SOURCES.md",
    "docs/demo_script.md",
    "docs/final_architecture.md",
    "docs/OFFICIAL_RAG_SOURCE_LINKS.md",
    "docs/VS_CODE_EVALUATION_GUIDE.md",
    "scripts/build_gwanak_gangseo_assets.py",
    "scripts/benchmark_price_models.py",
    "scripts/evaluate_price_model_errors.py",
    "scripts/segment_price_model_improvement.py",
    "scripts/package_final_assets.py",
]

GLOBS = [
    "data/processed/gwanak_gangseo_*.csv",
    "data/processed/ganak_rent_clean.csv",
    "data/processed/ganak_sale_clean.csv",
    "data/processed/ganak_building_clean.csv",
    "data/rag_docs/processed/*",
    "data/model_diagnostics/*",
    "data/model_improvements/*",
]


def collect_files() -> list[Path]:
    files: set[Path] = set()

    for relative in EXPLICIT_FILES:
        path = ROOT / relative
        if path.exists() and path.is_file():
            files.add(path)

    for pattern in GLOBS:
        for path in ROOT.glob(pattern):
            if path.exists() and path.is_file():
                files.add(path)

    return sorted(files)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    files = collect_files()

    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            zf.write(path, path.relative_to(ROOT).as_posix())

    manifest = {
        "zip_path": str(OUTPUT),
        "file_count": len(files),
        "zip_size_bytes": OUTPUT.stat().st_size,
        "included_files": [path.relative_to(ROOT).as_posix() for path in files],
        "excluded": [
            "raw source ZIP/PDF/DOC files",
            "full benchmark payload files with candidate model tables",
            "legacy sample-only model artifacts",
        ],
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
