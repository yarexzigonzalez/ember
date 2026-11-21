"""Same company + role + link should not land twice for one person.

Normalization is boring on purpose: lowercase, collapse whitespace, so
"Stripe" and " stripe " share a key. The separator is a character that
won't show up in normal titles.
"""

_SEP = "\x1f"


def normalize_part(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def make_dedupe_key(company: str, role: str, posting_url: str | None) -> str:
    return _SEP.join(
        [
            normalize_part(company),
            normalize_part(role),
            normalize_part(posting_url),
        ]
    )
