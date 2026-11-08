import pytest

from app import import_hostels as imp
from conftest import signup

HEADER = "name,area,distance_km,phone,amenities,rooms,description\n"


def test_parse_rooms_and_amenities():
    assert imp.parse_rooms("Single room:11,000; twin sharing:7500:full") == [
        {"name": "Single room", "price": 11000, "available": True},
        {"name": "Twin sharing", "price": 7500, "available": False}]
    assert imp.parse_amenities("wifi; WATER BACKUP") == ["WiFi", "Water backup"]
    assert imp.parse_rooms("") == [] and imp.parse_amenities(None) == []


@pytest.mark.parametrize("bad,fragment", [
    ("Penthouse:9000", "unknown room type"), ("Single room:abc", "not a number"), ("Single room", "should look like")])
def test_bad_rooms_give_friendly_errors(bad, fragment):
    with pytest.raises(imp.RowError, match=fragment):
        imp.parse_rooms(bad)


def test_parse_row_validates_like_the_website():
    ok = imp.parse_row({"name": "A Hostel", "distance_km": "0.8", "rooms": "Single room:9000", "amenities": "WiFi"})
    assert ok.rooms[0].price == 9000 and ok.amenities == ["WiFi"]
    with pytest.raises(imp.RowError, match="distance_km must be a number"):
        imp.parse_row({"name": "A Hostel", "distance_km": "far", "rooms": "Single room:9000"})
    with pytest.raises(imp.RowError, match="rooms"):
        imp.parse_row({"name": "A Hostel", "distance_km": "1", "rooms": ""})       # at least one room type needed


def test_run_imports_skips_duplicates_reports_errors_and_dry_run(client, tmp_path):
    signup(client, "owner", "owner@example.com")
    csv_file = tmp_path / "h.csv"
    csv_file.write_text(HEADER +
        "Alpha Hostel,Roysambu,0.9,0712,WiFi;Security,Single room:10500;Twin sharing:7000,nice\n"
        "Beta Hostel,Mirema,1.4,,WiFi,Studio:15000:full,\n"
        "Broken Hostel,Mirema,xx,,WiFi,Single room:9000,\n"
        "alpha hostel,Roysambu,0.9,,WiFi,Single room:9999,dup\n", encoding="utf-8")
    dry = imp.run(str(csv_file), "owner@example.com", dry_run=True)
    assert dry["added"] == 2 and client.get("/api/hostels").json() == []           # nothing saved
    real = imp.run(str(csv_file), "owner@example.com")
    assert real["added"] == 2 and real["skipped"] == ["alpha hostel"]
    assert real["errors"] == [(4, "distance_km must be a number such as 0.8")]
    hostels = {h["name"]: h for h in client.get("/api/hostels").json()}
    assert hostels["Alpha Hostel"]["price_from"] == 7000 and len(hostels["Alpha Hostel"]["rooms"]) == 2
    assert hostels["Beta Hostel"]["available"] is False
    again = imp.run(str(csv_file), "owner@example.com")                             # re-running adds nothing
    assert again["added"] == 0


def test_run_requires_an_owner_account(client, tmp_path):
    signup(client, "student", "stu@example.com")
    f = tmp_path / "h.csv"
    f.write_text(HEADER, encoding="utf-8")
    with pytest.raises(SystemExit):
        imp.run(str(f), "stu@example.com")
    with pytest.raises(SystemExit):
        imp.run(str(f), "nobody@example.com")
