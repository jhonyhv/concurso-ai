from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    name: str
    organization: str
    bank: str
    contest: str
    page_url: str
    allowed_domains: tuple[str, ...]
    mode: str = "generate_original"
    license_name: str = "source_only"
    enabled: bool = True
    max_documents: int = 10
    default_subject: str = "Conhecimentos Gerais"
    style_notes: str = "Questão objetiva de concurso público brasileiro, com cinco alternativas."


@dataclass(frozen=True)
class DocumentLink:
    source_id: str
    title: str
    url: str
    kind: str


@dataclass
class ExtractedDocument:
    source_id: str
    title: str
    url: str
    kind: str
    text: str
    content_hash: str
    content_type: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateQuestion:
    source_uid: str
    organization: str
    contest: str
    bank: str
    cargo: str
    year: int | None
    subject: str
    topic: str
    subtopic: str
    difficulty: str
    statement: str
    options: dict[str, str]
    answer: str
    explanation: str
    tags: list[str]
    source_url: str
    source_kind: str
    license_name: str
    status: str = "published"
    confidence: float = 0.9
    official_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
