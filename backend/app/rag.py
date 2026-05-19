from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RAG_PATH = ROOT / "data" / "rag_documents_mvp.json"
OFFICIAL_RAG_CORPUS_PATH = ROOT / "data" / "rag" / "official_rag_corpus.jsonl"


def load_rag_documents(path: Path = RAG_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_official_rag_corpus(path: Path = OFFICIAL_RAG_CORPUS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    chunks = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def retrieve_evidence(risk_keys: list[str]) -> list[dict[str, Any]]:
    keys = set(risk_keys)
    corpus = load_official_rag_corpus()
    if corpus:
        evidence = []
        seen_documents = set()
        for chunk in corpus:
            if not keys.intersection(chunk.get("risk_keys", [])):
                continue
            document_id = chunk.get("document_id") or chunk.get("title")
            if document_id in seen_documents:
                continue
            seen_documents.add(document_id)
            evidence.append({
                "title": chunk["title"],
                "provider": chunk["provider"],
                "official_url": chunk["official_url"],
                "mvp_use": chunk.get("response_rule") or chunk.get("heading", ""),
                "chunks": [{"summary": chunk["text"], "chunk_id": chunk["chunk_id"]}],
            })
        return evidence

    evidence = []
    for document in load_rag_documents():
        if keys.intersection(document.get("risk_keys", [])):
            evidence.append({
                "title": document["title"],
                "provider": document["provider"],
                "official_url": document["official_url"],
                "mvp_use": document["mvp_use"],
                "chunks": document.get("chunks", [])[:2],
            })
    return evidence
