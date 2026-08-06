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

    # O edital fundamenta o conteúdo programático; provas oficiais, quando
    # disponíveis, complementam o padrão de cobrança da banca.
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


def collect_source(
    source: SourceConfig,
    storage: SupabaseStorage,
    max_questions_per_document: int = 5,
) -> dict[str, int]:
    client = HttpClient()
    links = discover_documents(source, client)
    LOGGER.info("%s: %s link(s) oficial(is) descoberto(s)", source.source_id, len(links))
    if not links:
        raise RuntimeError(f"{source.source_id}: nenhuma fonte oficial foi descoberta")

    documents: list[ExtractedDocument] = []
    extraction_errors: list[str] = []
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
            extraction_errors.append(f"{link.url}: {exc}")
            LOGGER.warning("Falha ao extrair %s: %s", link.url, exc)

    if not documents:
        detail = "; ".join(extraction_errors[:3]) or "nenhum documento retornou texto"
        raise RuntimeError(f"{source.source_id}: nenhuma fonte pôde ser extraída ({detail})")

    storage.upsert_documents(documents)
    questions: list[CandidateQuestion] = []

    exams = [doc for doc in documents if doc.kind == "exam" and doc.confidence >= 0.8]
    answers = [doc for doc in documents if doc.kind == "answer" and doc.confidence >= 0.8]
    official_questions = pair_official_questions(source, exams, answers)
    questions.extend(official_questions)
    LOGGER.info("Questões oficiais pareadas: %s", len(official_questions))

    generated_count = 0
    if source.mode == "generate_original":
        generation_docs = _generation_documents(documents)
        LOGGER.info("Documentos de qualidade selecionados para a Groq: %s", len(generation_docs))
        if not generation_docs and not official_questions:
            raise RuntimeError(
                f"{source.source_id}: nenhum edital, prova ou normativo passou no filtro de qualidade"
            )

        for document in generation_docs:
            try:
                generated = generate_original_questions(
                    source,
                    document,
                    max_questions_per_document,
                )
                generated_count += len(generated)
                questions.extend(generated)
                LOGGER.info("Questões inéditas aceitas para %s: %s", document.url, len(generated))
            except Exception as exc:
                LOGGER.warning("Falha na geração para %s: %s", document.url, exc)

        if generated_count == 0 and not official_questions:
            raise RuntimeError(
                f"{source.source_id}: fontes válidas foram extraídas, mas nenhuma questão foi gerada"
            )

    unique = {question.source_uid: question for question in questions}
    saved = storage.upsert_questions(unique.values())
    LOGGER.info(
        "%s concluído: documentos=%s questões_geradas=%s questões_novas=%s",
        source.source_id,
        len(documents),
        len(unique),
        saved,
    )
    return {"documents": len(documents), "questions": saved}


def run_collection() -> dict[str, dict[str, int]]:
    storage = SupabaseStorage()
    sources = enabled_sources()
    results: dict[str, dict[str, int]] = {}
    failures: dict[str, str] = {}

    for source in sources:
        try:
            result = collect_source(source, storage)
            storage.log_run(source.source_id, "success", result["documents"], result["questions"])
            results[source.source_id] = result
        except Exception as exc:
            message = str(exc)
            failures[source.source_id] = message
            storage.log_run(source.source_id, "error", 0, 0, message)
            LOGGER.exception("Coleta falhou para %s", source.source_id)
            results[source.source_id] = {"documents": 0, "questions": 0}

    if sources and len(failures) == len(sources):
        summary = "; ".join(f"{source_id}: {message}" for source_id, message in failures.items())
        raise RuntimeError(f"Todas as fontes habilitadas falharam: {summary}")

    return results
