from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "registry"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads"

EXPECTED_ZIP_FILENAMES = {
    "(경기)국토교통부_건축물대장_표제부.zip",
    "(인천)국토교통부_건축물대장_표제부.zip",
    "(서울)국토교통부_건축물대장_표제부.zip",
    "(경기)국토교통부_건축물대장_전유부.zip",
    "(인천)국토교통부_건축물대장_전유부.zip",
    "(서울)국토교통부_건축물대장_전유부.zip",
    "(경기)국토교통부_건축물대장_층별개요.zip",
    "(인천)국토교통부_건축물대장_층별개요.zip",
    "(서울)국토교통부_건축물대장_층별개요.zip",
    "(서울)국토교통부_건축물대장_전유공용면적.zip",
}

TABLE_KEYWORDS = {
    "title": "표제부",
    "unit": "전유부",
    "floor": "층별개요",
    "area": "전유공용면적",
}

PUBLIC_SOURCE_URL = "https://www.data.go.kr/dataset/15004825/openapi.do"

RECORD_COLUMNS = [
    "registry_sample_id",
    "source_region",
    "registry_table",
    "address",
    "road_address",
    "legal_dong_code",
    "sigungu_code",
    "building_registry_pk",
    "building_name",
    "dong_name",
    "ho_name",
    "floor",
    "main_use",
    "area_m2",
    "approval_year",
    "violation_status",
    "raw_source_zip",
    "raw_source_file",
]

FEATURE_COLUMNS = [
    "registry_id",
    "source_region",
    "address",
    "road_address",
    "legal_dong_code",
    "sigungu_code",
    "building_registry_pk",
    "building_name",
    "primary_main_use",
    "approval_year",
    "unit_count",
    "observed_floor_count",
    "total_observed_area_m2",
    "has_title_section",
    "has_unit_section",
    "has_floor_section",
    "has_area_section",
    "violation_status",
    "data_completeness_score",
    "old_building_flag",
    "non_residential_use_flag",
    "basement_or_unknown_floor_flag",
    "missing_approval_year_flag",
    "registry_weak_label",
    "risk_reasons",
]


def clean(value: Any) -> str:
    return str(value or "").strip()


def digits(value: str) -> str:
    return "".join(ch for ch in clean(value) if ch.isdigit())


