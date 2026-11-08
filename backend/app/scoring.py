"""Fuzzy-logic recommendation engine (Objective iii).

Each criterion is turned into a membership degree in [0, 1] using a simple
trapezoidal "falling" function, the degrees are combined with student-adjustable
weights, and one fuzzy rule penalises hostels that are BOTH over budget AND too far.
The engine is pure Python (no DB access) so it is easy to unit test and explain.

    membership(x) = 1                      if x <= full_until
                  = 0                      if x >= zero_at
                  = linear in between
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_WEIGHTS = {"price": 0.35, "distance": 0.25, "amenities": 0.30, "rating": 0.10}

PRICE_TOLERANCE = 1.5      # membership reaches 0 at 150% of the student's budget
DISTANCE_TOLERANCE = 2.0   # membership reaches 0 at 2x the student's max distance
NEUTRAL_RATING = 3.0       # prior used so hostels with few reviews are not over/under-rated
PRIOR_WEIGHT = 2           # equivalent number of "neutral" reviews (Bayesian average)
UNAVAILABLE_FACTOR = 0.5   # fully booked hostels are shown, but ranked lower


def falling(x: float, full_until: float, zero_at: float) -> float:
    """Trapezoidal membership: 1 up to `full_until`, then linearly down to 0 at `zero_at`."""
    if x <= full_until:
        return 1.0
    if x >= zero_at or zero_at <= full_until:
        return 0.0
    return (zero_at - x) / (zero_at - full_until)


def price_fit(price: float, budget: float) -> float:
    return falling(price, budget, budget * PRICE_TOLERANCE)


def distance_fit(distance_km: float, max_distance_km: float) -> float:
    return falling(distance_km, max_distance_km, max_distance_km * DISTANCE_TOLERANCE)


def amenity_fit(have: list[str], wanted: list[str]) -> float:
    wanted_set = {a.lower() for a in wanted}
    if not wanted_set:
        return 1.0
    have_set = {a.lower() for a in have}
    return len(wanted_set & have_set) / len(wanted_set)


def smoothed_rating(avg: float | None, count: int) -> float:
    """Bayesian average pulled toward a neutral 3.0, scaled to [0, 1]."""
    if not count or avg is None:
        return NEUTRAL_RATING / 5
    return ((avg * count + NEUTRAL_RATING * PRIOR_WEIGHT) / (count + PRIOR_WEIGHT)) / 5


def normalise_weights(weights: dict[str, float] | None) -> dict[str, float]:
    merged = {**DEFAULT_WEIGHTS, **{k: max(0.0, float(v)) for k, v in (weights or {}).items()
                                    if k in DEFAULT_WEIGHTS}}
    total = sum(merged.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {k: v / total for k, v in merged.items()}


@dataclass
class Preferences:
    budget: float
    max_distance_km: float
    amenities: list[str] = field(default_factory=list)
    weights: dict[str, float] | None = None


@dataclass
class ScoreResult:
    score: int                       # 0-100, shown to the student as "% match"
    parts: dict[str, float]          # individual membership degrees (explainability)
    reasons: list[str]               # plain-English explanation of the ranking


def score_hostel(*, price: float, distance_km: float, amenities: list[str],
                 avg_rating: float | None, review_count: int, available: bool,
                 prefs: Preferences) -> ScoreResult:
    w = normalise_weights(prefs.weights)
    parts = {
        "price": price_fit(price, prefs.budget),
        "distance": distance_fit(distance_km, prefs.max_distance_km),
        "amenities": amenity_fit(amenities, prefs.amenities),
        "rating": smoothed_rating(avg_rating, review_count),
    }
    raw = sum(w[k] * parts[k] for k in w)

    # Fuzzy rule: IF price is "too high" AND distance is "too far" THEN penalise.
    # min() is the standard fuzzy AND; at most halves the score.
    penalty = 1 - 0.5 * min(1 - parts["price"], 1 - parts["distance"])
    raw *= penalty
    if not available:
        raw *= UNAVAILABLE_FACTOR

    return ScoreResult(score=round(raw * 100), parts={k: round(v, 3) for k, v in parts.items()},
                       reasons=_reasons(price, distance_km, amenities, avg_rating, review_count,
                                        available, prefs))


def _reasons(price, distance_km, amenities, avg_rating, review_count, available, prefs) -> list[str]:
    out: list[str] = []
    if price <= prefs.budget * 0.8:
        out.append(f"Well within your budget (KES {price:,.0f})")
    elif price <= prefs.budget:
        out.append(f"Within your budget (KES {price:,.0f})")
    elif price <= prefs.budget * 1.2:
        out.append(f"Slightly over budget (KES {price:,.0f})")
    else:
        out.append(f"Over budget (KES {price:,.0f})")

    if distance_km <= prefs.max_distance_km * 0.5:
        out.append(f"Very close to campus ({distance_km:g} km)")
    elif distance_km <= prefs.max_distance_km:
        out.append(f"Walkable distance ({distance_km:g} km)")
    else:
        out.append(f"Further than you wanted ({distance_km:g} km)")

    wanted = {a.lower(): a for a in prefs.amenities}
    if wanted:
        have = {a.lower() for a in amenities}
        got = [orig for low, orig in wanted.items() if low in have]
        missing = [orig for low, orig in wanted.items() if low not in have]
        out.append(f"Has {len(got)} of {len(wanted)} amenities you need")
        if missing:
            out.append("Missing: " + ", ".join(missing))

    if review_count:
        out.append(f"Rated {avg_rating:.1f}/5 by {review_count} student{'s' if review_count != 1 else ''}")
    else:
        out.append("No reviews yet")
    if not available:
        out.append("Currently fully booked")
    return out
