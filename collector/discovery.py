from __future__ import annotations

from urllib.parse import urljoin, urldefrag

from bs4 import BeautifulSoup

from collector.http_client import HttpClient
from collector.models import DocumentLink, SourceConfig

KEYWORDS = {
    "answer": ("gabarito", "resposta", "padrão definitivo"),
    "exam": ("caderno de prova", "caderno de provas", "prova objetiva", "provas objetivas", "prova"),
    "notice": ("edital", "conteúdo programático", "programa"),
}


def classify_document(title: str, url: str) -> str:
    text = f"{title} {url}".lower()
    for kind, words in KEYWORDS.items():
        if any(word in text for word in words):
            return kind
    return "reference"


def discover_documents(source: SourceConfig, client: HttpClient) -> list[DocumentLink]:
    response = client.get(source.page_url)
    soup = BeautifulSoup(response.text, "html.parser")
    found: dict[str, DocumentLink] = {}

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
        looks_relevant = (
            absolute.lower().endswith(".pdf")
            or "/view" in absolute.lower()
            or kind != "reference"
            or any(token in searchable for token in ("concurso", "seleção externa", "selecao externa"))
        )
        if looks_relevant:
            found[absolute] = DocumentLink(source.source_id, title[:240], absolute, kind)

    if source.page_url not in found:
        found[source.page_url] = DocumentLink(source.source_id, source.name, source.page_url, "reference")

    priority = {"exam": 0, "answer": 1, "notice": 2, "reference": 3}
    return sorted(found.values(), key=lambda item: (priority.get(item.kind, 9), item.title))[: source.max_documents]
