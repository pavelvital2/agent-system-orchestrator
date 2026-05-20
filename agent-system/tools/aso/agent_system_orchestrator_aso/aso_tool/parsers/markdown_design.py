"""Small Markdown helpers for ASO design validation."""

from __future__ import annotations

import re
from dataclasses import dataclass


HEADING_RE = re.compile(r"^(?P<level>#{2,6})\s+(?P<title>.+?)\s*$")
FIELD_RE = re.compile(r"^\s*-?\s*(?P<key>[A-Z][A-Z0-9_]*):\s*(?P<value>.*?)\s*$")
NONE_VALUES = {"", "NONE", "none", "null", "N/A", "n/a", "UNKNOWN", "unknown", "TBD", "tbd"}


@dataclass(frozen=True)
class MarkdownSection:
    """Parsed Markdown section body keyed by a normalized heading title."""

    title: str
    normalized_title: str
    line: int
    body: str


@dataclass(frozen=True)
class MarkdownDocument:
    """Parsed Markdown document with deterministic section lookup."""

    text: str
    sections: dict[str, MarkdownSection]
    duplicate_sections: list[str]


def normalize_heading(title: str) -> str:
    return re.sub(r"\s+", "_", title.strip().upper())


def is_none(value: str | None) -> bool:
    return value is None or value.strip() in NONE_VALUES


def parse_markdown(text: str) -> MarkdownDocument:
    """Parse level-2+ Markdown sections without interpreting inline markup."""

    headings: list[tuple[int, str, str, int]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            title = match.group("title").strip()
            headings.append((index, title, normalize_heading(title), len(match.group("level"))))

    sections: dict[str, MarkdownSection] = {}
    duplicates: list[str] = []
    for position, (line_index, title, normalized, _level) in enumerate(headings):
        next_line_index = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        body = "\n".join(lines[line_index + 1 : next_line_index]).strip()
        if normalized in sections:
            duplicates.append(normalized)
            continue
        sections[normalized] = MarkdownSection(
            title=title,
            normalized_title=normalized,
            line=line_index + 1,
            body=body,
        )
    return MarkdownDocument(text=text, sections=sections, duplicate_sections=sorted(set(duplicates)))


def field_values(section: MarkdownSection, key: str) -> list[str]:
    values: list[str] = []
    for line in section.body.splitlines():
        match = FIELD_RE.match(line)
        if match and match.group("key") == key:
            values.append(match.group("value").strip())
    return values


def all_field_values(section: MarkdownSection) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for line in section.body.splitlines():
        match = FIELD_RE.match(line)
        if match:
            values.append((match.group("key"), match.group("value").strip()))
    return values


def has_substantive_body(section: MarkdownSection) -> bool:
    body = section.body.strip()
    if not body:
        return False
    nonempty_lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith("```")
    ]
    if not nonempty_lines:
        return False
    if len(nonempty_lines) == 1 and is_none(nonempty_lines[0]):
        return False
    return True


def has_non_none_field(section: MarkdownSection, key: str) -> bool:
    return any(not is_none(value) for value in field_values(section, key))
