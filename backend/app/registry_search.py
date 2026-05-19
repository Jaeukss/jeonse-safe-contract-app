from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_CHUNKS_PATH = ROOT / "data" / "registry" / "registry_search_chunks.jsonl"
TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "") if len(token) >= 2]


def load_registry_chunks(path: Path = REGISTRY_CHUNKS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    chunks = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def retrieve_registry_matches(
    *,
    address: str,
    legal_dong_code: str,
    housing_type: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    chunks = load_registry_chunks()
    query = " ".join(part for part in [address, legal_dong_code, housing_type] if part)
    query_tokens = Counter(tokenize(query))
    if not chunks or not query_tokens:
        return []

    doc_tokens = [Counter(tokenize(chunk.get("text", ""))) for chunk in chunks]
    document_frequency: Counter[str] = Counter()
    for counter in doc_tokens:
        document_frequency.update(counter.keys())
    idf = {
        token: math.log((len(chunks) + 1) / (df + 1)) + 1
        for token, df in document_frequency.items()
    }

    scored = []
    for chunk, counter in zip(chunks, doc_tokens):
        score = 0.0
        metadata = chunk.get("metadata", {})
        if legal_dong_code and metadata.get("legal_dong_code") == legal_dong_code:
            score += 8.0
        for token, count in query_tokens.items():
            if token in counter:
                score += (1.0 + math.log(count)) * (1.0 + math.log(counter[token])) * idf.get(token, 1.0)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)

    matches = []
    for score, chunk in scored[:limit]:
        matches.append(
            {
                "title": chunk.get("title", "Building registry record"),
                "source_type": "structured_building_registry_search",
                "score": round(score, 4),
                "text": chunk.get("text", ""),
                "metadata": chunk.get("metadata", {}),
            }
        )
    return matches
