"""Naive vs optimized, measured. Writes docs/BENCHMARKS.md.

    make bench            (or: .venv/bin/python benchmarks/run.py)

For each dataset size it makes a throwaway user, seeds fake data, runs
ANALYZE (fresh stats matter a lot, see the doc), then times each workload
a bunch of times and keeps the median and p95. Three variants:

- naive:            the python-loop version
- sql, no indexes:  optimized code with the M10 composite indexes dropped
                    (inside a transaction that gets rolled back)
- sql + indexes:    what the app actually runs

Times are the service function call (db round trips + python), not HTTP.
The throwaway users get deleted at the end.
"""

import argparse
import platform
import statistics
import time
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

import _setup  # noqa: F401

from app.db import SessionLocal
from app.models.application import Application
from app.models.user import User
from app.schemas.application import ApplicationListParams
from app.services.analytics.naive import market_pulse_naive
from app.services.analytics.optimized import market_pulse_optimized
from app.services.fake_data import insert_fake
from app.services.importing.naive import import_naive
from app.services.importing.optimized import import_optimized
from app.services.importing.parse import parse_csv
from app.services.listing.naive import list_applications_naive
from app.services.listing.optimized import list_applications_optimized

PERF_INDEXES = [
    "ix_applications_user_status",
    "ix_applications_user_applied_at",
    "ix_applications_user_source",
    "ix_applications_user_last_status_at",
    "ix_applications_user_updated_at",
    "ix_status_events_user_occurred_at",
]
IMPORT_ROWS = 1_000
IMPORT_DUPES = 200
LIST_PARAMS = ApplicationListParams(
    q="intern", status="applied", sort="company", direction="asc", page=1, page_size=50
)
OUT = Path(__file__).resolve().parent.parent / "docs" / "BENCHMARKS.md"


def timed(fn: Callable[[], object], runs: int, before: Callable[[], None] | None = None):
    fn()  # warm-up, not counted
    if before:
        before()
    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
        if before:
            before()
    samples.sort()
    p95 = statistics.quantiles(samples, n=20, method="inclusive")[18]
    return statistics.median(samples), p95


def import_csv_for(db: Session, user: User) -> str:
    # 800 brand-new rows + 200 that the user already has, so the skip path gets exercised
    existing = db.execute(
        select(Application.company, Application.role, Application.posting_url)
        .where(Application.user_id == user.id)
        .limit(IMPORT_DUPES)
    ).all()
    lines = ["company,role,link,date"]
    lines += [f"{c},{r},{u},2026-10-01" for c, r, u in existing]
    lines += [
        f"Bench Co {i % 90},Engineer {i % 13},https://import.bench/{i},2026-10-{(i % 28) + 1:02d}"
        for i in range(IMPORT_ROWS - len(existing))
    ]
    return "\n".join(lines) + "\n"


def undo_import(db: Session, user: User) -> Callable[[], None]:
    def run() -> None:
        db.execute(
            delete(Application).where(
                Application.user_id == user.id, Application.posting_url.like("https://import.bench/%")
            )
        )
        db.commit()

    return run


