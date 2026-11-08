from app.scoring import (Preferences, amenity_fit, distance_fit, falling, normalise_weights,
                         price_fit, score_hostel, smoothed_rating)


def test_falling_membership_shape():
    assert falling(5, 10, 20) == 1.0
    assert falling(10, 10, 20) == 1.0
    assert falling(15, 10, 20) == 0.5
    assert falling(20, 10, 20) == 0.0
    assert falling(99, 10, 20) == 0.0


def test_price_and_distance_fit():
    assert price_fit(9000, 10000) == 1.0
    assert price_fit(12500, 10000) == 0.5      # halfway to 150% of budget
    assert price_fit(15000, 10000) == 0.0
    assert distance_fit(1.0, 2.0) == 1.0
    assert distance_fit(3.0, 2.0) == 0.5
    assert distance_fit(4.0, 2.0) == 0.0


def test_amenity_fit_is_case_insensitive_and_defaults_to_one():
    assert amenity_fit(["WiFi"], []) == 1.0
    assert amenity_fit(["wifi", "Security"], ["WiFi", "Security"]) == 1.0
    assert amenity_fit(["WiFi"], ["WiFi", "Kitchen"]) == 0.5


def test_rating_is_smoothed_toward_neutral():
    assert smoothed_rating(None, 0) == 0.6
    assert smoothed_rating(5.0, 1) < 1.0           # one 5-star review is not a perfect score
    assert smoothed_rating(5.0, 50) > smoothed_rating(5.0, 1)


def test_weights_are_normalised():
    w = normalise_weights({"price": 3, "distance": 1, "amenities": 0, "rating": 0})
    assert abs(sum(w.values()) - 1) < 1e-9 and w["price"] == 0.75


def _score(**kw):
    base = dict(price=10000, distance_km=1.0, amenities=["WiFi", "Security"], avg_rating=4.0,
                review_count=5, available=True,
                prefs=Preferences(budget=10000, max_distance_km=2, amenities=["WiFi", "Security"]))
    base.update(kw)
    return score_hostel(**base)


def test_good_match_scores_high_and_bad_match_low():
    assert _score().score >= 90
    assert _score(price=20000, distance_km=6, amenities=[]).score <= 25


def test_cheaper_closer_better_amenities_rank_higher():
    assert _score(price=8000).score >= _score(price=11000).score
    assert _score(distance_km=0.5).score >= _score(distance_km=3).score
    assert _score(amenities=["WiFi", "Security"]).score > _score(amenities=["WiFi"]).score


def test_fuzzy_penalty_when_over_budget_and_far():
    only_far = _score(distance_km=4.0)
    only_pricey = _score(price=15000)
    both = _score(price=15000, distance_km=4.0)
    assert both.score < min(only_far.score, only_pricey.score)


def test_unavailable_is_demoted_and_explained():
    open_, full = _score(), _score(available=False)
    assert full.score < open_.score
    assert "Currently fully booked" in full.reasons


def test_reasons_are_human_readable():
    r = _score(amenities=["WiFi"]).reasons
    assert any("Missing: Security" in x for x in r)
    assert any("Rated 4.0/5" in x for x in r)
