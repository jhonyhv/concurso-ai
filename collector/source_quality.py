from __future__ import annotations

import re
import unicodedata

from collector.models import ExtractedDocument

ALLOWED_GENERATION_KINDS = {"notice", "exam"}
MIN_CHARS_BY_KIND = {
    "notice": 1200,
    "exam": 1800,
}

BLOCKED_LOCATION_TERMS = (
    "convocacao",
    "posse",
    "portal-da-transparencia",
    "transparencia",
    "agente-comercial",
    "trabalhe-conosco",
    "noticia",
    "imprensa",
    "relacao-de-convocados",
)

QUALITY_SIGNALS = (
    "edital",
    "conteudo programatico",
    "programa de provas",
    "disciplinas",
    "conhecimentos exigidos",
    "conhecimentos bancarios",
    "sistema financeiro nacional",
    "prova objetiva",
    "caderno de prova",
    "caderno de provas",
    "regulamento",
    "normativo",
    "resolucao",
)


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value.lower()).strip()


def assess_generation_document(document: ExtractedDocument) -> tuple[bool, str]:
    """Valida se uma fonte possui qualidade mínima para fundamentar questões inéditas."""
    if document.kind not in ALLOWED_GENERATION_KINDS:
        return False, f"tipo {document.kind!r} não permitido para geração"

    location = _normalized(f"{document.title} {document.url}")
    blocked = next((term for term in BLOCKED_LOCATION_TERMS if term in location), None)
    if blocked:
        return False, f"página administrativa ou irrelevante ({blocked})"

    minimum = MIN_CHARS_BY_KIND[document.kind]
    text = document.text.strip()
    if len(text) < minimum:
        return False, f"texto insuficiente ({len(text)} < {minimum} caracteres)"

    if float(document.confidence or 0) < 0.65:
        return False, f"baixa confiança de extração ({document.confidence:.2f})"

    normalized_text = _normalized(text[:12000])
    unique_words = set(re.findall(r"\b[a-z0-9]{3,}\b", normalized_text))
    if len(unique_words) < 120:
        return False, f"baixa diversidade textual ({len(unique_words)} termos únicos)"

    evidence = f"{location} {normalized_text}"
    signal_hits = [signal for signal in QUALITY_SIGNALS if signal in evidence]
    if not signal_hits:
        return False, "não contém sinais de edital, conteúdo programático, prova ou normativo"

    return True, f"fonte aprovada; sinais: {', '.join(signal_hits[:4])}"
