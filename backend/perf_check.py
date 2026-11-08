"""NFR2 evidence: how fast are search and ranking with lots of hostels?   Run from backend/:  python perf_check.py

Builds a throw-away SQLite database with 500 random hostels (3 room types, 3 amenities each, some reviews),
calls the real API 7 times and prints the median and worst time. Your proposal's limit is 3,000 ms for 200+ listings.
It never touches your real database. Local numbers are a best case; a hosted server adds network time.
"""
import os, tempfile, time, random, statistics
tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/perf.db"; os.environ["UPLOAD_DIR"] = f"{tmp}/up"; os.environ["PBKDF2_ITERATIONS"] = "1000"
from fastapi.testclient import TestClient
from app.main import app, init_db
from app.database import SessionLocal
from app import models
from sqlalchemy import select
init_db(); random.seed(1)
with SessionLocal() as db:
    owner = models.User(name="O", email="o@x.com", password_hash="x", role="owner"); stu = models.User(name="S", email="s@x.com", password_hash="x", role="student")
    db.add_all([owner, stu]); db.flush()
    amen = list(db.scalars(select(models.Amenity)))
    N = 500
    for i in range(N):
        h = models.Hostel(owner_id=owner.id, name=f"Hostel {i}", distance_km=round(random.uniform(.3, 5), 1), amenities=random.sample(amen, 3),
            rooms=[models.RoomType(name=n, price=random.randint(5000, 20000)) for n in random.sample(["Single room","Twin sharing","Studio","Bedsitter"], 3)])
        h.reviews = [models.Review(student_id=stu.id, rating=random.randint(1,5), comment="ok") ] if i % 2 else []
        db.add(h)
    db.commit()
with TestClient(app) as c:
    body = {"budget": 12000, "max_distance_km": 2, "amenities": ["WiFi", "Security"]}
    for label, path, fn in [("recommend", "/api/hostels/recommend", lambda: c.post("/api/hostels/recommend", json=body)),
                            ("list/search", "/api/hostels?q=Hostel 4", lambda: c.get("/api/hostels", params={"q": "Hostel 4"}))]:
        times = []
        for _ in range(7):
            t = time.perf_counter(); r = fn(); times.append((time.perf_counter() - t) * 1000); assert r.status_code == 200
        print(f"{label:12} {N} hostels: median {statistics.median(times):.0f} ms, worst {max(times):.0f} ms  (limit 3000 ms)")
