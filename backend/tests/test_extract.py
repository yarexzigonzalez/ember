from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.api.extract import get_llm
from app.db import SessionLocal
from app.main import app
from app.models.extraction_cache import ExtractionCache
from app.services.extract.anthropic_provider import AnthropicExtractor
from app.services.extract.heuristic import HeuristicExtractor
from app.services.extract.protocol import ExtractedJob, ExtractionFailed
from app.services.extract.service import input_hash

POSTING = """Software Engineer Intern - Summer 2027
Stripe is hiring!
Location: San Francisco, CA
Apply: https://stripe.com/jobs/listing/swe-intern/123

About Stripe
We build economic infrastructure for the internet.

Requirements
- Currently pursuing a BS in Computer Science
- Experience with Python or Go
- Comfortable with SQL

Benefits
- Free lunch
"""


def test_heuristic_pulls_the_obvious_stuff() -> None:
    job = HeuristicExtractor().extract(POSTING)
    assert job.company == "Stripe"
    assert job.role == "Software Engineer Intern"
    assert job.location == "San Francisco, CA"
    assert job.posting_url == "https://stripe.com/jobs/listing/swe-intern/123"
    assert job.seniority == "intern"
    assert job.role_type == "intern"
    assert job.requirements == [
        "Currently pursuing a BS in Computer Science",
        "Experience with Python or Go",
        "Comfortable with SQL",
    ]


def test_heuristic_never_throws_on_junk() -> None:
    job = HeuristicExtractor().extract("lorem ipsum " * 50)
    assert job.company is None
    assert job.seniority == "unknown"


def _fake_client(text: str, stop_reason: str = "end_turn"):
    response = SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)]
    )
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **_: response))


def test_anthropic_provider_rejects_garbage_json() -> None:
    with pytest.raises(ExtractionFailed):
        AnthropicExtractor(_fake_client("{not json"), "m").extract(POSTING)  # type: ignore[arg-type]
    with pytest.raises(ExtractionFailed):
        AnthropicExtractor(_fake_client('{"seniority": "wizard"}'), "m").extract(POSTING)  # type: ignore[arg-type]
    with pytest.raises(ExtractionFailed):
        AnthropicExtractor(_fake_client("{}", "refusal"), "m").extract(POSTING)  # type: ignore[arg-type]


class CountingLlm:
    name = "fake-model"

    def __init__(self, result: ExtractedJob | None) -> None:
        self.calls = 0
        self.result = result

    def extract(self, text: str) -> ExtractedJob:
        self.calls += 1
        if self.result is None:
            raise ExtractionFailed("nope")
        return self.result


@pytest.fixture
def logged_in(client: TestClient, registered_user) -> TestClient:
    client.post("/api/auth/login", json=registered_user)
    return client


@pytest.fixture
def clean_cache():
    yield
    db = SessionLocal()
    db.execute(delete(ExtractionCache).where(ExtractionCache.model == "fake-model"))
    db.commit()
    db.close()


def _use(llm) -> None:
    app.dependency_overrides[get_llm] = lambda: llm


def test_no_key_means_heuristic(logged_in: TestClient) -> None:
    _use(None)
    try:
        response = logged_in.post("/api/extract", json={"text": POSTING})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["via"] == "heuristic"
    assert response.json()["job"]["company"] == "Stripe"


def test_llm_failure_falls_back(logged_in: TestClient) -> None:
    _use(CountingLlm(None))
    try:
        response = logged_in.post("/api/extract", json={"text": POSTING + "fallback"})
    finally:
        app.dependency_overrides.clear()
    assert response.json()["via"] == "heuristic"


def test_same_paste_twice_hits_cache(logged_in: TestClient, clean_cache) -> None:
    llm = CountingLlm(ExtractedJob(company="Stripe", role="SWE Intern", seniority="intern"))
    _use(llm)
    text = POSTING + "cache test"
    try:
        first = logged_in.post("/api/extract", json={"text": text}).json()
        second = logged_in.post("/api/extract", json={"text": text}).json()
    finally:
        app.dependency_overrides.clear()
    assert (first["via"], second["via"]) == ("llm", "cache")
    assert llm.calls == 1  # second one never got billed
    assert second["job"]["role"] == "SWE Intern"
    db = SessionLocal()
    assert db.get(ExtractionCache, input_hash(text)) is not None
    db.close()


def test_paste_size_limits(logged_in: TestClient) -> None:
    assert logged_in.post("/api/extract", json={"text": "short"}).status_code == 422
    assert logged_in.post("/api/extract", json={"text": "x" * 20_001}).status_code == 422
