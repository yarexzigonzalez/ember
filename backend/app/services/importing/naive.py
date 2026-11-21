"""Naive import: for each row, ask the DB "do I have this already?", insert,
commit, repeat. That's 3+ round trips per row. It's the 'before' in the
benchmark, so it stays exactly this dumb.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.applications import DuplicateApplicationError, create_application
from app.services.importing.parse import Parsed, RowError


@dataclass
class ImportResult:
    added: int = 0
    skipped: int = 0
    errors: list[RowError] = field(default_factory=list)


def import_naive(db: Session, user: User, parsed: Parsed) -> ImportResult:
    result = ImportResult(errors=list(parsed.errors))
    for _number, row in parsed.rows:
        try:
            create_application(db, user, row)
        except DuplicateApplicationError:
            result.skipped += 1
        else:
            result.added += 1
    return result
