from enum import StrEnum


class ApplicationStatus(StrEnum):
    """Pipeline columns. Stored as plain TEXT so adding a status later is easy."""

    SAVED = "saved"
    APPLIED = "applied"
    OA = "oa"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    GHOSTED = "ghosted"


STATUS_VALUES = tuple(status.value for status in ApplicationStatus)
