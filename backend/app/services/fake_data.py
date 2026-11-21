"""Realistic-looking fake job search, used by the benchmarks, the demo seed,
and the naive-vs-optimized test.

Deterministic for a given seed so benchmark runs are comparable. Rows go in
with bulk INSERTs because the benchmark needs 50k of them without waiting all day.
"""

import random
import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.status_event import StatusEvent
from app.services.dedupe import make_dedupe_key

COMPANIES = [
    "Stripe",
    "Notion",
    "Figma",
    "Datadog",
    "Cloudflare",
    "Airbnb",
    "Ramp",
    "Linear",
    "Vercel",
    "Plaid",
    "Robinhood",
    "Discord",
    "Duolingo",
    "Pinterest",
    "Snowflake",
    "Databricks",
    "Atlassian",
    "Shopify",
    "Twilio",
    "HubSpot",
    "Asana",
    "Brex",
    "Retool",
    "Scale AI",
    "Instacart",
    "DoorDash",
    "Lyft",
    "Coinbase",
    "Square",
    "Zillow",
    "Etsy",
    "Reddit",
    "Dropbox",
    "Okta",
    "MongoDB",
    "Confluent",
    "GitLab",
    "Grammarly",
    "Canva",
    "Palantir",
    "Capital One",
    "JPMorgan",
    "Goldman Sachs",
    "Microsoft",
    "Amazon",
    "Google",
    "Meta",
    "Apple",
    "Netflix",
    "Uber",
    "Salesforce",
    "Adobe",
    "Intuit",
]
ROLES = [
    ("Software Engineer Intern", "intern", "intern"),
    ("Backend Engineer Intern", "intern", "intern"),
    ("Frontend Engineer Intern", "intern", "intern"),
    ("Data Science Intern", "intern", "intern"),
    ("Product Engineer Intern", "intern", "intern"),
    ("Software Engineer, New Grad", "full_time", "new_grad"),
    ("Backend Engineer, New Grad", "full_time", "new_grad"),
    ("Full Stack Engineer I", "full_time", "junior"),
    ("Software Engineer I", "full_time", "junior"),
    ("Data Engineer", "full_time", "mid"),
    ("Platform Engineer (Contract)", "contract", "mid"),
    ("QA Automation Engineer (Contract)", "contract", "junior"),
]
LOCATIONS = [
    "Remote",
    "San Francisco, CA",
    "New York, NY",
    "Seattle, WA",
    "Austin, TX",
    "Chicago, IL",
    "Boston, MA",
    "Los Angeles, CA",
    "Denver, CO",
    None,
]
# Referrals reply way more often than cold applies, which makes the charts tell a story.
SOURCES = {
    "LinkedIn": (0.34, 0.16),
    "Company site": (0.26, 0.22),
    "Handshake": (0.18, 0.20),
    "Referral": (0.12, 0.55),
    "Other": (0.10, 0.12),
}


def _weighted(rng: random.Random, options: dict[str, tuple[float, float]]) -> str:
    return rng.choices(list(options), weights=[w for w, _ in options.values()])[0]


def generate(
    user_id: uuid.UUID, count: int, *, seed: int = 7, today: date, days_back: int = 120
) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    apps: list[dict] = []
    events: list[dict] = []

    def at(day: date) -> datetime:
        return datetime.combine(day, time(rng.randint(14, 23), rng.randint(0, 59)), UTC)

    for i in range(count):
        company = rng.choice(COMPANIES)
        role, role_type, seniority = rng.choice(ROLES)
        source = _weighted(rng, SOURCES)
        url = f"https://jobs.example.com/{company.lower().replace(' ', '-')}/{i}"
        app_id = uuid.uuid4()
        found = today - timedelta(days=rng.randint(0, days_back))
        chain: list[tuple[str, datetime]] = [("saved", at(found))]
        applied_at: date | None = None

        if rng.random() < 0.82:  # most saved jobs actually get applied to
            # weekdays get more applications than weekends
            applied_day = found + timedelta(days=rng.randint(0, 3))
            if applied_day.weekday() >= 5 and rng.random() < 0.6:
                applied_day -= timedelta(days=applied_day.weekday() - 4)
            applied_day = min(applied_day, today)
            applied_at = applied_day
            chain.append(("applied", at(applied_day)))
            reply_odds = SOURCES[source][1]
            reply_day = applied_day + timedelta(days=rng.randint(2, 28))
            if reply_day <= today and rng.random() < reply_odds:
                first = rng.choices(["oa", "interview", "rejected"], weights=[4, 2, 4])[0]
                chain.append((first, at(reply_day)))
                if first != "rejected":
                    next_day = reply_day + timedelta(days=rng.randint(3, 14))
                    if next_day <= today:
                        nxt = rng.choices(["interview", "rejected", "offer"], weights=[5, 4, 1])[0]
                        if nxt != first:
                            chain.append((nxt, at(next_day)))
            elif (today - applied_day).days > 30 and rng.random() < 0.35:
                chain.append(("ghosted", at(applied_day + timedelta(days=30))))

        previous = None
        for status, when in chain:
            events.append(
                {
                    "id": uuid.uuid4(),
                    "application_id": app_id,
                    "user_id": user_id,
                    "from_status": previous,
                    "to_status": status,
                    "occurred_at": when,
                }
            )
            previous = status
        apps.append(
            {
                "id": app_id,
                "user_id": user_id,
                "company": company,
                "role": role,
                "location": rng.choice(LOCATIONS),
                "source": source,
                "posting_url": url,
                "dedupe_key": make_dedupe_key(company, role, url),
                "status": chain[-1][0],
                "seniority": seniority,
                "role_type": role_type,
                "requirements": [],
                "notes": None,
                "applied_at": applied_at,
                "last_status_at": chain[-1][1],
                "created_at": chain[0][1],
                "updated_at": chain[-1][1],
            }
        )
    return apps, events


def insert_fake(
    db: Session,
    user_id: uuid.UUID,
    count: int,
    *,
    seed: int = 7,
    today: date,
    days_back: int = 120,
) -> int:
    apps, events = generate(user_id, count, seed=seed, today=today, days_back=days_back)
    for start in range(0, len(apps), 2_000):
        db.execute(insert(Application), apps[start : start + 2_000])
    for start in range(0, len(events), 5_000):
        db.execute(insert(StatusEvent), events[start : start + 5_000])
    db.commit()
    return len(apps)
