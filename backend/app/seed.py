"""Load SAMPLE data for demos:  python -m app.seed        (add --reset to drop and rebuild all tables)
Hostel names/prices are placeholders; replace them with the real data collected
from the student survey and hostel owners (see proposal Section 3.1)."""
from sqlalchemy import select

from . import models
from .main import init_db
from .database import Base, SessionLocal, engine
from .security import hash_password

# (name, area, distance km, amenities, [(room type, KES per person/month, available)], [(reviewer, stars, text)])
HOSTELS = [
    ("Roysambu Heights", "Roysambu", 0.8, ["WiFi", "Water backup", "Security", "Kitchen"],
     [("Single room", 11000, True), ("Twin sharing", 7500, True)],
     [("Amina", 5, "Water is reliable and the walk to campus is short."),
      ("Brian", 4, "Quiet at night, WiFi slows at peak hours.")]),
    ("Mirema Court", "Mirema", 1.2, ["WiFi", "Security", "Kitchen"],
     [("Single room", 9500, True), ("Twin sharing", 6500, True), ("Triple sharing", 5200, False)],
     [("Sara", 4, "Good value, shared kitchen is clean.")]),
    ("Kasarani Nest", "Kasarani", 2.4, ["Water backup", "Security"],
     [("Bedsitter", 7800, True)],
     [("Kevin", 4, "Cheap and safe, but a matatu ride away.")]),
    ("Thika Rd Studios", "Roysambu", 1.0, ["WiFi", "Water backup", "Security", "Kitchen", "Study desk"],
     [("Studio", 14500, True), ("Single room", 12000, True), ("Twin sharing", 8000, True)],
     [("Lina", 5, "Study desks in every room. Worth the price.")]),
    ("Zimmerman Lodge", "Zimmerman", 3.1, ["Security"],
     [("Single room", 6500, False)],
     [("Omar", 3, "Budget friendly, basic facilities.")]),
    ("Garden Estate Hostel", "Garden Estate", 1.5, ["WiFi", "Security", "Laundry", "Study desk"],
     [("Single room", 12500, True), ("Studio", 16000, True)], []),
]


def _user(db, name, email, password, role):
    u = db.scalar(select(models.User).where(models.User.email == email))
    if not u:
        u = models.User(name=name, email=email, password_hash=hash_password(password), role=role)
        db.add(u)
        db.flush()
    return u


def run(reset: bool = False) -> None:
    if reset:  # wipes ALL tables (use after a schema change, never on real data)
        Base.metadata.drop_all(engine)
        print("Dropped all tables.")
    init_db()
    with SessionLocal() as db:
        owner = _user(db, "Demo Owner", "owner@usiu.ac.ke", "owner123", "owner")
        _user(db, "Demo Student", "student@usiu.ac.ke", "student123", "student")
        if db.scalar(select(models.Hostel.id).limit(1)):
            print("Hostels already present, skipping sample hostels.")
            db.commit()
            return
        amen = {a.name: a for a in db.scalars(select(models.Amenity))}
        for name, loc, dist, ams, rooms, revs in HOSTELS:
            h = models.Hostel(owner_id=owner.id, name=name, location=loc, distance_km=dist,
                              amenities=[amen[a] for a in ams],
                              rooms=[models.RoomType(name=n, price=pr, available=av) for n, pr, av in rooms])
            for who, stars, text in revs:
                s = _user(db, who, f"{who.lower()}@usiu.ac.ke", "student123", "student")
                h.reviews.append(models.Review(student_id=s.id, rating=stars, comment=text))
            db.add(h)
        db.commit()
        print("Seeded sample data.\n  owner   : owner@usiu.ac.ke / owner123\n  student : student@usiu.ac.ke / student123")


if __name__ == "__main__":
    import sys
    run(reset="--reset" in sys.argv)
