from __future__ import annotations

import logging

from collector.ai_generator import generate_original_questions
from collector.config import enabled_sources
from collector.discovery import discover_documents
from collector.http_client import HttpClient
from collector.models import CandidateQuestion, ExtractedDocument, SourceConfig
from collector.pdf_reader import extract_document
from collector.question_parser import pair_official_questions
from collector.source_quality import assess_generation_document
from collector.storage import SupabaseStorage

LOGGER = logging.getLogger("concursoai.collector")


def _generation_documents(documents: list[ExtractedDocument]) -> list[ExtractedDocument]:
    ordered = sorted(documents, key=lambda document: -len(document.text))
    eligible: list[ExtractedDocument] = []
    for document in ordered:
        accepted, reason = assess_generation_document(document)
        if accepted:
            LOGGER.info(
                "Fonte aprovada para geração: tipo=%s caracteres=%s url=%s (%s)",
                document.kind,
                len(document.text),
                document.url,
                reason,
            )
            eligible.append(document)
        else:
            LOGGER.info(
                "Fonte bloqueada para geração: tipo=%s caracteres=%s url=%s motivo=%s",
                document.kind,
                len(document.text),
                document.url,
                reason,
            )

    # O edital fundamenta o conteúdo programático; as provas fornecem o padrão
    # de cobrança da banca. Essa combinação reduz alucinações e duplicidades.
    notices = [document for document in eligible if document.kind == "notice"]
    exams = [document for document in eligible if document.kind == "exam"]
    selected = notices[:1] + exams[:2]

    if len(selected) < 3:
        selected_urls = {document.url for document in selected}
        selected.extend(
            document
            for document in eligible
            if document.url not in selected_urls
        )
    return selected[:3]


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
        LOGGER.info("Documentos de qualidade selecionados para a Groq: %s", len(generation_docs))
        for document in generation_docs:
            try:
                generated = generate_original_questions(source, document, max_questions_per_document)
                questions.extend(generated)
                LOGGER.info("Questões inéditas aceitas para %s: %s", document.url, len(generated))
            except Exception as exc:
                LOGGER.warning("Falha na geração para %s: %s", document.url, exc)

    unique = {question.source_uid: question for question in questions}
    saved = storage.upsert_questions(unique.values())
    LOGGER.info(
        "%s concluído: documentos=%s questões_salvas=%s",
        source.source_id,
        len(documents),
        saved,
    )
    return {"documents": len(documents), "questions": saved}


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
