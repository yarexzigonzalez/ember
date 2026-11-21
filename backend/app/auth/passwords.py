from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Argon2id with library defaults (memory-hard: slow for attackers, fine for one login).
_hasher = PasswordHasher()
_dummy_hash: str | None = None


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_dummy_password(plain: str) -> None:
    """Burn the same CPU as a real verify so we don't leak whether the email exists."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = _hasher.hash("ember-nonexistent-user-dummy")
    verify_password(plain, _dummy_hash)
