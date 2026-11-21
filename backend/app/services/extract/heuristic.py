"""Regex + keyword extractor. Free, instant, and kinda dumb, which is fine.

It's the fallback when there's no API key or the model returns junk, so it
has to always return *something* and never throw.
"""

import re

from app.services.extract.protocol import ExtractedJob

_URL = re.compile(r"https?://[^\s<>\"')]+")
_LABEL = r"^\s*(?:{})\s*[:\-–]\s*(.+)$"
_ROLE_WORDS = (
    r"engineer|developer|intern|analyst|designer|scientist|manager|architect|"
    r"researcher|specialist|consultant|sre|devops|programmer|associate|swe"
)
_ROLE_LINE = re.compile(rf"\b({_ROLE_WORDS})\b", re.IGNORECASE)
_CITY_STATE = re.compile(r"\b([A-Z][a-zA-Z .]+,\s*(?:[A-Z]{2}|[A-Z][a-z]+))\b")
_REQ_HEADER = re.compile(
    r"^\s*(requirements|qualifications|minimum qualifications|basic qualifications|"
    r"what you(?:'|’)ll need|what we(?:'|’)re looking for|you have|you might be a fit|"
    r"about you|skills)\b",
    re.IGNORECASE,
)
_ANY_HEADER = re.compile(r"^\s*[A-Z][A-Za-z ’'&/]{2,48}:?\s*$")
_BULLET = re.compile(r"^\s*(?:[-*•·▪◦]|\d+[.)])\s+(.*)$")


def _labeled(lines: list[str], labels: str) -> str | None:
    pattern = re.compile(_LABEL.format(labels), re.IGNORECASE)
    for line in lines:
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return None


def _find_company(text: str, lines: list[str]) -> str | None:
    labeled = _labeled(lines, "company|employer|organization")
    if labeled:
        return labeled
    patterns = [
        r"\bAbout\s+([A-Z][\w&.\- ]{1,40}?)\s*(?:\n|:|$)",
        r"\b([A-Z][\w&.\-]+(?: [A-Z][\w&.\-]+){0,3}) is hiring\b",
        r"\bjoin\s+([A-Z][\w&.\-]+(?: [A-Z][\w&.\-]+){0,2})\b",
        r"\b(?:at|@)\s+([A-Z][\w&.\-]+(?: [A-Z][\w&.\-]+){0,2})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip(" .")
            if candidate.lower() not in {"the", "us", "our", "the role", "you"}:
                return candidate
    return None


def _find_role(lines: list[str]) -> str | None:
    labeled = _labeled(lines, "title|job title|position|role")
    if labeled:
        return labeled
    for line in lines[:8]:
        stripped = line.strip()
        if 3 <= len(stripped) <= 90 and _ROLE_LINE.search(stripped):
            # "Backend Engineer at Stripe" / "Backend Engineer - Stripe" -> keep the title half
            return re.split(r"\s+(?:at|@|[-–|])\s+", stripped, maxsplit=1)[0].strip()
    return None


def _find_location(text: str, lines: list[str]) -> str | None:
    labeled = _labeled(lines, "location|locations|office|based in")
    if labeled:
        return labeled
    if re.search(r"\bremote\b", text, re.IGNORECASE):
        return "Remote"
    match = _CITY_STATE.search(text)
    return match.group(1).strip() if match else None


def _find_seniority(text: str) -> str:
    lowered = text.lower()
    checks = [
        ("intern", r"\bintern(ship)?\b|\bco-?op\b"),
        ("new_grad", r"new grad|university grad|early career|entry[- ]level|class of 20\d\d"),
        ("senior", r"\bsenior\b|\bsr\.?\b|\bstaff\b|\bprincipal\b|\blead\b"),
        ("junior", r"\bjunior\b|\bjr\.?\b|\bassociate\b"),
        ("mid", r"\bmid[- ]level\b|\b[3-5]\+? years\b"),
    ]
    for label, pattern in checks:
        if re.search(pattern, lowered):
            return label
    return "unknown"


def _find_role_type(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\bintern(ship)?\b|\bco-?op\b", lowered):
        return "intern"
    if re.search(r"\bcontract(or)?\b|\b1099\b|\bc2c\b|\btemporary\b", lowered):
        return "contract"
    if re.search(r"full[- ]time|\bfte\b|\bsalary\b|\bbenefits\b", lowered):
        return "full_time"
    return "unknown"


def _find_requirements(lines: list[str]) -> list[str]:
    found: list[str] = []
    inside = False
    for line in lines:
        if _REQ_HEADER.match(line):
            inside = True
            continue
        if not inside:
            continue
        bullet = _BULLET.match(line)
        if bullet:
            found.append(bullet.group(1).strip())
        elif _ANY_HEADER.match(line) and found:
            break  # next section started
        if len(found) >= 12:
            break
    return found


class HeuristicExtractor:
    name = "heuristic"

    def extract(self, text: str) -> ExtractedJob:
        lines = [line for line in text.splitlines() if line.strip()]
        url = _URL.search(text)
        return ExtractedJob(
            company=_find_company(text, lines),
            role=_find_role(lines),
            location=_find_location(text, lines),
            posting_url=url.group(0).rstrip(".,") if url else None,
            seniority=_find_seniority(text),  # type: ignore[arg-type]
            role_type=_find_role_type(text),  # type: ignore[arg-type]
            requirements=_find_requirements(lines),
        )
