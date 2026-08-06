from __future__ import annotations

import hashlib
import logging

from collector.ai_generator import generate_original_questions
from collector.config import enabled_sources
from collector.discovery import discover_documents
from collector.http_client import HttpClient
from collector.models import CandidateQuestion, ExtractedDocument, SourceConfig
from collector.pdf_reader import extract_document
from collector.question_parser import pair_official_questions
from collector.storage import SupabaseStorage

LOGGER = logging.getLogger("concursoai.collector")
MIN_GENERATION_CHARS = 250


def _generation_documents(documents: list[ExtractedDocument]) -> list[ExtractedDocument]:
    ordered = sorted(
        documents,
        key=lambda doc: (doc.kind not in {"notice", "exam", "reference"}, -len(doc.text)),
    )
    eligible = [doc for doc in ordered if len(doc.text) >= MIN_GENERATION_CHARS][:3]
    if eligible:
        return eligible

    combined_text = "\n\n".join(
        f"FONTE: {doc.title}\n{doc.text}" for doc in ordered if doc.text.strip()
    ).strip()
    if len(combined_text) < MIN_GENERATION_CHARS or not ordered:
        return []

    base = ordered[0]
    return [
        ExtractedDocument(
            source_id=base.source_id,
            title="Compilado de páginas oficiais do concurso",
            url=base.url,
            kind="reference",
            text=combined_text[:18000],
            content_hash=hashlib.sha256(combined_text.encode("utf-8")).hexdigest(),
            content_type="text/plain",
            confidence=0.75,
            metadata={"composite": True, "documents": len(ordered)},
        )
    ]


def collect_source(source: SourceConfig, storage: SupabaseStorage, max_questions_per_document: int = 5) -> dict[str, int]:
    client = HttpClient()
    links = discover_documents(source, client)
    LOGGER.info("%s: %s link(s) oficial(is) descoberto(s)", source.source_id, len(links))

    documents: list[ExtractedDocument] = []
    for link in links:
        try:
            document = extract_document(link, client)
            LOGGER.info(
                "Documento extraído: tipo=%s caracteres=%s url=%s",
                document.kind,
                len(document.text),
                document.url,
            )
            if document.text:
                documents.append(document)
        except Exception as exc:
            LOGGER.warning("Falha ao extrair %s: %s", link.url, exc)

    storage.upsert_documents(documents)
    questions: list[CandidateQuestion] = []

    exams = [doc for doc in documents if doc.kind == "exam" and doc.confidence >= 0.8]
    answers = [doc for doc in documents if doc.kind == "answer" and doc.confidence >= 0.8]
    official_questions = pair_official_questions(source, exams, answers)
    questions.extend(official_questions)
    LOGGER.info("Questões oficiais pareadas: %s", len(official_questions))

    if source.mode == "generate_original":
        generation_docs = _generation_documents(documents)
        LOGGER.info("Documentos selecionados para a Groq: %s", len(generation_docs))
        for document in generation_docs:
            try:
                generated = generate_original_questions(source, document, max_questions_per_document)
                questions.extend(generated)
                LOGGER.info("Questões inéditas aceitas para %s: %s", document.url, len(generated))
            except Exception as exc:
                LOGGER.warning("Falha na geração para %s: %s", document.url, exc)

    unique = {question.source_uid: question for question in questions}
    published = storage.upsert_questions(unique.values())
    LOGGER.info(
        "%s concluído: documentos=%s questões_publicadas=%s",
        source.source_id,
        len(documents),
        published,
    )
    return {"documents": len(documents), "questions": published}


def run_collection() -> dict[str, dict[str, int]]:
    storage = SupabaseStorage()
    results: dict[str, dict[str, int]] = {}
    for source in enabled_sources():
        try:
            result = collect_source(source, storage)
            storage.log_run(source.source_id, "success", result["documents"], result["questions"])
            results[source.source_id] = result
        except Exception as exc:
            storage.log_run(source.source_id, "error", 0, 0, str(exc))
            LOGGER.exception("Coleta falhou para %s", source.source_id)
            results[source.source_id] = {"documents": 0, "questions": 0}
    return results
