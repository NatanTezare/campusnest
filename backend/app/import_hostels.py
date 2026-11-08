"""Bulk-load REAL hostels from a CSV file (export from Excel / Google Sheets).

    python -m app.import_hostels ../data/hostels.csv --owner owner@usiu.ac.ke --dry-run
    python -m app.import_hostels ../data/hostels.csv --owner owner@usiu.ac.ke

Columns:  name, area, distance_km, phone, amenities, rooms, description
  amenities : separated by ;      e.g.  WiFi;Security;Water backup
  rooms     : type:price[:full]   separated by ;   e.g.  Single room:11000;Twin sharing:7500;Studio:16000:full
              (price = KES per person per month; add :full if that room type is fully booked)
Every row is checked with the same rules as the website. Hostels whose name the owner already has are skipped.
"""
import argparse
import csv
import sys

from pydantic import ValidationError
from sqlalchemy import select

from . import models, schemas
from .database import SessionLocal
from .main import init_db
from .routers.hostels import _resolve_amenities, _sync_rooms

AMENITY_LOOKUP = {a.lower(): a for a in schemas.AMENITIES}
ROOM_LOOKUP = {r.lower(): r for r in schemas.ROOM_TYPES}
FULL_WORDS = {"full", "no", "booked", "unavailable"}


class RowError(ValueError):
    """A problem with one CSV row, written so a non-programmer can fix it."""


def _split(text: str | None) -> list[str]:
    return [p.strip() for p in (text or "").split(";") if p.strip()]


def parse_amenities(text: str | None) -> list[str]:
    out = []
    for part in _split(text):
        canonical = AMENITY_LOOKUP.get(part.lower())
        if not canonical:
            raise RowError(f"unknown amenity '{part}' (allowed: {', '.join(schemas.AMENITIES)})")
        out.append(canonical)
    return out


def parse_rooms(text: str | None) -> list[dict]:
    rooms = []
    for part in _split(text):
        bits = [b.strip() for b in part.split(":")]
        if not 2 <= len(bits) <= 3:
            raise RowError(f"room '{part}' should look like 'Single room:11000' or 'Studio:16000:full'")
        name = ROOM_LOOKUP.get(bits[0].lower())
        if not name:
            raise RowError(f"unknown room type '{bits[0]}' (allowed: {', '.join(schemas.ROOM_TYPES)})")
        try:
            price = int(bits[1].replace(",", ""))
        except ValueError:
            raise RowError(f"price '{bits[1]}' for {name} is not a number")
        rooms.append({"name": name, "price": price, "available": not (len(bits) == 3 and bits[2].lower() in FULL_WORDS)})
    return rooms


def parse_row(row: dict) -> schemas.HostelIn:
    get = lambda k: (row.get(k) or "").strip()  # noqa: E731
    try:
        distance = float(get("distance_km"))
    except ValueError:
        raise RowError("distance_km must be a number such as 0.8")
    data = dict(name=get("name"), location=get("area") or None, distance_km=distance,
                contact_phone=get("phone") or None, description=get("description") or None,
                amenities=parse_amenities(row.get("amenities")), rooms=parse_rooms(row.get("rooms")))
    try:
        return schemas.HostelIn(**data)
    except ValidationError as e:
        raise RowError("; ".join(f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()))


def run(path: str, owner_email: str, dry_run: bool = False) -> dict:
    init_db()
    result = {"added": 0, "skipped": [], "errors": []}
    with SessionLocal() as db:
        owner = db.scalar(select(models.User).where(models.User.email == owner_email.lower()))
        if not owner or owner.role != "owner":
            raise SystemExit(f"No hostel-owner account with email '{owner_email}'. Create it on the website first.")
        have = {n.lower() for n in db.scalars(select(models.Hostel.name).where(models.Hostel.owner_id == owner.id))}
        with open(path, newline="", encoding="utf-8-sig") as f:
            for line, row in enumerate(csv.DictReader(f), start=2):  # line 1 is the header
                if not any((v or "").strip() for v in row.values()):
                    continue
                try:
                    data = parse_row(row)
                except RowError as e:
                    result["errors"].append((line, str(e)))
                    continue
                if data.name.lower() in have:
                    result["skipped"].append(data.name)
                    continue
                h = models.Hostel(owner_id=owner.id, name=data.name, location=data.location, distance_km=data.distance_km,
                                  description=data.description, contact_phone=data.contact_phone)
                h.amenities = _resolve_amenities(db, data.amenities)
                _sync_rooms(h, data.rooms)
                db.add(h)
                have.add(data.name.lower())
                result["added"] += 1
        if dry_run:
            db.rollback()
        else:
            db.commit()
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Import hostels from a CSV file")
    ap.add_argument("csv_file")
    ap.add_argument("--owner", required=True, help="email of an existing hostel-owner account")
    ap.add_argument("--dry-run", action="store_true", help="check the file without saving anything")
    args = ap.parse_args()
    r = run(args.csv_file, args.owner, args.dry_run)
    print(("DRY RUN - nothing saved. " if args.dry_run else "") + f"Added {r['added']} hostel(s).")
    for name in r["skipped"]:
        print(f"  skipped (already listed): {name}")
    for line, msg in r["errors"]:
        print(f"  line {line}: {msg}")
    if r["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
