from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests


def _secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        import streamlit as st

        return str(st.secrets.get(name, "") or "").strip()
    except Exception:
        return ""


def admin_password() -> str:
    return _secret("ADMIN_PASSWORD")


def _config() -> tuple[str, str]:
    return (
        _secret("SUPABASE_URL").rstrip("/"),
        _secret("SUPABASE_SERVICE_ROLE_KEY"),
    )


def _headers(*, count: bool = False, return_representation: bool = False) -> dict[str, str]:
    _, key = _config()
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
    }
    # A chave legada service_role é um JWT. A nova sb_secret_ é opaca
    # e deve ser enviada somente em apikey.
    if key and not key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {key}"
    if count:
        headers["Prefer"] = "count=exact"
    elif return_representation:
        headers["Prefer"] = "return=representation"
    else:
        headers["Prefer"] = "return=minimal"
    return headers


def review_admin_configured() -> bool:
    url, key = _config()
    return bool(url and key and admin_password())


def _raise_for_status(response: requests.Response) -> None:
    if response.ok:
        return
    detail = response.text[:600].strip()
    raise requests.HTTPError(
        f"Supabase retornou HTTP {response.status_code}: {detail}",
        response=response,
    )


def count_questions(status: str) -> int:
    url, _ = _config()
    response = requests.get(
        f"{url}/rest/v1/questions_catalog",
        headers={**_headers(count=True), "Range": "0-0"},
        params={"select": "id", "status": f"eq.{status}", "limit": "1"},
        timeout=30,
    )
    _raise_for_status(response)
    content_range = response.headers.get("content-range", "0-0/0")
    try:
        return int(content_range.rsplit("/", 1)[-1])
    except (TypeError, ValueError):
        return 0


def fetch_questions(status: str = "pending_review", limit: int = 40) -> list[dict[str, Any]]:
    url, _ = _config()
    response = requests.get(
        f"{url}/rest/v1/questions_catalog",
        headers=_headers(),
        params={
            "select": "*",
            "status": f"eq.{status}",
            "order": "created_at.desc,id.desc",
            "limit": str(max(1, min(limit, 100))),
        },
        timeout=45,
    )
    _raise_for_status(response)
    data = response.json()
    return data if isinstance(data, list) else []


def update_question(question_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "subject",
        "topic",
        "subtopic",
        "difficulty",
        "statement",
        "options",
        "answer",
        "explanation",
        "tags",
        "cargo",
        "year",
        "status",
        "confidence",
    }
    clean_payload = {key: value for key, value in payload.items() if key in allowed}
    clean_payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    url, _ = _config()
    response = requests.patch(
        f"{url}/rest/v1/questions_catalog",
        headers=_headers(return_representation=True),
        params={"id": f"eq.{int(question_id)}"},
        json=clean_payload,
        timeout=45,
    )
    _raise_for_status(response)
    rows = response.json()
    if not rows:
        raise RuntimeError("A questão não foi encontrada ou não pôde ser atualizada.")
    return dict(rows[0])
