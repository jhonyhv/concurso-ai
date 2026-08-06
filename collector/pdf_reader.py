from __future__ import annotations

import hashlib
import io
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pypdf import PdfReader

from collector.http_client import HttpClient
from collector.models import DocumentLink, ExtractedDocument


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    pages: list[str] = []
    for page in reader.pages[:120]:
        pages.append(page.extract_text() or "")
    return _clean_text("\n".join(pages))


def _html_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "nav", "footer"]):
        element.decompose()
    return _clean_text(soup.get_text("\n", strip=True))


def extract_document(link: DocumentLink, client: HttpClient) -> ExtractedDocument:
    response = client.get(link.url)
    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    final_url = response.url
    content = response.content

    if "html" in content_type and not final_url.lower().endswith(".pdf"):
        soup = BeautifulSoup(response.text, "html.parser")
        pdf_anchor = soup.select_one(
            'a[href$=".pdf"], a[href*=".pdf?"], iframe[src$=".pdf"], embed[src$=".pdf"]'
        )
        if pdf_anchor:
            attr = "href" if pdf_anchor.has_attr("href") else "src"
            resolved = urljoin(final_url, str(pdf_anchor.get(attr)))
            nested = client.get(resolved)
            nested_type = nested.headers.get("content-type", "").split(";", 1)[0].lower()
            if "pdf" in nested_type or nested.url.lower().endswith(".pdf"):
                final_url, content, content_type = nested.url, nested.content, "application/pdf"

    if "pdf" in content_type or final_url.lower().endswith(".pdf") or content[:4] == b"%PDF":
        text = _pdf_text(content)
        confidence = 1.0 if len(text) >= 1200 else 0.35
        content_type = "application/pdf"
    else:
        text = _html_text(response.text)
        confidence = 0.95 if len(text) >= 500 else 0.5
        content_type = "text/html"

    digest = hashlib.sha256(content).hexdigest()
    return ExtractedDocument(
        source_id=link.source_id,
        title=link.title,
        url=final_url,
        kind=link.kind,
        text=text,
        content_hash=digest,
        content_type=content_type,
        confidence=confidence,
        metadata={"bytes": len(content)},
    )
