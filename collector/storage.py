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
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not self.url or not self.key:
            raise RuntimeError(
                "SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórios "
                "para publicar automaticamente."
            )
        if self.key.startswith("sb_publishable_"):
            raise RuntimeError(
                "SUPABASE_SERVICE_ROLE_KEY recebeu uma chave publicável. "
                "Use a Secret key sb_secret_... ou a service_role legada."
            )

        self.headers = {
            "apikey": self.key,
            "Content-Type": "application/json",
        }

        # As chaves legadas service_role são JWTs e podem ser enviadas
        # no cabeçalho Authorization. As novas sb_secret_ são opacas e
        # devem ser enviadas somente no cabeçalho apikey.
        if not self.key.startswith("sb_secret_"):
            self.headers["Authorization"] = f"Bearer {self.key}"

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if response.ok:
            return
        detail = response.text[:500].strip()
        raise requests.HTTPError(
            f"Supabase retornou HTTP {response.status_code}: {detail}",
            response=response,
        )

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
            headers={
                **self.headers,
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            data=json.dumps(rows, ensure_ascii=False),
            timeout=60,
        )
        self._raise_for_status(response)
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

        # Uma questão já revisada não pode voltar para pending_review em uma
        # coleta futura. Duplicatas são ignoradas; apenas questões realmente
        # novas são inseridas na fila de revisão.
        response = requests.post(
            f"{self.url}/rest/v1/questions_catalog?on_conflict=source_uid",
            headers={
                **self.headers,
                "Prefer": "resolution=ignore-duplicates,return=representation",
            },
            data=json.dumps(rows, ensure_ascii=False),
            timeout=90,
        )
        self._raise_for_status(response)
        inserted = response.json() if response.content else []
        return len(inserted) if isinstance(inserted, list) else 0

    def log_run(
        self,
        source_id: str,
        status: str,
        documents: int,
        questions: int,
        message: str = "",
    ) -> None:
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
        self._raise_for_status(response)
