from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_step(command: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run preprocessing, RAG build, model training, and evaluation for the MVP.")
    parser.add_argument("--registry-input-dir", type=Path, default=Path.home() / "Downloads")
    parser.add_argument("--max-rows-per-zip", type=int, default=800)
    parser.add_argument("--max-rows-per-file", type=int, default=80)
    parser.add_argument("--skip-registry", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    python = sys.executable
    steps: list[list[str]] = [
        [python, "scripts/rag_document_pipeline.py"],
        [python, "scripts/train_evaluate_models.py"],
    ]
    if not args.skip_registry:
        steps.insert(
            1,
            [
                python,
                "scripts/registry_pipeline.py",
                "--input-dir",
                str(args.registry_input_dir),
                "--max-rows-per-zip",
                str(args.max_rows_per_zip),
                "--max-rows-per-file",
                str(args.max_rows_per_file),
            ],
        )

    results = [run_step(step) for step in steps]
    failed = [item for item in results if item["returncode"] != 0]
    payload = {
        "status": "failed" if failed else "ok",
        "steps": results,
        "artifacts": [
            "data/rag/official_rag_corpus.jsonl",
            "data/rag/official_rag_retrieval_eval.json",
            "data/registry/registry_feature_table.csv",
            "data/registry/registry_search_chunks.jsonl",
            "data/registry/registry_model_eval.json",
            "data/models/market_preprocessed.csv",
            "data/models/market_model_eval.json",
            "data/models/market_model_weights.json",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
