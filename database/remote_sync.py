from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import requests

from database.database import connect


def _secret(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value
    try:
        import streamlit as st
        return str(st.secrets.get(name, "") or "")
    except Exception:
        return ""


def _config() -> tuple[str, str]:
    return _secret("SUPABASE_URL").rstrip("/"), _secret("SUPABASE_ANON_KEY")


def _should_sync(force: bool) -> bool:
    if force:
        return True
    with connect() as connection:
        row = connection.execute("SELECT last_synced_at FROM collector_sync_state WHERE id = 1").fetchone()
    if not row or not row["last_synced_at"]:
        return True
    try:
        last = datetime.fromisoformat(str(row["last_synced_at"]))
        return datetime.now() - last >= timedelta(minutes=20)
    except ValueError:
        return True


def sync_remote_questions(force: bool = False) -> dict[str, object]:
    url, key = _config()
    if not url or not key:
        return {"configured": False, "synced": 0, "message": "Supabase não configurado"}
    if not _should_sync(force):
        return {"configured": True, "synced": 0, "message": "Sincronização recente"}

    response = requests.get(
        f"{url}/rest/v1/questions_catalog",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        params={
            "select": "*",
            "status": "eq.published",
            "order": "created_at.asc",
            "limit": "5000",
        },
        timeout=60,
    )
    response.raise_for_status()
    rows = response.json()
    synced = 0
    with connect() as connection:
        for row in rows:
            options = row.get("options") or {}
            if isinstance(options, str):
                options = json.loads(options)
            tags = row.get("tags") or []
            if isinstance(tags, list):
                tags = ",".join(str(tag) for tag in tags)
            values = (
                row.get("contest") or "Concurso",
                row.get("bank") or "Banca não informada",
                row.get("subject") or "Conhecimentos Gerais",
                row.get("topic") or "Geral",
                row.get("subtopic") or "",
                row.get("difficulty") or "Média",
                row.get("statement") or "",
                options.get("A", ""), options.get("B", ""), options.get("C", ""), options.get("D", ""), options.get("E"),
                row.get("answer") or "A",
                row.get("explanation") or "",
                tags,
                row.get("organization") or "",
                row.get("cargo") or "",
                row.get("year"),
                row.get("source_url") or "",
                row.get("source_kind") or "ai_original",
                row.get("license_name") or "",
                row.get("status") or "published",
                float(row.get("confidence") or 0),
                row.get("source_uid") or "",
                row.get("official_number"),
            )
            connection.execute(
                """
                INSERT INTO questions(
                    concurso, banca, subject, assunto, subassunto, dificuldade,
                    statement, option_a, option_b, option_c, option_d, option_e,
                    answer, explanation, tags, organization, cargo, year,
                    source_url, source_kind, license_name, status, confidence,
                    source_uid, official_number, created_at, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                ON CONFLICT(source_uid) DO UPDATE SET
                    subject=excluded.subject, assunto=excluded.assunto, subassunto=excluded.subassunto,
                    dificuldade=excluded.dificuldade, statement=excluded.statement,
                    option_a=excluded.option_a, option_b=excluded.option_b, option_c=excluded.option_c,
                    option_d=excluded.option_d, option_e=excluded.option_e, answer=excluded.answer,
                    explanation=excluded.explanation, tags=excluded.tags, status=excluded.status,
                    confidence=excluded.confidence, imported_at=datetime('now')
                """,
                values,
            )
            synced += 1
        connection.execute(
            """
            INSERT INTO collector_sync_state(id, last_synced_at, last_count, last_error)
            VALUES (1, datetime('now'), ?, NULL)
            ON CONFLICT(id) DO UPDATE SET last_synced_at=datetime('now'), last_count=excluded.last_count, last_error=NULL
            """,
            (synced,),
        )
        connection.commit()
    return {"configured": True, "synced": synced, "message": "Sincronização concluída"}
