from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import requests
import streamlit as st

from database.database import connect, get_settings, load_df

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"


@dataclass(frozen=True)
class AIConfig:
    api_key: str
    model: str
    provider: str = "Groq"
    endpoint: str = GROQ_API_URL


@dataclass(frozen=True)
class AIResult:
    content: str
    provider: str
    model: str
    latency_ms: int


def _secret_value(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value)
        ai_section = st.secrets.get("ai", {})
        if isinstance(ai_section, dict) and ai_section.get(name):
            return str(ai_section[name])
    except Exception:
        pass
    return str(os.getenv(name, "") or "")


def get_ai_config() -> AIConfig:
    settings = get_settings()
    model = str(settings.get("ai_model") or _secret_value("GROQ_MODEL") or DEFAULT_MODEL)
    return AIConfig(api_key=_secret_value("GROQ_API_KEY"), model=model)


def ai_available() -> bool:
    return bool(get_ai_config().api_key.strip())


def _student_context(subject: str) -> str:
    condition = "" if subject == "Todas" else "WHERE q.subject = ?"
    params: tuple[Any, ...] = () if subject == "Todas" else (subject,)
    stats = load_df(
        f"""
        SELECT COUNT(a.id) AS attempts,
               COALESCE(ROUND(100.0 * AVG(a.correct), 1), 0) AS accuracy,
               COALESCE(SUM(CASE WHEN a.correct = 0 THEN 1 ELSE 0 END), 0) AS errors
          FROM attempts a
          JOIN questions q ON q.id = a.question_id
          {condition}
        """,
        params,
    ).iloc[0]

    weak_topics = load_df(
        f"""
        SELECT q.subject, COALESCE(q.assunto, 'Geral') AS assunto,
               COUNT(a.id) AS attempts,
               ROUND(100.0 * AVG(a.correct), 1) AS accuracy
          FROM attempts a
          JOIN questions q ON q.id = a.question_id
          {condition}
         GROUP BY q.subject, q.assunto
         HAVING COUNT(a.id) > 0
         ORDER BY accuracy ASC, attempts DESC
         LIMIT 5
        """,
        params,
    )

    errors = load_df(
        f"""
        SELECT q.subject, COALESCE(q.assunto, 'Geral') AS assunto,
               q.statement, q.answer, q.explanation, e.error_count
          FROM error_notebook e
          JOIN questions q ON q.id = e.question_id
          {condition.replace('WHERE', 'WHERE') if condition else ''}
         ORDER BY e.reviewed ASC, e.error_count DESC, e.last_error_at DESC
         LIMIT 5
        """,
        params,
    )

    lines = [
        f"Escopo: {subject}",
        f"Questões respondidas: {int(stats['attempts'])}",
        f"Aproveitamento: {float(stats['accuracy']):.1f}%",
        f"Erros acumulados: {int(stats['errors'])}",
    ]
    if not weak_topics.empty:
        lines.append("Pontos com menor aproveitamento:")
        for row in weak_topics.itertuples(index=False):
            lines.append(f"- {row.subject} / {row.assunto}: {float(row.accuracy):.1f}% em {int(row.attempts)} tentativa(s)")
    if not errors.empty:
        lines.append("Erros recentes relevantes:")
        for row in errors.itertuples(index=False):
            explanation = str(row.explanation or "Sem explicação cadastrada")
            lines.append(
                f"- [{row.subject} / {row.assunto}] {row.statement} | Gabarito: {row.answer} | "
                f"Explicação: {explanation} | Erros: {int(row.error_count)}"
            )
    return "\n".join(lines)


def _system_prompt(subject: str, response_style: str) -> str:
    return f"""
Você é o Professor IA do ConcursoAI, especializado em preparação para concursos públicos brasileiros,
com foco atual no Banco do Brasil e na banca Cesgranrio.

Regras:
- Responda em português do Brasil, com clareza e precisão.
- Use o contexto de desempenho do aluno, mas não invente dados ausentes.
- Quando explicar conteúdo, apresente conceito, exemplo curto e armadilha de prova.
- Quando recomendar estudo, dê uma sequência prática e mensurável.
- Não trate orientação educacional como garantia de aprovação.
- Se a pergunta depender de informação atual não fornecida, avise que precisa de fonte atualizada.
- Formato desejado: {response_style}.
- Matéria selecionada: {subject}.
""".strip()


def _log_usage(provider: str, model: str, latency_ms: int, success: bool, error: str = "") -> None:
    try:
        with connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_usage(provider, model, latency_ms, success, error_message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (provider, model, int(latency_ms), int(success), error[:500]),
            )
            connection.commit()
    except Exception:
        pass


def chat_completion(
    prompt: str,
    subject: str,
    response_style: str = "explicação didática e objetiva",
    history: list[dict[str, str]] | None = None,
) -> AIResult:
    config = get_ai_config()
    if not config.api_key:
        raise RuntimeError("A chave GROQ_API_KEY não foi configurada.")

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _system_prompt(subject, response_style)},
        {"role": "system", "content": "Contexto do aluno:\n" + _student_context(subject)},
    ]
    for message in (history or [])[-8:]:
        role = str(message.get("role", ""))
        content = str(message.get("content", ""))
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})

    started = time.perf_counter()
    try:
        response = requests.post(
            config.endpoint,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.model,
                "messages": messages,
                "temperature": 0.35,
                "max_completion_tokens": 1200,
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        content = str(payload["choices"][0]["message"]["content"]).strip()
        latency_ms = int((time.perf_counter() - started) * 1000)
        _log_usage(config.provider, config.model, latency_ms, True)
        return AIResult(content=content, provider=config.provider, model=config.model, latency_ms=latency_ms)
    except requests.RequestException as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        detail = str(exc)
        if getattr(exc, "response", None) is not None:
            try:
                body = exc.response.json()
                detail = body.get("error", {}).get("message") or json.dumps(body, ensure_ascii=False)
            except Exception:
                detail = exc.response.text[:500]
        _log_usage(config.provider, config.model, latency_ms, False, detail)
        raise RuntimeError(f"Falha ao consultar a IA: {detail}") from exc


def test_connection() -> AIResult:
    return chat_completion(
        "Responda apenas: conexão confirmada.",
        subject="Todas",
        response_style="uma frase curta",
        history=[],
    )
