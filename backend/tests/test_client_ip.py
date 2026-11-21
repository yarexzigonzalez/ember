from fastapi.testclient import TestClient

from app.config import settings
from app.middleware.rate_limit import limiter, resolve_client_ip


def test_no_proxies_uses_socket_peer() -> None:
    # Locally nothing sits in front, so a client-supplied header means nothing.
    assert resolve_client_ip("10.0.0.5", "6.6.6.6", trusted_hops=0) == "10.0.0.5"


def test_vercel_then_render_picks_second_from_right() -> None:
    # Vercel writes the real client, Render appends Vercel's egress IP.
    chain = "203.0.113.9, 76.76.21.21"
    assert resolve_client_ip("10.0.0.5", chain, trusted_hops=2) == "203.0.113.9"


def test_spoofed_prefix_is_ignored() -> None:
    # Client tried to sneak "1.1.1.1" in front. We only trust the last two hops.
    chain = "1.1.1.1, 203.0.113.9, 76.76.21.21"
    assert resolve_client_ip("10.0.0.5", chain, trusted_hops=2) == "203.0.113.9"


def test_short_chain_falls_back_to_leftmost() -> None:
    assert resolve_client_ip("10.0.0.5", "203.0.113.9", trusted_hops=2) == "203.0.113.9"


def test_missing_header_falls_back_to_peer() -> None:
    assert resolve_client_ip("10.0.0.5", None, trusted_hops=2) == "10.0.0.5"


def test_limiter_buckets_by_forwarded_ip(client: TestClient, unique_email: str) -> None:
    original = (settings.trusted_proxy_hops, settings.auth_rate_limit)
    settings.trusted_proxy_hops = 2
    settings.auth_rate_limit = 2
    limiter.reset()
    payload = {"email": unique_email, "password": "wrong-password"}
    try:
        alice = {"x-forwarded-for": "203.0.113.1, 76.76.21.21"}
        bob = {"x-forwarded-for": "203.0.113.2, 76.76.21.21"}
        alice_codes = [
            client.post("/api/auth/login", json=payload, headers=alice).status_code
            for _ in range(3)
        ]
        bob_code = client.post("/api/auth/login", json=payload, headers=bob).status_code
    finally:
        settings.trusted_proxy_hops, settings.auth_rate_limit = original
        limiter.reset()
    assert alice_codes == [401, 401, 429]
    # Same proxy, different person: they don't share alice's bucket.
    assert bob_code == 401
