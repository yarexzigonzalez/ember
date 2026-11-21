import csv
import io

from fastapi.testclient import TestClient

from app.services.importing.parse import parse_csv

GOOD = """Company,ROLE,Link,Date,Salary,Recruiter
Stripe,Backend Intern,https://stripe.com/1,2026-10-01,$$$,Bob
Notion,New Grad,,2026-10-03,,
Figma,Product Intern,https://figma.com/2,,,
"""


def test_parse_ignores_unknown_columns_and_matches_case() -> None:
    parsed = parse_csv(GOOD)
    assert parsed.errors == []
    assert [row.company for _, row in parsed.rows] == ["Stripe", "Notion", "Figma"]
    stripe = parsed.rows[0][1]
    assert stripe.applied_at.isoformat() == "2026-10-01"
    assert stripe.status == "applied"
    assert parsed.rows[2][1].status == "saved"  # no date = not applied yet


def test_bad_rows_get_reported_not_fatal() -> None:
    parsed = parse_csv(
        "company,role,date\nStripe,,2026-10-01\nNotion,PM,10/03/2026\nFigma,Eng,2026-10-05\n"
    )
    assert [(e.row, e.message.split()[0]) for e in parsed.errors] == [(2, "missing"), (3, "bad")]
    assert len(parsed.rows) == 1


def test_import_adds_skips_and_reports(client: TestClient, registered_user) -> None:
    client.post("/api/auth/login", json=registered_user)
    first = client.post("/api/import", json={"csv": GOOD}).json()
    assert first == {"added": 3, "skipped": 0, "errors": []}

    again = GOOD + "Stripe,Backend Intern,https://stripe.com/1,2026-10-01,,\nBroken,,,,\n"
    second = client.post("/api/import", json={"csv": again}).json()
    assert second["added"] == 0
    assert second["skipped"] == 4
    assert second["errors"] == [{"row": 6, "message": "missing role"}]


def test_missing_required_header_is_a_400(client: TestClient, registered_user) -> None:
    client.post("/api/auth/login", json=registered_user)
    response = client.post("/api/import", json={"csv": "name,title\nx,y\n"})
    assert response.status_code == 400


def test_export_round_trips_and_defuses_formulas(client: TestClient, registered_user) -> None:
    client.post("/api/auth/login", json=registered_user)
    client.post("/api/import", json={"csv": GOOD})
    client.post(
        "/api/applications", json={"company": "=HYPERLINK(\"x\")", "role": "Eng", "notes": "+1"}
    )
    response = client.get("/api/export.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows[0]["date"] == "2026-10-01" and rows[0]["link"] == "https://stripe.com/1"
    sneaky = rows[-1]
    assert sneaky["company"].startswith("'=") and sneaky["notes"] == "'+1"
    # and the export imports back cleanly into the same shape
    assert parse_csv(response.text).errors == []
