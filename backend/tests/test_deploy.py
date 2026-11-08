"""Things that matter once CampusNest is hosted: photos in the database, URL handling, startup safety."""
import io
import os
import subprocess
import sys

from PIL import Image
from sqlalchemy import inspect, text

from app.database import engine, normalise_database_url
from app.main import init_db
from conftest import make_hostel


def _png(size=(3000, 2000), color=(200, 30, 30), mode="RGB"):
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, "PNG")
    return buf.getvalue()


def test_photo_is_compressed_stored_in_db_and_cacheable(client, owner):
    h = make_hostel(client, owner)
    r = client.post(f"/api/hostels/{h['id']}/photos", files={"file": ("big.png", _png(), "image/png")}, headers=owner)
    assert r.status_code == 201
    url = r.json()["photos"][0]
    assert url.startswith("/api/photos/")                                  # served from the database, not the disk
    img = client.get(url)
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    assert "immutable" in img.headers["cache-control"]
    pic = Image.open(io.BytesIO(img.content))
    assert pic.format == "JPEG" and max(pic.size) == 1280                  # 3000 px wide upload shrunk to 1280
    assert len(img.content) < 100_000                                       # and small


def test_transparent_png_and_photo_removal(client, owner):
    h = make_hostel(client, owner)
    up = client.post(f"/api/hostels/{h['id']}/photos",
                     files={"file": ("t.png", _png((40, 40), (0, 0, 0, 0), "RGBA"), "image/png")}, headers=owner).json()
    assert Image.open(io.BytesIO(client.get(up["photos"][0]).content)).getpixel((5, 5)) == (255, 255, 255)  # white, not black
    gone = client.delete(f"/api/hostels/{h['id']}/photos/{up['photo_ids'][0]}", headers=owner)
    assert gone.status_code == 200 and gone.json()["photos"] == []
    assert client.get(up["photos"][0]).status_code == 404


def test_fake_image_with_valid_header_is_rejected(client, owner):
    h = make_hostel(client, owner)
    fake = b"\xff\xd8\xff" + b"this is not really a jpeg"
    r = client.post(f"/api/hostels/{h['id']}/photos", files={"file": ("x.jpg", fake, "image/jpeg")}, headers=owner)
    assert r.status_code == 415


def test_old_database_without_photo_columns_is_upgraded_on_startup(client):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE photos"))
        conn.execute(text("CREATE TABLE photos (id INTEGER PRIMARY KEY, hostel_id INTEGER, filename VARCHAR(80))"))
    assert {"data", "content_type"}.isdisjoint(c["name"] for c in inspect(engine).get_columns("photos"))
    init_db()
    assert {"data", "content_type"} <= {c["name"] for c in inspect(engine).get_columns("photos")}
    init_db()  # running it again is harmless


def test_hosting_database_urls_are_understood():
    assert normalise_database_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalise_database_url("postgresql://u:p@h/db?sslmode=require") == "postgresql+psycopg://u:p@h/db?sslmode=require"
    assert normalise_database_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalise_database_url("sqlite:///./x.db") == "sqlite:///./x.db"


def test_production_refuses_the_default_secret_key():
    from app.security import _DEV_SECRET

    # Keep the real environment: on Windows, Python finds its installed packages through variables such as
    # APPDATA/USERPROFILE, so an empty environment makes "import jwt" fail for the wrong reason.
    base = {**os.environ, "ENVIRONMENT": "production", "DATABASE_URL": "sqlite://"}
    code = "import app.security"
    bad = subprocess.run([sys.executable, "-c", code], env={**base, "SECRET_KEY": _DEV_SECRET},
                         capture_output=True, text=True)
    assert bad.returncode != 0 and "SECRET_KEY must be set" in bad.stderr
    good = subprocess.run([sys.executable, "-c", code], env={**base, "SECRET_KEY": "x" * 40},
                          capture_output=True, text=True)
    assert good.returncode == 0, good.stderr