def bench_size(size: int, runs: int) -> dict:
    db = SessionLocal()
    user = User(email=f"bench-{uuid.uuid4().hex}@ember.dev", password_hash="x", timezone="UTC")
    db.add(user)
    db.commit()
    try:
        insert_fake(db, user.id, size, seed=size, today=date(2026, 11, 20))
        db.execute(text("ANALYZE applications"))
        db.execute(text("ANALYZE status_events"))
        db.commit()
        csv_text = import_csv_for(db, user)
        reset = undo_import(db, user)
        slow_runs = max(5, runs // 3)  # naive at 50k is slow, don't need 30 of them

        results: dict[str, dict[str, tuple[float, float]]] = {}
        results["Market Pulse analytics"] = {
            "naive": timed(lambda: market_pulse_naive(db, user.id, "UTC"), slow_runs),
            "fast": timed(lambda: market_pulse_optimized(db, user.id, "UTC"), runs),
        }
        results["Filtered + search list"] = {
            "naive": timed(lambda: list_applications_naive(db, user.id, LIST_PARAMS), slow_runs),
            "fast": timed(lambda: list_applications_optimized(db, user.id, LIST_PARAMS), runs),
        }
        results[f"Bulk import ({IMPORT_ROWS:,} rows)"] = {
            "naive": timed(lambda: import_naive(db, user, parse_csv(csv_text)), slow_runs, reset),
            "fast": timed(lambda: import_optimized(db, user, parse_csv(csv_text)), runs, reset),
        }

        # same optimized code, minus the composite indexes. DDL is transactional in
        # postgres, so drop them, measure, roll back, and they're right back.
        db.commit()
        for name in PERF_INDEXES:
            db.execute(text(f"DROP INDEX {name}"))
        results["Market Pulse analytics"]["noidx"] = timed(
            lambda: market_pulse_optimized(db, user.id, "UTC"), runs
        )
        results["Filtered + search list"]["noidx"] = timed(
            lambda: list_applications_optimized(db, user.id, LIST_PARAMS), runs
        )
        db.rollback()

        explain = {
            "list": explain_list(db, user.id),
            "ghost": explain_ghost(db, user.id),
        }
        return {"results": results, "explain": explain}
    finally:
        db.rollback()
        db.execute(delete(User).where(User.id == user.id))
        db.commit()
        db.close()


def _explain(db: Session, sql: str, params: dict) -> str:
    rows = db.execute(text("EXPLAIN (ANALYZE, BUFFERS) " + sql), params).all()
    return "\n".join(row[0] for row in rows)


def explain_list(db: Session, user_id: uuid.UUID) -> str:
    return _explain(
        db,
        """SELECT *, count(*) OVER () AS total FROM applications
WHERE user_id = :u AND status = 'applied'
  AND (company ILIKE '%intern%' OR role ILIKE '%intern%' OR location ILIKE '%intern%')
ORDER BY lower(company), id LIMIT 50""",
        {"u": user_id},
    )


def explain_ghost(db: Session, user_id: uuid.UUID) -> str:
    return _explain(
        db,
        """SELECT * FROM applications
WHERE user_id = :u AND status IN ('saved', 'applied', 'oa', 'interview')
  AND last_status_at <= now() - interval '14 days'
ORDER BY last_status_at LIMIT 200""",
        {"u": user_id},
    )


def fmt(pair: tuple[float, float] | None) -> str:
    if pair is None:
        return "—"
    median, p95 = pair
    return f"{median:,.1f} / {p95:,.1f}"


def speedup(row: dict) -> str:
    return f"{row['naive'][0] / row['fast'][0]:,.0f}×"


def write_doc(all_results: dict[int, dict], runs: int) -> None:
    db = SessionLocal()
    pg = db.scalar(text("SHOW server_version"))
    db.close()
    biggest = max(all_results)
    lines = [
        "# Benchmarks",
        "",
        "Real numbers from `benchmarks/run.py`, not vibes. Rerun it and this whole file gets",
        "rewritten with whatever your machine says.",
        "",
        f"- ran: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC",
        f"- machine: {platform.system()} {platform.machine()}, Python {platform.python_version()}, "
        f"Postgres {pg} (docker, local)",
        f"- each cell is **median / p95 in ms**. fast paths ran {runs}× per cell, naive ran "
        f"{max(5, runs // 3)}× (it's slow, you get the idea). one warm-up run first, not counted.",
        "- times are the service call itself (db round trips + python), no HTTP on top.",
        "- data comes from `app/services/fake_data.py` with a fixed seed: ~82% of rows applied,",
        "  replies vary by source, about 2.3 status events per application.",
        "",
        "## What's being compared",
        "",
        "- **naive**: load everything for the user into python and loop (`services/*/naive.py`).",
        "- **sql, no indexes**: the optimized query, but with the M10 composite indexes dropped.",
        "  only the correctness indexes from M1 are around (pk, unique, plain `user_id`).",
        "- **sql + indexes**: what the app actually runs.",
        "",
        "Import doesn't get a no-index column. It's bound by round trips, not lookups.",
        f"Import timings include parsing + validating the CSV ({IMPORT_ROWS:,} rows, "
        f"{IMPORT_DUPES} of them already in the account), same for both versions.",
        "",
    ]
    for size, data in sorted(all_results.items()):
        lines += [
            f"## {size:,} applications",
            "",
            "| workload | naive | sql, no indexes | sql + indexes | naive ÷ fast |",
            "|---|---:|---:|---:|---:|",
        ]
        for name, row in data["results"].items():
            lines.append(
                f"| {name} | {fmt(row['naive'])} | {fmt(row.get('noidx'))} | "
                f"{fmt(row['fast'])} | {speedup(row)} |"
            )
        lines.append("")
    lines += [
        "## Reading it",
        "",
        "- **analytics**: naive drags every application *and* every status event into python",
        "  objects, so it scales with how much you've ever done. the sql version ships back",
        "  ~20 rows. biggest win on the page.",
        "- **list**: naive sorts and filters the whole account in python to hand back 50 rows.",
        "  sql only touches what it needs and returns one page.",
        "- **import**: naive is a lookup + insert + commit per row, so it's basically",
        "  `rows × round trip`. the bulk version is one select plus a couple of big inserts.",
        "- **indexes, honestly**: on these two workloads they barely move it. analytics reads",
        "  basically every row the user has, so there's nothing to skip, and the plain `user_id`",
        "  index from M1 already narrows things down. the search list has a `%term%` ILIKE,",
        "  which a btree can't help with. almost all of the win is moving work into sql.",
        "- where the composite indexes *do* earn their keep is anything ordered + limited,",
        "  like Ghost Radar below: a straight index scan that stops after 200 rows, ~0.3ms.",
        "- next step if search ever gets slow: the 50k list plan spills its window count to",
        "  disk (`temp read/written`). options are `pg_trgm` GIN indexes for the ILIKE, or",
        "  dropping the exact total. not worth it at 45ms.",
        "- one gotcha found while building this: right after bulk-loading 10k rows, before",
        "  autovacuum ran `ANALYZE`, the optimized pulse query took ~2.4s because the planner",
        "  had garbage row estimates. with fresh stats it's ~15ms. the script runs `ANALYZE`",
        "  after seeding for that reason.",
        "",
        f"## EXPLAIN ANALYZE ({biggest:,} rows, with indexes)",
        "",
        "Search list: applied + 'intern', sorted by company, first page.",
        "",
        "```",
        all_results[biggest]["explain"]["list"],
        "```",
        "",
        "Ghost Radar: open stuff that's been quiet 14+ days, oldest first.",
        "",
        "```",
        all_results[biggest]["explain"]["ghost"],
        "```",
        "",
        "## Rerun it",
        "",
        "```bash",
        "make db && make migrate",
        "make bench               # 1k, 10k, 50k. takes a few minutes, mostly naive import",
        "make bench ARGS='--sizes 1000 --runs 10'   # quick pass",
        "```",
        "",
    ]
    OUT.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", type=int, nargs="+", default=[1_000, 10_000, 50_000])
    parser.add_argument("--runs", type=int, default=21)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    all_results = {}
    for size in args.sizes:
        start = time.perf_counter()
        all_results[size] = bench_size(size, args.runs)
        print(f"{size:>7,} rows done in {time.perf_counter() - start:,.0f}s")
        for name, row in all_results[size]["results"].items():
            print(f"   {name:<28} naive {fmt(row['naive']):>20}   fast {fmt(row['fast']):>16}")
    if not args.no_write:
        write_doc(all_results, args.runs)
        print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
