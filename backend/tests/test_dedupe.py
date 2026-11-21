from app.services.dedupe import make_dedupe_key, normalize_part


def test_normalize_collapses_case_and_space() -> None:
    assert normalize_part("  Stripe   ") == "stripe"
    assert normalize_part(None) == ""
    assert normalize_part("") == ""


def test_dedupe_key_ignores_cosmetic_differences() -> None:
    left = make_dedupe_key("Stripe", "Backend Intern", "https://stripe.com/jobs/1")
    right = make_dedupe_key(" stripe ", "backend   intern", "https://stripe.com/jobs/1")
    assert left == right


def test_different_link_is_a_different_job() -> None:
    left = make_dedupe_key("Stripe", "Backend Intern", "https://stripe.com/a")
    right = make_dedupe_key("Stripe", "Backend Intern", "https://stripe.com/b")
    assert left != right
