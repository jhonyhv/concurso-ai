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
MIN_SOURCE_CHARS = 1200
MAX_EXCERPT_CHARS = 7000
MAX_QUESTIONS_PER_REQUEST = 3
MAX_COMPLETION_TOKENS = 2400
RETRY_EXCERPT_CHARS = 3800
RETRY_QUESTIONS = 2
RETRY_COMPLETION_TOKENS = 1600
LOGGER = logging.getLogger("concursoai.collector.ai")


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value.lower()).strip()


def _indexable(value: str) -> str:
    """Normaliza acentos sem compactar espaços, preservando índices aproximados."""
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()


def _source_excerpt(text: str, limit: int = MAX_EXCERPT_CHARS) -> str:
    """Seleciona trechos programáticos relevantes em vez do início administrativo do edital."""
    cleaned = re.sub(r"\n{3,}", "\n\n", text.replace("\x00", " ")).strip()
    if len(cleaned) <= limit:
        return cleaned

    indexed = _indexable(cleaned)
    anchors = (
        "conhecimentos bancarios",
        "conhecimentos de informatica",
        "vendas e negociacao",
        "matematica financeira",
        "probabilidade e estatistica",
        "lingua portuguesa",
        "lingua inglesa",
        "conteudos programaticos",
        "conteudo programatico",
    )

    windows: list[tuple[int, int]] = []
    for anchor in anchors:
        position = indexed.rfind(anchor)
        if position < 0:
            continue
        start = max(0, position - 350)
        end = min(len(cleaned), position + 1900)
        if any(start < existing_end and end > existing_start for existing_start, existing_end in windows):
            continue
        windows.append((start, end))

    if not windows:
        return cleaned[:limit]

    excerpts: list[str] = []
    used = 0
    for start, end in windows:
        snippet = cleaned[start:end].strip()
        separator = "\n\n--- TRECHO PROGRAMÁTICO ---\n\n" if excerpts else ""
        available = limit - used - len(separator)
        if available <= 0:
            break
        excerpts.append(separator + snippet[:available])
        used += len(separator) + min(len(snippet), available)

    result = "".join(excerpts).strip()
    return result or cleaned[:limit]


def _uid(source: SourceConfig, statement: str, options: dict[str, str]) -> str:
    raw = source.source_id + "|" + _normalized(statement) + "|" + "|".join(
        _normalized(options[key]) for key in sorted(options)
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _extract_json(content: str) -> list[dict]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I | re.S)
    payload = json.loads(cleaned)

    if isinstance(payload, dict):
        questions = payload.get("questions")
        if not isinstance(questions, list):
            raise ValueError("O objeto JSON não contém a lista 'questions'.")
        return questions

    # Compatibilidade com respostas antigas em formato de array.
    if isinstance(payload, list):
        return payload

    raise ValueError("Resposta JSON inesperada.")


def _build_prompt(
    source: SourceConfig,
    document: ExtractedDocument,
    source_text: str,
    quantity: int,
) -> str:
    return f"""
Crie até {quantity} questões INÉDITAS para uma plataforma de preparação para concursos.
Não copie frases longas nem reproduza questões existentes. Use somente informações presentes nos trechos abaixo.
{source.style_notes}

Toda afirmação do enunciado, da resposta correta e da explicação deve ser verificável nos trechos fornecidos.
Não acrescente produtos, tarifas, limites, valores, datas, percentuais, benefícios ou regras ausentes.
Produza menos questões quando o conteúdo sustentar poucos itens confiáveis.

Fonte oficial: {document.title}
Órgão: {source.organization}
Concurso: {source.contest}
Banca/estilo: {source.bank}
URL de origem: {document.url}

Retorne SOMENTE um objeto JSON válido no formato:
{{"questions": [{{"subject": "...", "topic": "...", "subtopic": "...", "difficulty": "Fácil|Média|Difícil", "statement": "...", "options": {{"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}}, "answer": "A-E", "explanation": "...", "tags": ["..."], "cargo": "Agente Comercial", "year": 2022}}]}}

A explicação deve justificar a correta com base na fonte e apontar por que a principal alternativa-distratora está errada.
Garanta apenas uma resposta correta e cinco alternativas plausíveis.

TRECHOS SELECIONADOS DA FONTE:
{source_text}
""".strip()


