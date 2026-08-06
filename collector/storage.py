from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Iterable

import requests

from collector.models import CandidateQuestion, ExtractedDocument


class SupabaseStorage:
    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not self.url or not self.key:
            raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórios para publicar automaticamente.")
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }

    def upsert_documents(self, documents: Iterable[ExtractedDocument]) -> int:
        rows = [
            {
                "source_id": doc.source_id,
                "title": doc.title,
                "url": doc.url,
                "document_kind": doc.kind,
                "content_hash": doc.content_hash,
                "content_type": doc.content_type,
                "extraction_confidence": doc.confidence,
                "text_length": len(doc.text),
                "metadata": doc.metadata,
            }
            for doc in documents
        ]
        if not rows:
            return 0
        response = requests.post(
            f"{self.url}/rest/v1/source_documents?on_conflict=content_hash",
            headers=self.headers,
            data=json.dumps(rows, ensure_ascii=False),
            timeout=60,
        )
        response.raise_for_status()
        return len(rows)

    def upsert_questions(self, questions: Iterable[CandidateQuestion]) -> int:
        rows = []
        for question in questions:
            row = asdict(question)
            row["options"] = question.options
            row["tags"] = question.tags
            rows.append(row)
        if not rows:
            return 0
        response = requests.post(
            f"{self.url}/rest/v1/questions_catalog?on_conflict=source_uid",
            headers=self.headers,
            data=json.dumps(rows, ensure_ascii=False),
            timeout=90,
        )
        response.raise_for_status()
        return len(rows)

    def log_run(self, source_id: str, status: str, documents: int, questions: int, message: str = "") -> None:
        response = requests.post(
            f"{self.url}/rest/v1/collector_runs",
            headers={**self.headers, "Prefer": "return=minimal"},
            json={
                "source_id": source_id,
                "status": status,
                "documents_found": documents,
                "questions_published": questions,
                "message": message[:1500],
            },
            timeout=30,
        )
        response.raise_for_status()
