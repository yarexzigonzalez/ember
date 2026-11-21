"""CSV -> clean rows + per-row errors. Shared by naive and optimized import.

Headers match case-insensitively and a few aliases are fine (url/link,
date/applied_at). Anything we don't know about gets ignored instead of
blowing up, since people export from all kinds of spreadsheets.
"""

import csv
import io
from dataclasses import dataclass
from datetime import date

from pydantic import ValidationError

from app.models.enums import STATUS_VALUES
from app.schemas.application import ApplicationCreate

MAX_ROWS = 5_000
MAX_BYTES = 2 * 1024 * 1024

_ALIASES = {
    "company": "company",
    "employer": "company",
    "role": "role",
    "title": "role",
    "position": "role",
    "link": "posting_url",
    "url": "posting_url",
    "posting_url": "posting_url",
    "date": "applied_at",
    "applied_at": "applied_at",
    "applied": "applied_at",
    "source": "source",
    "location": "location",
    "status": "status",
    "notes": "notes",
}


@dataclass
class RowError:
    row: int  # 1-based, counting the header as row 1 like a spreadsheet does
    message: str


@dataclass
class Parsed:
    rows: list[tuple[int, ApplicationCreate]]
    errors: list[RowError]


class CsvTooBig(ValueError):
    pass


def parse_csv(text: str, max_rows: int = MAX_ROWS) -> Parsed:
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise CsvTooBig("CSV is over 2 MB")
    reader = csv.reader(io.StringIO(text.lstrip("﻿")))
    header = next(reader, None)
    if not header:
        raise CsvTooBig("CSV is empty")
    columns = {i: _ALIASES.get(name.strip().lower()) for i, name in enumerate(header)}
    known = set(columns.values()) - {None}
    if not {"company", "role"} <= known:
        raise ValueError("Need at least a company and a role column")

    rows: list[tuple[int, ApplicationCreate]] = []
    errors: list[RowError] = []
    for number, raw in enumerate(reader, start=2):
        if not any(cell.strip() for cell in raw):
            continue
        if len(rows) + len(errors) >= max_rows:
            raise CsvTooBig(f"Too many rows, max is {max_rows:,}")
        fields = {
            columns[i]: cell.strip()
            for i, cell in enumerate(raw)
            if i in columns and columns[i] and cell.strip()
        }
        try:
            rows.append((number, _to_create(fields)))
        except ValueError as error:
            errors.append(RowError(number, str(error)))
    return Parsed(rows, errors)


def _to_create(fields: dict[str, str]) -> ApplicationCreate:
    for required in ("company", "role"):
        if not fields.get(required):
            raise ValueError(f"missing {required}")
    applied_at = None
    if fields.get("applied_at"):
        try:
            applied_at = date.fromisoformat(fields["applied_at"])
        except ValueError:
            raise ValueError(f"bad date {fields['applied_at']!r}, use YYYY-MM-DD") from None
    status = fields.get("status", "").lower() or ("applied" if applied_at else "saved")
    if status not in STATUS_VALUES:
        raise ValueError(f"unknown status {fields['status']!r}")
    try:
        return ApplicationCreate(
            company=fields["company"],
            role=fields["role"],
            posting_url=fields.get("posting_url"),
            source=fields.get("source"),
            location=fields.get("location"),
            notes=fields.get("notes"),
            status=status,  # type: ignore[arg-type]
            applied_at=applied_at,
        )
    except ValidationError as error:
        first = error.errors()[0]
        raise ValueError(f"{first['loc'][0]}: {first['msg']}") from None
