from __future__ import annotations

import hashlib
import re
import unicodedata

from collector.models import CandidateQuestion, ExtractedDocument, SourceConfig

QUESTION_START = re.compile(r"(?im)^\s*(?:QUEST[ÃA]O\s*)?(\d{1,3})\s*[.\-–)]\s*(.+)$")
OPTION_LINE = re.compile(r"(?im)^\s*[\[(]?([A-E])[\])\].:\-–]\s*(.+)$")
ANSWER_PAIR = re.compile(r"(?im)(?<!\w)(\d{1,3})\s*[.\-–:)]*\s*([A-E])(?!\w)")


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value.lower()).strip()


def _source_uid(source: SourceConfig, statement: str, options: dict[str, str]) -> str:
    payload = source.source_id + "|" + _normalized(statement) + "|" + "|".join(
        _normalized(options[key]) for key in sorted(options)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_answer_key(text: str) -> dict[int, str]:
    answers: dict[int, str] = {}
    for number, letter in ANSWER_PAIR.findall(text):
        answers[int(number)] = letter.upper()
    return answers


def parse_official_questions(
    document: ExtractedDocument,
    source: SourceConfig,
) -> list[tuple[int, str, dict[str, str]]]:
    matches = list(QUESTION_START.finditer(document.text))
    results: list[tuple[int, str, dict[str, str]]] = []
    for index, match in enumerate(matches):
        number = int(match.group(1))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(document.text)
        block = document.text[match.start() : end]
        option_matches = list(OPTION_LINE.finditer(block))
        if len(option_matches) not in {4, 5}:
            continue
        first_option = option_matches[0].start()
        header = block[:first_option]
        header_match = QUESTION_START.search(header)
        statement = header_match.group(2).strip() if header_match else header.strip()
        options: dict[str, str] = {}
        for option_match in option_matches:
            options[option_match.group(1).upper()] = option_match.group(2).strip(" .\n")
        if len(statement) >= 10 and all(len(value) >= 2 for value in options.values()):
            results.append((number, statement, options))
    return results


def pair_official_questions(
    source: SourceConfig,
    exam_documents: list[ExtractedDocument],
    answer_documents: list[ExtractedDocument],
) -> list[CandidateQuestion]:
    # Evita combinar versões diferentes da prova por engano.
    if len(exam_documents) != 1 or len(answer_documents) != 1:
        return []
    answers = parse_answer_key(answer_documents[0].text)
    if not answers:
        return []
    candidates: list[CandidateQuestion] = []
    for number, statement, options in parse_official_questions(exam_documents[0], source):
        answer = answers.get(number)
        if answer not in options:
            continue
        candidates.append(
            CandidateQuestion(
                source_uid=_source_uid(source, statement, options),
                organization=source.organization,
                contest=source.contest,
                bank=source.bank,
                cargo="Não identificado",
                year=None,
                subject=source.default_subject,
                topic="A classificar",
                subtopic="",
                difficulty="Média",
                statement=statement,
                options=options,
                answer=answer,
                explanation="Gabarito confirmado pelo documento oficial; explicação ainda não gerada.",
                tags=[source.source_id, "oficial"],
                source_url=exam_documents[0].url,
                source_kind="official",
                license_name=source.license_name,
                status="published" if source.license_name.startswith("CC-") else "review",
                confidence=0.96,
                official_number=number,
            )
        )
    return candidates