def to_float(value: str) -> float:
    text = clean(value).replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def to_int(value: str) -> int | None:
    text = digits(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_year(value: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", clean(value))
    if not match:
        return None
    return int(match.group(0))


def stable_id(*parts: str, length: int = 16) -> str:
    body = "|".join(clean(part) for part in parts)
    return hashlib.sha1(body.encode("utf-8", errors="ignore")).hexdigest()[:length]


def guess_region(path: Path) -> str:
    name = path.name
    for region in ("서울", "인천", "경기"):
        if region in name:
            return region
    return "unknown"


def guess_table(path: Path) -> str | None:
    name = path.name
    if TABLE_KEYWORDS["area"] in name:
        return "area"
    if TABLE_KEYWORDS["floor"] in name:
        return "floor"
    if TABLE_KEYWORDS["unit"] in name:
        return "unit"
    if TABLE_KEYWORDS["title"] in name:
        return "title"
    return None


def find_registry_zips(input_dir: Path, *, use_all_zips: bool = False) -> list[dict[str, Any]]:
    items = []
    for path in sorted(input_dir.glob("*.zip")):
        if not use_all_zips and path.name not in EXPECTED_ZIP_FILENAMES:
            continue
        table = guess_table(path)
        if table is None:
            continue
        items.append(
            {
                "path": path,
                "region": guess_region(path),
                "table": table,
                "size_bytes": path.stat().st_size,
            }
        )
    return items


def csv_members(zf: zipfile.ZipFile) -> list[str]:
    names = []
    for name in zf.namelist():
        lowered = name.lower()
        if lowered.endswith(".csv") and not name.endswith("/"):
            names.append(name)
    return sorted(names)


def row_get(row: dict[str, str], *names: str) -> str:
    for name in names:
        if name in row and clean(row[name]):
            return clean(row[name])
    return ""


def normalize_row(
    row: dict[str, str],
    *,
    source_zip: Path,
    source_file: str,
    region: str,
    table: str,
) -> dict[str, Any]:
    approval_year = parse_year(row_get(row, "사용승인일", "사용승인일자"))
    if approval_year is None:
        approval_year = parse_year(row_get(row, "생성일자"))

    main_use = row_get(row, "주용도코드명", "기타용도", "기타용동", "주용도")
    area = row_get(row, "전유면적", "전유면적(㎡)", "면적(㎡)", "대지면적(㎡)", "연면적(㎡)")
    floor = row_get(row, "층번호", "지상층수")
    registry_pk = row_get(row, "관리건축물대장PK")
    address = row_get(row, "대지위치")
    road_address = row_get(row, "도로명대지위치")
    building_name = row_get(row, "건물명")
    dong_name = row_get(row, "동명칭")
    ho_name = row_get(row, "호명칭")
    legal_dong_code = digits(row_get(row, "법정동코드"))
    sigungu_code = digits(row_get(row, "시군구코드"))

    registry_sample_id = stable_id(
        source_zip.name,
        source_file,
        registry_pk,
        address,
        dong_name,
        ho_name,
        floor,
        table,
    )
    return {
        "registry_sample_id": registry_sample_id,
        "source_region": region,
        "registry_table": table,
        "address": address,
        "road_address": road_address,
        "legal_dong_code": legal_dong_code,
        "sigungu_code": sigungu_code,
        "building_registry_pk": registry_pk,
        "building_name": building_name,
        "dong_name": dong_name,
        "ho_name": ho_name,
        "floor": to_int(floor),
        "main_use": main_use,
        "area_m2": round(to_float(area), 4),
        "approval_year": approval_year,
        "violation_status": "unknown",
        "raw_source_zip": source_zip.name,
        "raw_source_file": source_file,
    }


def read_zip_records(
    item: dict[str, Any],
    *,
    max_rows_per_zip: int,
    max_rows_per_file: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = item["path"]
    records = []
    manifest = {
        "source_zip": path.name,
        "source_path": str(path),
        "source_region": item["region"],
        "registry_table": item["table"],
        "zip_size_bytes": item["size_bytes"],
        "csv_files_seen": 0,
        "rows_sampled": 0,
        "status": "ok",
    }
    try:
        with zipfile.ZipFile(path) as zf:
            members = csv_members(zf)
            manifest["csv_files_seen"] = len(members)
            for member in members:
                if len(records) >= max_rows_per_zip:
                    break
                with zf.open(member) as raw:
                    text = (line.decode("utf-8-sig", errors="replace") for line in raw)
                    reader = csv.DictReader(text)
                    per_file = 0
                    for row in reader:
                        if len(records) >= max_rows_per_zip or per_file >= max_rows_per_file:
                            break
                        records.append(
                            normalize_row(
                                row,
                                source_zip=path,
                                source_file=member,
                                region=item["region"],
                                table=item["table"],
                            )
                        )
                        per_file += 1
    except Exception as exc:  # pragma: no cover - included in manifest for operators
        manifest["status"] = "error"
        manifest["error"] = str(exc)
    manifest["rows_sampled"] = len(records)
    return records, manifest


def mode(values: list[str]) -> str:
    clean_values = [clean(v) for v in values if clean(v)]
    if not clean_values:
        return ""
    return Counter(clean_values).most_common(1)[0][0]


def first(values: list[Any]) -> Any:
    for value in values:
        if value not in ("", None, 0):
            return value
    return ""


def build_features(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = record["building_registry_pk"] or stable_id(
            record["address"],
            record["road_address"],
            record["building_name"],
            record["dong_name"],
            record["legal_dong_code"],
        )
        grouped[key].append(record)

    features = []
    for key, rows in grouped.items():
        tables = {row["registry_table"] for row in rows}
        floors = [row["floor"] for row in rows if isinstance(row["floor"], int)]
        approval_years = [row["approval_year"] for row in rows if row["approval_year"]]
        main_use = mode([row["main_use"] for row in rows])
        area_sum = sum(float(row["area_m2"] or 0.0) for row in rows)
        unit_count = len(
            {
                (row["dong_name"], row["ho_name"])
                for row in rows
                if row["registry_table"] == "unit" and clean(row["ho_name"])
            }
        )
        approval_year = min(approval_years) if approval_years else None
        old_building = bool(approval_year and approval_year <= 2005)
        non_residential = bool(main_use and not any(token in main_use for token in ("주택", "아파트", "다가구", "다세대", "연립", "오피스텔")))
        basement_or_unknown = any((floor or 0) <= 0 for floor in floors) or not floors
        missing_approval = approval_year is None

        completeness_parts = [
            bool(first([row["address"] for row in rows])),
            bool(first([row["legal_dong_code"] for row in rows])),
            "title" in tables,
            "unit" in tables or "area" in tables,
            bool(approval_year),
            bool(main_use),
        ]
        completeness = round(sum(completeness_parts) / len(completeness_parts), 3)
        reasons = []
        if old_building:
            reasons.append("old_building")
        if non_residential:
            reasons.append("non_residential_main_use")
        if basement_or_unknown:
            reasons.append("basement_or_unknown_floor")
        if missing_approval:
            reasons.append("missing_approval_year")
        if completeness < 0.67:
            reasons.append("low_data_completeness")

        weak_label = 1 if reasons else 0
        features.append(
            {
                "registry_id": stable_id(key),
                "source_region": mode([row["source_region"] for row in rows]),
                "address": first([row["address"] for row in rows]),
                "road_address": first([row["road_address"] for row in rows]),
                "legal_dong_code": first([row["legal_dong_code"] for row in rows]),
                "sigungu_code": first([row["sigungu_code"] for row in rows]),
                "building_registry_pk": key,
                "building_name": first([row["building_name"] for row in rows]),
                "primary_main_use": main_use,
                "approval_year": approval_year or "",
                "unit_count": unit_count,
                "observed_floor_count": len(set(floors)),
                "total_observed_area_m2": round(area_sum, 4),
                "has_title_section": int("title" in tables),
                "has_unit_section": int("unit" in tables),
                "has_floor_section": int("floor" in tables),
                "has_area_section": int("area" in tables),
                "violation_status": "unknown",
                "data_completeness_score": completeness,
                "old_building_flag": int(old_building),
                "non_residential_use_flag": int(non_residential),
                "basement_or_unknown_floor_flag": int(basement_or_unknown),
                "missing_approval_year_flag": int(missing_approval),
                "registry_weak_label": weak_label,
                "risk_reasons": "|".join(reasons),
            }
        )
    return sorted(features, key=lambda row: row["registry_id"])


def chunk_text(row: dict[str, Any]) -> str:
    parts = [
        f"address={row['address'] or row['road_address']}",
        f"legal_dong_code={row['legal_dong_code']}",
        f"building_name={row['building_name']}",
        f"main_use={row['primary_main_use']}",
        f"approval_year={row['approval_year']}",
        f"unit_count={row['unit_count']}",
        f"observed_floor_count={row['observed_floor_count']}",
        f"area_m2={row['total_observed_area_m2']}",
        f"violation_status={row['violation_status']}",
        f"risk_reasons={row['risk_reasons'] or 'none'}",
    ]
    return "; ".join(str(part) for part in parts if part)


def build_chunks(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks = []
    for row in features:
        chunks.append(
            {
                "chunk_id": f"registry-{row['registry_id']}",
                "source_type": "building_registry",
                "provider": "MOLIT building registry open data",
                "official_url": PUBLIC_SOURCE_URL,
                "title": f"Building registry evidence: {row['address'] or row['road_address']}",
                "text": chunk_text(row),
                "metadata": {
                    "registry_id": row["registry_id"],
                    "source_region": row["source_region"],
                    "legal_dong_code": row["legal_dong_code"],
                    "primary_main_use": row["primary_main_use"],
                    "approval_year": row["approval_year"],
                    "violation_status": row["violation_status"],
                    "weak_label": row["registry_weak_label"],
                },
            }
        )
    return chunks


def feature_vector(row: dict[str, Any]) -> list[float]:
    year = int(row["approval_year"]) if str(row["approval_year"]).isdigit() else 0
    age = 0 if not year else max(0, 2026 - year)
    return [
        age / 60.0,
        math.log1p(float(row["unit_count"])) / 6.0,
        math.log1p(float(row["observed_floor_count"])) / 5.0,
        math.log1p(float(row["total_observed_area_m2"])) / 10.0,
        float(row["has_title_section"]),
        float(row["has_unit_section"]),
        float(row["has_floor_section"]),
        float(row["has_area_section"]),
        float(row["data_completeness_score"]),
        float(row["old_building_flag"]),
        float(row["non_residential_use_flag"]),
        float(row["basement_or_unknown_floor_flag"]),
        float(row["missing_approval_year_flag"]),
    ]


def split_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train = []
    test = []
    for row in rows:
        bucket = int(hashlib.sha1(row["registry_id"].encode("utf-8")).hexdigest()[:8], 16) % 10
        (test if bucket < 2 else train).append(row)
    if not test and rows:
        test = rows[: max(1, len(rows) // 5)]
        train = rows[len(test) :]
    return train, test


def train_logistic(train_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not train_rows:
        return {"weights": [], "bias": 0.0, "means": [], "stds": []}
    vectors = [feature_vector(row) for row in train_rows]
    labels = [float(row["registry_weak_label"]) for row in train_rows]
    width = len(vectors[0])
    means = [sum(vec[i] for vec in vectors) / len(vectors) for i in range(width)]
    stds = []
    for i in range(width):
        variance = sum((vec[i] - means[i]) ** 2 for vec in vectors) / len(vectors)
        stds.append(math.sqrt(variance) or 1.0)

    def normalize(vec: list[float]) -> list[float]:
        return [(vec[i] - means[i]) / stds[i] for i in range(width)]

    weights = [0.0] * width
    bias = 0.0
    lr = 0.08
    l2 = 0.001
    for _ in range(450):
        grad_w = [0.0] * width
        grad_b = 0.0
        for raw_vec, label in zip(vectors, labels):
            vec = normalize(raw_vec)
            z = bias + sum(w * x for w, x in zip(weights, vec))
            pred = 1.0 / (1.0 + math.exp(-max(-35.0, min(35.0, z))))
            error = pred - label
            for i, value in enumerate(vec):
                grad_w[i] += error * value
            grad_b += error
        n = max(len(vectors), 1)
        for i in range(width):
            weights[i] -= lr * ((grad_w[i] / n) + l2 * weights[i])
        bias -= lr * (grad_b / n)
    return {"weights": weights, "bias": bias, "means": means, "stds": stds}


def predict(model: dict[str, Any], row: dict[str, Any]) -> float:
    weights = model.get("weights", [])
    if not weights:
        return 0.0
    vec = feature_vector(row)
    means = model["means"]
    stds = model["stds"]
    norm = [(vec[i] - means[i]) / (stds[i] or 1.0) for i in range(len(weights))]
    z = model["bias"] + sum(w * x for w, x in zip(weights, norm))
    return 1.0 / (1.0 + math.exp(-max(-35.0, min(35.0, z))))


def auc(labels: list[int], scores: list[float]) -> float | None:
    positives = [score for label, score in zip(labels, scores) if label == 1]
    negatives = [score for label, score in zip(labels, scores) if label == 0]
    if not positives or not negatives:
        return None
    wins = 0.0
    total = len(positives) * len(negatives)
    for pos in positives:
        for neg in negatives:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / total


def evaluate_classifier(features: list[dict[str, Any]]) -> dict[str, Any]:
    train_rows, test_rows = split_rows(features)
    model = train_logistic(train_rows)
    labels = [int(row["registry_weak_label"]) for row in test_rows]
    scores = [predict(model, row) for row in test_rows]
    preds = [1 if score >= 0.5 else 0 for score in scores]
    tp = sum(1 for y, p in zip(labels, preds) if y == 1 and p == 1)
    tn = sum(1 for y, p in zip(labels, preds) if y == 0 and p == 0)
    fp = sum(1 for y, p in zip(labels, preds) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(labels, preds) if y == 1 and p == 0)
    total = max(len(labels), 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    majority = 1 if sum(int(row["registry_weak_label"]) for row in train_rows) >= len(train_rows) / 2 else 0
    majority_accuracy = sum(1 for y in labels if y == majority) / total
    return {
        "task": "weakly_supervised_registry_review_classifier",
        "label_definition": "1 when the normalized registry record has rule-derived review reasons; this is not a confirmed fraud label.",
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "positive_rate_train": round(sum(int(row["registry_weak_label"]) for row in train_rows) / max(len(train_rows), 1), 4),
        "positive_rate_test": round(sum(labels) / total, 4),
        "accuracy": round((tp + tn) / total, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "roc_auc": None if auc(labels, scores) is None else round(float(auc(labels, scores)), 4),
        "majority_baseline_accuracy": round(majority_accuracy, 4),
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "model": model,
    }


TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "") if len(token) >= 2]


def retrieval_score(query_tokens: Counter[str], doc_tokens: Counter[str], idf: dict[str, float]) -> float:
    score = 0.0
    for token, q_count in query_tokens.items():
        if token in doc_tokens:
            score += (1.0 + math.log(q_count)) * (1.0 + math.log(doc_tokens[token])) * idf.get(token, 1.0)
    return score


def evaluate_retrieval(chunks: list[dict[str, Any]], features: list[dict[str, Any]]) -> dict[str, Any]:
    doc_counters = [Counter(tokenize(chunk["text"])) for chunk in chunks]
    document_frequency: Counter[str] = Counter()
    for counter in doc_counters:
        document_frequency.update(counter.keys())
    idf = {token: math.log((len(chunks) + 1) / (df + 1)) + 1 for token, df in document_frequency.items()}
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    chunk_by_registry_id = {chunk["metadata"]["registry_id"]: chunk["chunk_id"] for chunk in chunks}

    rng = random.Random(20260518)
    sample = list(features)
    rng.shuffle(sample)
    sample = sample[: min(200, len(sample))]
    hits = {1: 0, 5: 0, 10: 0}
    evaluated = 0
    for row in sample:
        target = chunk_by_registry_id.get(row["registry_id"])
        if not target:
            continue
        query = " ".join(
            clean(part)
            for part in [
                row["address"],
                row["road_address"],
                row["legal_dong_code"],
                row["building_name"],
                row["primary_main_use"],
            ]
            if clean(part)
        )
        query_tokens = Counter(tokenize(query))
        if not query_tokens:
            continue
        scored = [
            (retrieval_score(query_tokens, counter, idf), chunk_id)
            for counter, chunk_id in zip(doc_counters, chunk_ids)
        ]
        scored.sort(reverse=True)
        ranked = [chunk_id for _, chunk_id in scored[:10]]
        evaluated += 1
        for k in hits:
            if target in ranked[:k]:
                hits[k] += 1

    return {
        "task": "registry_rag_lexical_retrieval",
        "retrieval_method": "token tf-idf cosine-style overlap implemented with Python standard library",
        "evaluated_queries": evaluated,
        "recall_at_1": round(hits[1] / max(evaluated, 1), 4),
        "recall_at_5": round(hits[5] / max(evaluated, 1), 4),
        "recall_at_10": round(hits[10] / max(evaluated, 1), 4),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build compact registry RAG and evaluation artifacts from MOLIT building-registry ZIP files.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_DOWNLOAD_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--max-rows-per-zip", type=int, default=800)
    parser.add_argument("--max-rows-per-file", type=int, default=80)
    parser.add_argument("--use-all-zips", action="store_true", help="Use every matching building-registry ZIP in input-dir instead of the 10 contest files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    zips = find_registry_zips(args.input_dir, use_all_zips=args.use_all_zips)
    all_records: list[dict[str, Any]] = []
    manifests = []
    for item in zips:
        records, manifest = read_zip_records(
            item,
            max_rows_per_zip=args.max_rows_per_zip,
            max_rows_per_file=args.max_rows_per_file,
        )
        all_records.extend(records)
        manifests.append(manifest)

    features = build_features(all_records)
    chunks = build_chunks(features)
    classifier_eval = evaluate_classifier(features)
    retrieval_eval = evaluate_retrieval(chunks, features)

    manifest_payload = {
        "created_for": "Transportation-and-Logistics-Contest MVP",
        "source_note": "Raw ZIP files stay outside Git/Hugging Face because the uncompressed building-registry files are multi-GB public datasets.",
        "input_dir": str(args.input_dir),
        "output_dir": str(output_dir),
        "max_rows_per_zip": args.max_rows_per_zip,
        "max_rows_per_file": args.max_rows_per_file,
        "zip_count": len(zips),
        "records_sampled": len(all_records),
        "feature_rows": len(features),
        "rag_chunks": len(chunks),
        "official_source_url": PUBLIC_SOURCE_URL,
        "important_limitations": [
            "The provided registry CSV samples do not expose a direct violation-building flag; violation_status is kept as unknown instead of inferred.",
            "The classifier is weakly supervised from registry-quality/risk-review rules, not trained on confirmed fraud outcomes.",
            "For production, run this pipeline without row limits and join confirmed labels from adjudicated cases or public safety outcomes.",
        ],
        "sources": manifests,
    }

    write_csv(output_dir / "registry_records_sample.csv", all_records, RECORD_COLUMNS)
    write_csv(output_dir / "registry_feature_table.csv", features, FEATURE_COLUMNS)
    write_jsonl(output_dir / "registry_search_chunks.jsonl", chunks)
    write_json(output_dir / "registry_ingestion_manifest.json", manifest_payload)
    write_json(
        output_dir / "registry_model_eval.json",
        {
            "classifier": {key: value for key, value in classifier_eval.items() if key != "model"},
            "retrieval": retrieval_eval,
            "feature_columns": FEATURE_COLUMNS,
        },
    )
    write_json(output_dir / "registry_model_weights.json", classifier_eval["model"])

    print(json.dumps({
        "zip_count": len(zips),
        "records_sampled": len(all_records),
        "feature_rows": len(features),
        "search_chunks": len(chunks),
        "classifier_f1": classifier_eval["f1"],
        "retrieval_recall_at_5": retrieval_eval["recall_at_5"],
        "output_dir": str(output_dir),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
