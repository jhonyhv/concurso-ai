from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin, urldefrag

from bs4 import BeautifulSoup

from collector.http_client import HttpClient
from collector.models import DocumentLink, SourceConfig

KEYWORDS = {
    "answer": ("gabarito", "resposta", "padrão definitivo", "padrao definitivo"),
    "exam": (
        "caderno de prova",
        "caderno de provas",
        "prova objetiva",
        "provas objetivas",
        "prova",
    ),
    "notice": (
        "edital",
        "conteúdo programático",
        "conteudo programatico",
        "programa de provas",
        "regulamento",
        "normativo",
    ),
}

BLOCKED_DISCOVERY_TERMS = (
    "convocacao",
    "convocação",
    "posse",
    "portal-da-transparencia",
    "portal da transparência",
    "trabalhe-conosco",
    "noticia",
    "notícia",
    "imprensa",
)

OFFICIAL_SEEDS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "bb_concurso": (
        (
            "Edital no 01 - Seleção Externa Banco do Brasil 2022/001",
            "https://www.bb.com.br/docs/portal/dipes/Edital-de-Abertura-de-Selecao-Externa-2022-01.pdf",
            "notice",
        ),
    ),
}


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value.lower()).strip()


def classify_document(title: str, url: str) -> str:
    title_text = _normalized(title)
    text = _normalized(f"{title} {url}")

    # Na página da Cesgranrio, os cadernos são nomeados como
    # "PROVA A ... GABARITO 1". Eles continuam sendo provas, não gabaritos.
    if (
        re.search(r"\bprova\s+[abc]\b", title_text)
        and "agente comercial" in title_text
        and not title_text.startswith("gabarito")
        and not title_text.startswith("gabaritos")
    ):
        return "exam"

    for kind, words in KEYWORDS.items():
        if any(_normalized(word) in text for word in words):
            return kind
    return "reference"


def _bb_exam_letter(document: DocumentLink) -> str | None:
    match = re.search(r"\bprova\s+([abc])\b", _normalized(document.title))
    return match.group(1).upper() if match else None


def _bb_document_allowed(document: DocumentLink) -> bool:
    text = _normalized(f"{document.title} {document.url}")
    if "agente de tecnologia" in text or "microrregiao 158" in text:
        return False

    if document.kind == "exam":
        return "agente comercial" in text
    if document.kind == "answer":
        return "agente comercial" in text and "gabarito" in text
    if document.kind == "notice":
        return (
            "edital no 01" in text
            or "conteudo programatico" in text
            or "programa de provas" in text
        )
    return document.kind == "reference"


def _select_bb_documents(documents: list[DocumentLink], limit: int) -> list[DocumentLink]:
    selected: list[DocumentLink] = []

    # Mantém suporte a provas oficiais caso o BB passe a hospedá-las diretamente.
    exams = [document for document in documents if document.kind == "exam"]
    for letter in ("A", "B", "C"):
        candidates = [document for document in exams if _bb_exam_letter(document) == letter]
        candidates.sort(
            key=lambda document: (
                "gabarito 1" not in _normalized(document.title),
                document.title,
            )
        )
        if candidates:
            selected.append(candidates[0])

    answers = [document for document in documents if document.kind == "answer"]
    for letter in ("A", "B", "C"):
        candidates = [document for document in answers if _bb_exam_letter(document) == letter]
        candidates.sort(
            key=lambda document: (
                "alterado" not in _normalized(document.title),
                document.title,
            )
        )
        if candidates:
            selected.append(candidates[0])

    notices = [document for document in documents if document.kind == "notice"]
    notices.sort(
        key=lambda document: (
            "edital no 01" not in _normalized(document.title),
            document.title,
        )
    )
    if notices:
        selected.append(notices[0])

    references = [document for document in documents if document.kind == "reference"]
    if references:
        selected.append(references[0])

    unique = {document.url: document for document in selected}
    return list(unique.values())[:limit]


def discover_documents(source: SourceConfig, client: HttpClient) -> list[DocumentLink]:
    response = client.get(source.page_url)
    soup = BeautifulSoup(response.text, "html.parser")
    found: dict[str, DocumentLink] = {}

    for title, url, kind in OFFICIAL_SEEDS.get(source.source_id, ()):
        if client.domain_allowed(url, source.allowed_domains):
            found[url] = DocumentLink(source.source_id, title, url, kind)

    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith(("mailto:", "javascript:", "#")):
            continue
        absolute = urldefrag(urljoin(response.url, href)).url
        if not client.domain_allowed(absolute, source.allowed_domains):
            continue

        title = " ".join(anchor.get_text(" ", strip=True).split()) or absolute.rsplit("/", 1)[-1]
        kind = classify_document(title, absolute)
        searchable = f"{title} {absolute}".lower()
        if any(term in searchable for term in BLOCKED_DISCOVERY_TERMS):
            continue

        document = DocumentLink(source.source_id, title[:240], absolute, kind)
        if source.source_id == "bb_concurso" and not _bb_document_allowed(document):
            continue

        looks_relevant = (
            absolute.lower().endswith(".pdf")
            or "/view" in absolute.lower()
            or kind != "reference"
        )
        if looks_relevant:
            found[absolute] = document

    if source.page_url not in found:
        found[source.page_url] = DocumentLink(source.source_id, source.name, source.page_url, "reference")

    documents = list(found.values())
    if source.source_id == "bb_concurso":
        return _select_bb_documents(documents, source.max_documents)

    priority = {"exam": 0, "answer": 1, "notice": 2, "reference": 3}
    return sorted(documents, key=lambda item: (priority.get(item.kind, 9), item.title))[: source.max_documents]
