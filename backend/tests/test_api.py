import base64

from conftest import make_hostel, signup

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def test_auth_flow_and_duplicate_email(client):
    h = signup(client, "student", "a@example.com")
    assert client.get("/api/auth/me", headers=h).json()["role"] == "student"
    r = client.post("/api/auth/register", json={"name": "Dup", "email": "A@example.com", "password": "secret1"})
    assert r.status_code == 409
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "nope"}).status_code == 401
    ok = client.post("/api/auth/login", json={"email": "a@example.com", "password": "secret1"})
    assert ok.status_code == 200 and ok.json()["access_token"]


def test_requires_login_and_correct_role(client, owner, student):
    assert client.get("/api/hostels/mine").status_code == 401
    body = {"name": "X Hostel", "distance_km": 1, "rooms": [{"name": "Single room", "price": 5000}]}
    assert client.post("/api/hostels", json=body, headers=student).status_code == 403   # students cannot add
    assert client.post("/api/hostels", json=body, headers=owner).status_code == 201
    assert client.post("/api/hostels/1/reviews", json={"rating": 5, "comment": "great"}, headers=owner).status_code == 403


def test_owner_creates_edits_and_students_see_the_change(client, owner, student):
    h = make_hostel(client, owner)
    r = client.put(f"/api/hostels/{h['id']}", json={
        "rooms": [{"name": "Single room", "price": 12500, "available": False}],
        "amenities": ["WiFi", "Kitchen"]}, headers=owner)
    assert r.status_code == 200
    seen = client.get(f"/api/hostels/{h['id']}", headers=student).json()
    assert seen["price_from"] == 12500 and seen["available"] is False and seen["amenities"] == ["Kitchen", "WiFi"]
    assert client.get("/api/hostels/mine", headers=owner).json()[0]["id"] == h["id"]


def test_owner_cannot_touch_someone_elses_hostel(client, owner):
    h = make_hostel(client, owner)
    other = signup(client, "owner", "other@example.com")
    assert client.put(f"/api/hostels/{h['id']}", json={"distance_km": 1}, headers=other).status_code == 403
    assert client.delete(f"/api/hostels/{h['id']}", headers=other).status_code == 403
    assert client.delete(f"/api/hostels/{h['id']}", headers=owner).status_code == 204
    assert client.get(f"/api/hostels/{h['id']}").status_code == 404


def test_validation_rejects_bad_input(client, owner):
    bad = {"name": "A", "distance_km": 1, "rooms": [{"name": "Single room", "price": -5}]}
    assert client.post("/api/hostels", json=bad, headers=owner).status_code == 422
    bad2 = {"name": "Okay Name", "distance_km": 1, "rooms": [{"name": "Single room", "price": 5000}], "amenities": ["Jacuzzi"]}
    assert client.post("/api/hostels", json=bad2, headers=owner).status_code == 422


def test_search_by_name(client, owner):
    make_hostel(client, owner, name="Roysambu Heights")
    make_hostel(client, owner, name="Mirema Court")
    names = [h["name"] for h in client.get("/api/hostels", params={"q": "heights"}).json()]
    assert names == ["Roysambu Heights"]
    assert len(client.get("/api/hostels").json()) == 2
    assert client.get("/api/hostels", params={"q": "zzz"}).json() == []


def test_recommend_ranks_by_fit_and_explains(client, owner):
    good = make_hostel(client, owner, name="Good Fit", price=9000, distance_km=0.8, amenities=["WiFi", "Security"])
    make_hostel(client, owner, name="Pricey Far", price=20000, distance_km=5, amenities=[])
    r = client.post("/api/hostels/recommend", json={"budget": 10000, "max_distance_km": 2,
                                                    "amenities": ["WiFi", "Security"]})
    assert r.status_code == 200
    ranked = r.json()
    assert ranked[0]["id"] == good["id"] and ranked[0]["score"] > ranked[1]["score"]
    assert ranked[0]["reasons"] and set(ranked[0]["parts"]) == {"price", "distance", "amenities", "rating"}
    assert client.post("/api/hostels/recommend", json={"budget": 0, "max_distance_km": 2}).status_code == 422


def test_reviews_update_average_and_are_one_per_student(client, owner, student):
    h = make_hostel(client, owner)
    url = f"/api/hostels/{h['id']}/reviews"
    assert client.post(url, json={"rating": 5, "comment": "Excellent place"}, headers=student).status_code == 201
    assert client.post(url, json={"rating": 3, "comment": "Changed my mind"}, headers=student).status_code == 201
    d = client.get(f"/api/hostels/{h['id']}").json()
    assert d["review_count"] == 1 and d["avg_rating"] == 3
    assert d["reviews"][0]["student_name"] == "Sam"       # first name only
    assert client.post(url, json={"rating": 9, "comment": "bad rating"}, headers=student).status_code == 422


