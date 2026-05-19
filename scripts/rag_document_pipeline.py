from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAG_DOCS = ROOT / "data" / "rag_documents_mvp.json"
DEFAULT_SOURCES = ROOT / "data" / "rag_official_sources.json"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "rag"
TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "") if len(token) >= 2]


def source_index(sources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item.get("id", ""): item for item in sources}


def flatten_chunks(documents: list[dict[str, Any]], sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources_by_id = source_index(sources)
    chunks = []
    for document in documents:
        source = sources_by_id.get(document.get("id", ""), {})
        urls = [
            value
            for key, value in source.items()
            if key.endswith("_url") and isinstance(value, str) and value.startswith("http")
        ]
        if document.get("official_url"):
            urls.insert(0, document["official_url"])
        urls = list(dict.fromkeys(urls))
        for idx, chunk in enumerate(document.get("chunks", []), start=1):
            text = " ".join(
                part
                for part in [
                    document.get("title", ""),
                    document.get("mvp_use", ""),
                    chunk.get("heading", ""),
                    chunk.get("summary", ""),
                    chunk.get("agent_response_rule", ""),
                ]
                if part
            )
            chunks.append(
                {
                    "chunk_id": chunk.get("chunk_id") or f"{document.get('id', 'document')}_{idx:03d}",
                    "document_id": document.get("id", ""),
                    "title": document.get("title", ""),
                    "provider": document.get("provider", ""),
                    "document_type": document.get("document_type", source.get("source_type", "")),
                    "official_url": urls[0] if urls else "",
                    "related_urls": urls,
                    "risk_keys": document.get("risk_keys", []),
                    "heading": chunk.get("heading", ""),
                    "text": text,
                    "response_rule": chunk.get("agent_response_rule", ""),
                    "source_verified_at": document.get("source_verified_at") or source.get("source_verified_at", ""),
                }
            )
    return chunks


def rank_chunks(query: str, chunks: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    query_tokens = Counter(tokenize(query))
    if not query_tokens:
        return []
    doc_tokens = [Counter(tokenize(chunk["text"])) for chunk in chunks]
    document_frequency: Counter[str] = Counter()
    for counter in doc_tokens:
        document_frequency.update(counter.keys())
    idf = {
        token: math.log((len(chunks) + 1) / (frequency + 1)) + 1
        for token, frequency in document_frequency.items()
    }
    scored = []
    for chunk, counter in zip(chunks, doc_tokens):
        score = 0.0
        for token, count in query_tokens.items():
            if token in counter:
                score += (1.0 + math.log(count)) * (1.0 + math.log(counter[token])) * idf.get(token, 1.0)
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "score": round(score, 4),
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "title": chunk["title"],
            "risk_keys": chunk["risk_keys"],
        }
        for score, chunk in scored[:limit]
        if score > 0
    ]


def evaluate(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    queries = [
        {
            "query": "근저당권 채권최고액 보증금 말소 조건 등기부 확인",
            "expected_risk_key": "mortgage",
        },
        {
            "query": "신탁등기 신탁원부 임대 권한 동의서 확인",
            "expected_risk_key": "trust",
        },
        {
            "query": "압류 가압류 계약 보류 등기부 위험",
            "expected_risk_key": "seizure",
        },
        {
            "query": "전세가율 보증보험 HUG 반환보증 가입 조건",
            "expected_risk_key": "jeonse_ratio",
        },
        {
            "query": "건축물대장 위반건축물 주용도 전유면적 확인",
            "expected_risk_key": "violation",
        },
        {
            "query": "다가구 선순위 보증금 소액임차인 확인",
            "expected_risk_key": "multifamily",
        },
        {
            "query": "계약 전 표준계약서 중개대상물 확인설명서 특약",
            "expected_risk_key": "unchecked",
        },
    ]
    results = []
    hit_at_1 = 0
    hit_at_3 = 0
    hit_at_5 = 0
    for item in queries:
        ranked = rank_chunks(item["query"], chunks, limit=5)
        expected = item["expected_risk_key"]
        hit_positions = [
            index + 1
            for index, result in enumerate(ranked)
            if expected in result.get("risk_keys", [])
        ]
        if hit_positions and hit_positions[0] <= 1:
            hit_at_1 += 1
        if hit_positions and hit_positions[0] <= 3:
            hit_at_3 += 1
        if hit_positions and hit_positions[0] <= 5:
            hit_at_5 += 1
        results.append(
            {
                "query": item["query"],
                "expected_risk_key": expected,
                "top_results": ranked,
                "first_hit_rank": hit_positions[0] if hit_positions else None,
            }
        )
    total = max(len(queries), 1)
    return {
        "task": "official_document_rag_retrieval",
        "method": "metadata + curated official-document chunks; lexical TF-IDF style ranking",
        "query_count": len(queries),
        "hit_at_1": round(hit_at_1 / total, 4),
        "hit_at_3": round(hit_at_3 / total, 4),
        "hit_at_5": round(hit_at_5 / total, 4),
        "important_note": "This evaluates whether the MVP retrieves the intended official guidance category, not factual legal correctness.",
        "queries": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and evaluate official-document RAG corpus for the jeonse risk MVP.")
    parser.add_argument("--rag-docs", type=Path, default=DEFAULT_RAG_DOCS)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    documents = load_json(args.rag_docs)
    sources = load_json(args.sources)
    chunks = flatten_chunks(documents, sources)
    evaluation = evaluate(chunks)
    manifest = {
        "source_documents": str(args.rag_docs),
        "source_catalog": str(args.sources),
        "chunk_count": len(chunks),
        "document_count": len(documents),
        "source_count": len(sources),
        "copyright_policy": "The repository stores MVP summaries, metadata, chunk ids, and official URLs. Full third-party PDFs are not copied into Git.",
        "core_sources": [
            {
                "id": source.get("id"),
                "name": source.get("required_item") or source.get("title"),
                "official_url": source.get("official_url"),
                "leaflet_url": source.get("leaflet_url"),
                "mobile_apply_url": source.get("mobile_apply_url"),
                "source_type": source.get("source_type"),
            }
            for source in sources
        ],
    }
    write_jsonl(args.output_dir / "official_rag_corpus.jsonl", chunks)
    write_json(args.output_dir / "official_rag_manifest.json", manifest)
    write_json(args.output_dir / "official_rag_retrieval_eval.json", evaluation)
    print(json.dumps({
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "hit_at_5": evaluation["hit_at_5"],
        "output_dir": str(args.output_dir),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
