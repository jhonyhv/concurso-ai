from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import unicodedata

import requests

from collector.models import CandidateQuestion, ExtractedDocument, SourceConfig

API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"
MIN_SOURCE_CHARS = 250
LOGGER = logging.getLogger("concursoai.collector.ai")


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value.lower()).strip()


def _uid(source: SourceConfig, statement: str, options: dict[str, str]) -> str:
    raw = source.source_id + "|" + _normalized(statement) + "|" + "|".join(_normalized(options[key]) for key in sorted(options))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _extract_json(content: str) -> list[dict]:
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I | re.S)
    start, end = content.find("["), content.rfind("]")
    if start < 0 or end < start:
        raise ValueError("A IA não devolveu uma lista JSON válida.")
    payload = json.loads(content[start : end + 1])
    if not isinstance(payload, list):
        raise ValueError("Resposta JSON inesperada.")
    return payload


def generate_original_questions(
    source: SourceConfig,
    document: ExtractedDocument,
    quantity: int = 5,
) -> list[CandidateQuestion]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        LOGGER.warning("GROQ_API_KEY não configurada; geração ignorada.")
        return []
    if len(document.text) < MIN_SOURCE_CHARS:
        LOGGER.warning(
            "Fonte curta demais para geração: %s (%s caracteres)",
            document.url,
            len(document.text),
        )
        return []

    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    source_text = document.text[:14000]
    prompt = f"""
Crie {quantity} questões INÉDITAS para uma plataforma de preparação para concursos.
Não copie frases longas nem reproduza questões existentes. Use apenas os conceitos e o conteúdo programático
identificáveis na fonte abaixo. {source.style_notes}

Fonte oficial: {document.title}
Órgão: {source.organization}
Concurso: {source.contest}
Banca/estilo: {source.bank}
URL de origem: {document.url}

Retorne SOMENTE um array JSON. Cada item deve possuir exatamente:
subject, topic, subtopic, difficulty (Fácil|Média|Difícil), statement,
options (objeto com A, B, C, D, E), answer (A-E), explanation, tags (array de textos), cargo, year.
A explicação deve justificar a correta e apontar por que a principal alternativa-distratora está errada.
Garanta apenas uma resposta correta e alternativas plausíveis.

CONTEÚDO DA FONTE:
{source_text}
""".strip()

    started = time.perf_counter()
    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Você é um elaborador e revisor de questões de concursos públicos brasileiros. Responda somente JSON válido.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.35,
            "max_completion_tokens": 5000,
        },
        timeout=90,
    )
    if not response.ok:
        raise RuntimeError(f"Groq HTTP {response.status_code}: {response.text[:500]}")

    payload = response.json()
    content = str(payload["choices"][0]["message"]["content"])
    data = _extract_json(content)
    candidates: list[CandidateQuestion] = []

    for item in data:
        if not isinstance(item, dict):
            continue
        raw_options = item.get("options", {})
        if not isinstance(raw_options, dict):
            continue
        options = {
            str(key).upper(): str(value).strip()
            for key, value in raw_options.items()
            if str(key).upper() in "ABCDE"
        }
        answer = str(item.get("answer", "")).upper().strip()
        statement = str(item.get("statement", "")).strip()
        if set(options) != set("ABCDE") or answer not in options or len(statement) < 25:
            continue

        candidates.append(
            CandidateQuestion(
                source_uid=_uid(source, statement, options),
                organization=source.organization,
                contest=source.contest,
                bank=source.bank,
                cargo=str(item.get("cargo") or "Agente Comercial"),
                year=int(item["year"]) if str(item.get("year", "")).isdigit() else None,
                subject=str(item.get("subject") or source.default_subject),
                topic=str(item.get("topic") or "Geral"),
                subtopic=str(item.get("subtopic") or ""),
                difficulty=str(item.get("difficulty") or "Média"),
                statement=statement,
                options=options,
                answer=answer,
                explanation=str(item.get("explanation") or ""),
                tags=[str(tag) for tag in item.get("tags", [])][:12] + [source.source_id, "inédita_ia"],
                source_url=document.url,
                source_kind="ai_original",
                license_name=source.license_name,
                status="published",
                confidence=0.9,
            )
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    LOGGER.info(
        "Groq gerou %s questão(ões) válidas para %s em %sms",
        len(candidates),
        document.url,
        elapsed_ms,
    )
    return candidates