def test_flagging_listing(client, owner, student):
    h = make_hostel(client, owner)
    url = f"/api/hostels/{h['id']}/flag"
    assert client.post(url, json={"reason": "Price is outdated"}, headers=student).status_code == 201
    assert client.post(url, json={"reason": "again"}, headers=student).status_code == 409
    assert client.get(f"/api/hostels/{h['id']}").json()["flag_count"] == 1


def test_compare_needs_two_or_three_and_picks_best(client, owner):
    a = make_hostel(client, owner, name="Cheap One", price=6000, distance_km=2.5, amenities=["WiFi"])
    b = make_hostel(client, owner, name="Close One", price=9000, distance_km=0.4, amenities=["WiFi", "Security", "Kitchen"])
    r = client.get("/api/hostels/compare", params={"ids": f"{a['id']},{b['id']}"})
    assert r.status_code == 200
    best = r.json()["best"]
    assert best["price"] == a["id"] and best["distance"] == b["id"] and best["amenities"] == b["id"]
    assert client.get("/api/hostels/compare", params={"ids": str(a["id"])}).status_code == 422


def test_photo_upload_validates_type_and_serves_file(client, owner):
    h = make_hostel(client, owner)
    url = f"/api/hostels/{h['id']}/photos"
    bad = client.post(url, files={"file": ("x.png", b"not an image", "image/png")}, headers=owner)
    assert bad.status_code == 415
    ok = client.post(url, files={"file": ("pic.png", PNG, "image/png")}, headers=owner)
    assert ok.status_code == 201
    photo = ok.json()["photos"][0]
    assert client.get(photo).status_code == 200
    pid = client.get(f"/api/hostels/{h['id']}").json()["photos"]
    assert len(pid) == 1


def test_owner_can_delete_a_single_photo(client, owner):
    h = make_hostel(client, owner)
    up = client.post(f"/api/hostels/{h['id']}/photos", files={"file": ("a.png", PNG, "image/png")}, headers=owner).json()
    pid = up["photo_ids"][0]
    after = client.delete(f"/api/hostels/{h['id']}/photos/{pid}", headers=owner)
    assert after.status_code == 200 and after.json()["photos"] == []


# ---------------- room types ----------------

def _qwetu_like(client, owner, **over):
    """A hostel with three room types, like a purpose-built student residence."""
    rooms = [{"name": "Single room", "price": 15000}, {"name": "Twin sharing", "price": 9000},
             {"name": "Studio", "price": 20000}]
    return make_hostel(client, owner, name="Student Residence", rooms=rooms, **over)


def test_hostel_with_several_room_types(client, owner):
    h = _qwetu_like(client, owner)
    assert [r["name"] for r in h["rooms"]] == ["Twin sharing", "Single room", "Studio"]   # cheapest first
    assert h["price_from"] == 9000 and h["available"] is True


def test_room_rules_are_validated(client, owner):
    base = {"name": "Dup Hostel", "distance_km": 1}
    dup = {**base, "rooms": [{"name": "Single room", "price": 5000}, {"name": "Single room", "price": 6000}]}
    assert client.post("/api/hostels", json=dup, headers=owner).status_code == 422
    assert client.post("/api/hostels", json={**base, "rooms": []}, headers=owner).status_code == 422
    unknown = {**base, "rooms": [{"name": "Penthouse", "price": 5000}]}
    assert client.post("/api/hostels", json=unknown, headers=owner).status_code == 422


def test_owner_edits_rooms_individually(client, owner, student):
    h = _qwetu_like(client, owner)
    # change the twin price, drop the studio, add a bedsitter, mark single room full
    r = client.put(f"/api/hostels/{h['id']}", headers=owner, json={"rooms": [
        {"name": "Single room", "price": 15000, "available": False},
        {"name": "Twin sharing", "price": 9500},
        {"name": "Bedsitter", "price": 12000}]})
    assert r.status_code == 200
    got = {x["name"]: x for x in r.json()["rooms"]}
    assert set(got) == {"Single room", "Twin sharing", "Bedsitter"}
    assert got["Twin sharing"]["price"] == 9500 and got["Single room"]["available"] is False
    assert r.json()["price_from"] == 9500 and r.json()["available"] is True   # hostel still bookable
    # every room full -> hostel counts as fully booked
    full = client.put(f"/api/hostels/{h['id']}", headers=owner, json={"rooms": [
        {"name": "Twin sharing", "price": 9500, "available": False}]}).json()
    assert full["available"] is False


