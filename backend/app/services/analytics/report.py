from dataclasses import dataclass, field

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(frozen=True)
class Bucket:
    key: str
    applied: int
    responded: int

    @property
    def rate(self) -> float | None:
        return self.responded / self.applied if self.applied else None


@dataclass
class PulseReport:
    applied: int
    responded: int
    median_days_to_response: float | None
    by_source: list[Bucket] = field(default_factory=list)
    by_role_type: list[Bucket] = field(default_factory=list)
    by_weekday: list[Bucket] = field(default_factory=list)


def finish_buckets(counts: dict[str, list[int]]) -> list[Bucket]:
    """Biggest first, ties by name, so both implementations sort the same way."""
    buckets = [Bucket(key, applied, responded) for key, (applied, responded) in counts.items()]
    return sorted(buckets, key=lambda b: (-b.applied, b.key))


def weekday_buckets(counts: dict[int, list[int]]) -> list[Bucket]:
    return [
        Bucket(WEEKDAYS[i], counts.get(i, [0, 0])[0], counts.get(i, [0, 0])[1]) for i in range(7)
    ]
