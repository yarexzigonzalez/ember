# Benchmarks

Real numbers from `benchmarks/run.py`, not vibes. Rerun it and this whole file gets
rewritten with whatever your machine says.

- ran: 2026-11-21 06:42 UTC
- machine: Darwin arm64, Python 3.14.6, Postgres 16.15 (Debian 16.15-1.pgdg13+2) (docker, local)
- each cell is **median / p95 in ms**. fast paths ran 21× per cell, naive ran 7× (it's slow, you get the idea). one warm-up run first, not counted.
- times are the service call itself (db round trips + python), no HTTP on top.
- data comes from `app/services/fake_data.py` with a fixed seed: ~82% of rows applied,
  replies vary by source, about 2.3 status events per application.

## What's being compared

- **naive**: load everything for the user into python and loop (`services/*/naive.py`).
- **sql, no indexes**: the optimized query, but with the M10 composite indexes dropped.
  only the correctness indexes from M1 are around (pk, unique, plain `user_id`).
- **sql + indexes**: what the app actually runs.

Import doesn't get a no-index column. It's bound by round trips, not lookups.
Import timings include parsing + validating the CSV (1,000 rows, 200 of them already in the account), same for both versions.

## 1,000 applications

| workload | naive | sql, no indexes | sql + indexes | naive ÷ fast |
|---|---:|---:|---:|---:|
| Market Pulse analytics | 25.6 / 45.7 | 1.9 / 2.9 | 1.7 / 2.0 | 15× |
| Filtered + search list | 9.9 / 10.6 | 2.2 / 3.7 | 1.9 / 2.4 | 5× |
| Bulk import (1,000 rows) | 2,267.7 / 2,532.9 | — | 231.5 / 292.2 | 10× |

## 10,000 applications

| workload | naive | sql, no indexes | sql + indexes | naive ÷ fast |
|---|---:|---:|---:|---:|
| Market Pulse analytics | 354.1 / 458.7 | 13.8 / 15.1 | 15.1 / 15.9 | 23× |
| Filtered + search list | 142.2 / 184.1 | 10.8 / 11.7 | 10.6 / 11.9 | 13× |
| Bulk import (1,000 rows) | 2,642.9 / 3,745.2 | — | 226.7 / 277.1 | 12× |

## 50,000 applications

| workload | naive | sql, no indexes | sql + indexes | naive ÷ fast |
|---|---:|---:|---:|---:|
| Market Pulse analytics | 2,777.3 / 2,980.2 | 73.0 / 75.0 | 62.0 / 72.1 | 45× |
| Filtered + search list | 1,076.5 / 1,237.2 | 47.4 / 49.4 | 44.6 / 62.8 | 24× |
| Bulk import (1,000 rows) | 2,225.6 / 2,921.1 | — | 276.7 / 315.2 | 8× |

## Reading it

- **analytics**: naive drags every application *and* every status event into python
  objects, so it scales with how much you've ever done. the sql version ships back
  ~20 rows. biggest win on the page.
- **list**: naive sorts and filters the whole account in python to hand back 50 rows.
  sql only touches what it needs and returns one page.
- **import**: naive is a lookup + insert + commit per row, so it's basically
  `rows × round trip`. the bulk version is one select plus a couple of big inserts.
- **indexes, honestly**: on these two workloads they barely move it. analytics reads
  basically every row the user has, so there's nothing to skip, and the plain `user_id`
  index from M1 already narrows things down. the search list has a `%term%` ILIKE,
  which a btree can't help with. almost all of the win is moving work into sql.
- where the composite indexes *do* earn their keep is anything ordered + limited,
  like Ghost Radar below: a straight index scan that stops after 200 rows, ~0.3ms.
- next step if search ever gets slow: the 50k list plan spills its window count to
  disk (`temp read/written`). options are `pg_trgm` GIN indexes for the ILIKE, or
  dropping the exact total. not worth it at 45ms.
- one gotcha found while building this: right after bulk-loading 10k rows, before
  autovacuum ran `ANALYZE`, the optimized pulse query took ~2.4s because the planner
  had garbage row estimates. with fresh stats it's ~15ms. the script runs `ANALYZE`
  after seeding for that reason.

## EXPLAIN ANALYZE (50,000 rows, with indexes)

Search list: applied + 'intern', sorted by company, first page.

```
Limit  (cost=4350.59..4350.71 rows=50 width=318) (actual time=41.134..41.141 rows=50 loops=1)
  Buffers: shared hit=2376, temp read=413 written=341
  ->  Sort  (cost=4350.59..4376.57 rows=10394 width=318) (actual time=41.132..41.136 rows=50 loops=1)
        Sort Key: (lower(company)), id
        Sort Method: top-N heapsort  Memory: 68kB
        Buffers: shared hit=2376, temp read=413 written=341
        ->  WindowAgg  (cost=517.20..4005.31 rows=10394 width=318) (actual time=33.475..37.643 rows=10320 loops=1)
              Buffers: shared hit=2376, temp read=413 written=341
              ->  Bitmap Heap Scan on applications  (cost=517.20..3849.40 rows=10394 width=278) (actual time=1.131..30.570 rows=10320 loops=1)
                    Recheck Cond: ((user_id = 'f0dab065-b382-4c34-bc13-59c04bd2e8f9'::uuid) AND (status = 'applied'::text))
                    Filter: ((company ~~* '%intern%'::text) OR (role ~~* '%intern%'::text) OR (location ~~* '%intern%'::text))
                    Rows Removed by Filter: 14570
                    Heap Blocks: exact=2324
                    Buffers: shared hit=2376
                    ->  Bitmap Index Scan on ix_applications_user_status  (cost=0.00..514.60 rows=25431 width=0) (actual time=0.870..0.870 rows=44890 loops=1)
                          Index Cond: ((user_id = 'f0dab065-b382-4c34-bc13-59c04bd2e8f9'::uuid) AND (status = 'applied'::text))
                          Buffers: shared hit=52
Planning:
  Buffers: shared hit=80
Planning Time: 0.349 ms
Execution Time: 41.177 ms
```

Ghost Radar: open stuff that's been quiet 14+ days, oldest first.

```
Limit  (cost=0.42..59.25 rows=200 width=278) (actual time=0.039..0.293 rows=200 loops=1)
  Buffers: shared hit=204
  ->  Index Scan using ix_applications_user_last_status_at on applications  (cost=0.42..8985.63 rows=30548 width=278) (actual time=0.038..0.281 rows=200 loops=1)
        Index Cond: ((user_id = 'f0dab065-b382-4c34-bc13-59c04bd2e8f9'::uuid) AND (last_status_at <= (now() - '14 days'::interval)))
        Filter: (status = ANY ('{saved,applied,oa,interview}'::text[]))
        Buffers: shared hit=204
Planning Time: 0.148 ms
Execution Time: 0.312 ms
```

## Rerun it

```bash
make db && make migrate
make bench               # 1k, 10k, 50k. takes a few minutes, mostly naive import
make bench ARGS='--sizes 1000 --runs 10'   # quick pass
```