def test_recommend_filters_by_room_type_and_picks_best_room(client, owner):
    multi = _qwetu_like(client, owner)                                    # has Twin sharing @ 9,000
    only_single = make_hostel(client, owner, name="Singles Only", price=8000)
    prefs = {"budget": 9500, "max_distance_km": 2, "amenities": []}
    everything = client.post("/api/hostels/recommend", json=prefs).json()
    assert {h["id"] for h in everything} == {multi["id"], only_single["id"]}
    twin = client.post("/api/hostels/recommend", json={**prefs, "room_type": "Twin sharing"}).json()
    assert [h["id"] for h in twin] == [multi["id"]]                       # hostel without twin rooms excluded
    assert twin[0]["best_room"]["name"] == "Twin sharing" and twin[0]["best_room"]["price"] == 9000
    assert any("Best fit: Twin sharing" in r for r in twin[0]["reasons"])
    # with no room type chosen, the cheapest in-budget room is the best fit
    first = next(h for h in everything if h["id"] == multi["id"])
    assert first["best_room"]["name"] == "Twin sharing"
    assert client.post("/api/hostels/recommend", json={**prefs, "room_type": "Castle"}).status_code == 422


def test_fully_booked_room_is_not_the_best_fit(client, owner):
    h = make_hostel(client, owner, rooms=[{"name": "Single room", "price": 6000, "available": False},
                                          {"name": "Twin sharing", "price": 7000}])
    r = client.post("/api/hostels/recommend", json={"budget": 8000, "max_distance_km": 2}).json()
    assert r[0]["best_room"]["name"] == "Twin sharing"        # cheaper room is full, so the open one wins


def test_compare_uses_cheapest_room(client, owner):
    a = _qwetu_like(client, owner)                                         # from 9,000
    b = make_hostel(client, owner, name="Plain Hostel", price=10000)
    best = client.get("/api/hostels/compare", params={"ids": f"{a['id']},{b['id']}"}).json()["best"]
    assert best["price"] == a["id"]


# ---------------- FR7: flags can be reviewed and resolved ----------------

def test_owner_sees_flag_reasons_and_can_resolve_them(client, owner, student):
    h = make_hostel(client, owner)
    client.post(f"/api/hostels/{h['id']}/flag", json={"reason": "Price is outdated"}, headers=student)
    other_student = signup(client, "student", "other.student@example.com")
    client.post(f"/api/hostels/{h['id']}/flag", json={"reason": "Water is not reliable"}, headers=other_student)
    flags = client.get(f"/api/hostels/{h['id']}/flags", headers=owner).json()
    assert {f["reason"] for f in flags} == {"Price is outdated", "Water is not reliable"}
    assert all(set(f) == {"id", "reason", "created_at"} for f in flags)          # no reporter identity leaked
    resolved = client.post(f"/api/hostels/{h['id']}/flags/resolve", headers=owner)
    assert resolved.status_code == 200 and resolved.json()["flag_count"] == 0
    assert client.get(f"/api/hostels/{h['id']}/flags", headers=owner).json() == []


def test_only_the_hostels_owner_can_see_or_resolve_flags(client, owner, student):
    h = make_hostel(client, owner)
    other_owner = signup(client, "owner", "other.owner@example.com")
    for headers in (student, other_owner):
        assert client.get(f"/api/hostels/{h['id']}/flags", headers=headers).status_code == 403
        assert client.post(f"/api/hostels/{h['id']}/flags/resolve", headers=headers).status_code == 403
    assert client.get(f"/api/hostels/{h['id']}/flags").status_code == 401


def test_student_can_flag_again_after_it_was_resolved(client, owner, student):
    h = make_hostel(client, owner)
    url = f"/api/hostels/{h['id']}/flag"
    assert client.post(url, json={"reason": "wrong price"}, headers=student).status_code == 201
    assert client.post(url, json={"reason": "still wrong"}, headers=student).status_code == 409   # still open
    client.post(f"/api/hostels/{h['id']}/flags/resolve", headers=owner)
    assert client.post(url, json={"reason": "price changed again"}, headers=student).status_code == 201
    flags = client.get(f"/api/hostels/{h['id']}/flags", headers=owner).json()
    assert [f["reason"] for f in flags] == ["price changed again"]