def _request_groq(
    api_key: str,
    model: str,
    prompt: str,
    max_completion_tokens: int,
) -> requests.Response:
    return requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você elabora questões de concursos usando somente a fonte fornecida. "
                        "Responda exclusivamente com um objeto JSON válido contendo a chave questions."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_completion_tokens": max_completion_tokens,
            "response_format": {"type": "json_object"},
            "reasoning_format": "hidden",
            "reasoning_effort": "low",
        },
        timeout=90,
    )


def _decode_response(response: requests.Response) -> tuple[list[dict], str]:
    payload = response.json()
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("A Groq não retornou escolhas.")

    choice = choices[0]
    finish_reason = str(choice.get("finish_reason") or "")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("A Groq não retornou uma mensagem válida.")

    content = str(message.get("content") or "").strip()
    if not content:
        raise ValueError("A Groq retornou conteúdo vazio.")
    if finish_reason == "length":
        raise ValueError("A resposta da Groq foi interrompida por limite de saída.")

    return _extract_json(content), finish_reason


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
    requested_quantity = max(1, min(quantity, MAX_QUESTIONS_PER_REQUEST))
    attempts = (
        (requested_quantity, MAX_EXCERPT_CHARS, MAX_COMPLETION_TOKENS),
        (min(requested_quantity, RETRY_QUESTIONS), RETRY_EXCERPT_CHARS, RETRY_COMPLETION_TOKENS),
    )

    started = time.perf_counter()
    data: list[dict] | None = None
    last_error: Exception | None = None

    for attempt_number, (attempt_quantity, excerpt_limit, output_limit) in enumerate(attempts, start=1):
        source_text = _source_excerpt(document.text, excerpt_limit)
        prompt = _build_prompt(source, document, source_text, attempt_quantity)
        LOGGER.info(
            "Enviando à Groq: tentativa=%s questões=%s trecho=%s caracteres limite_saida=%s modo=json_object",
            attempt_number,
            attempt_quantity,
            len(source_text),
            output_limit,
        )

        response = _request_groq(api_key, model, prompt, output_limit)
        if not response.ok:
            last_error = RuntimeError(
                f"Groq HTTP {response.status_code}: {response.text[:500]}"
            )
            retryable = response.status_code in {413, 429, 500, 502, 503, 504}
            if retryable and attempt_number < len(attempts):
                LOGGER.warning(
                    "Groq recusou a tentativa %s; repetindo com contexto e saída menores.",
                    attempt_number,
                )
                continue
            raise last_error

        try:
            data, finish_reason = _decode_response(response)
            LOGGER.info(
                "Resposta JSON válida recebida da Groq: tentativa=%s itens=%s finish_reason=%s",
                attempt_number,
                len(data),
                finish_reason or "não informado",
            )
            break
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt_number < len(attempts):
                LOGGER.warning(
                    "Resposta JSON inválida ou truncada na tentativa %s (%s); repetindo com lote menor.",
                    attempt_number,
                    exc,
                )
                continue
            raise RuntimeError(f"A Groq não retornou JSON válido após nova tentativa: {exc}") from exc

    if data is None:
        raise RuntimeError(f"A Groq não retornou questões: {last_error}")

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
        if len({value.casefold() for value in options.values()}) != 5:
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
                tags=[str(tag) for tag in item.get("tags", [])][:12]
                + [source.source_id, "inédita_ia"],
                source_url=document.url,
                source_kind="ai_original",
                license_name=source.license_name,
                status="pending_review",
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
