import os
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..scoring import Preferences, score_hostel
from ..security import require_role
from ..serializers import hostel_out, review_out

router = APIRouter(prefix="/hostels", tags=["hostels"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_PHOTOS = 6
MAX_SIDE = 1280          # photos are shrunk to at most 1280 px on the longest side
Image.MAX_IMAGE_PIXELS = 40_000_000  # refuse "decompression bomb" images

_LOAD = (selectinload(models.Hostel.amenities), selectinload(models.Hostel.rooms), selectinload(models.Hostel.photos),
         selectinload(models.Hostel.reviews), selectinload(models.Hostel.flags))


def _all_hostels(db: Session):
    return db.scalars(select(models.Hostel).options(*_LOAD)).all()


def _get_or_404(db: Session, hostel_id: int) -> models.Hostel:
    h = db.scalar(select(models.Hostel).options(*_LOAD).where(models.Hostel.id == hostel_id))
    if not h:
        raise HTTPException(404, "Hostel not found")
    return h


def _owned_or_403(h: models.Hostel, user: models.User) -> None:
    if h.owner_id != user.id:
        raise HTTPException(403, "You can only manage your own hostels")


def _resolve_amenities(db: Session, names: list[str]) -> list[models.Amenity]:
    clean, seen = [], set()
    for n in names:
        n = n.strip()
        if n.lower() in seen:
            continue
        if n not in schemas.AMENITIES:
            raise HTTPException(422, f"Unknown amenity '{n}'. Allowed: {', '.join(schemas.AMENITIES)}")
        seen.add(n.lower())
        clean.append(n)
    return list(db.scalars(select(models.Amenity).where(models.Amenity.name.in_(clean))).all()) if clean else []


def _sync_rooms(h: models.Hostel, wanted: list[schemas.RoomIn]) -> None:
    """Make the hostel's room types match `wanted` (keyed by room-type name):
    update existing ones, add new ones, remove the ones no longer listed."""
    by_name = {r.name: r for r in h.rooms}
    keep = set()
    for w in wanted:
        keep.add(w.name)
        if w.name in by_name:
            by_name[w.name].price, by_name[w.name].available = w.price, w.available
        else:
            h.rooms.append(models.RoomType(name=w.name, price=w.price, available=w.available))
    for name, room in by_name.items():
        if name not in keep:
            h.rooms.remove(room)


def _normalise_image(data: bytes) -> bytes:
    """Re-encode an upload as a compressed JPEG: smaller files, and EXIF metadata (e.g. GPS location) is dropped."""
    try:
        with Image.open(BytesIO(data)) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                rgba = im.convert("RGBA")
                flat = Image.new("RGB", rgba.size, "white")
                flat.paste(rgba, mask=rgba.split()[-1])
                im = flat
            else:
                im = im.convert("RGB")
            im.thumbnail((MAX_SIDE, MAX_SIDE))
            out = BytesIO()
            im.save(out, "JPEG", quality=82, optimize=True)
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(415, "That file could not be read as an image")


def _sniff_image(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


# ---- fixed paths first (so "mine"/"recommend"/"compare" are not read as an id) ----

@router.get("", response_model=list[schemas.HostelOut])
def list_hostels(q: str | None = Query(default=None, max_length=100),
                 available_only: bool = False, db: Session = Depends(get_db)):
    """FR2 + search by name: all hostels, optionally filtered by a name fragment."""
    hostels = _all_hostels(db)
    if q and q.strip():
        needle = q.strip().lower()
        hostels = [h for h in hostels if needle in h.name.lower()]
    if available_only:
        hostels = [h for h in hostels if any(r.available for r in h.rooms)]
    return [hostel_out(h) for h in sorted(hostels, key=lambda h: h.name.lower())]


@router.get("/mine", response_model=list[schemas.HostelOut])
def my_hostels(user: models.User = Depends(require_role("owner")), db: Session = Depends(get_db)):
    hostels = db.scalars(select(models.Hostel).options(*_LOAD)
                         .where(models.Hostel.owner_id == user.id)
                         .order_by(models.Hostel.id.desc())).all()
    return [hostel_out(h) for h in hostels]


@router.post("/recommend", response_model=list[schemas.RecommendationOut])
def recommend(prefs: schemas.RecommendIn, db: Session = Depends(get_db)):
    """FR3: rank hostels against the student's preferences (fuzzy-logic engine).
    Each hostel is scored by its best matching room type; if the student asked for a
    specific room type, hostels without it are left out."""
    for a in prefs.amenities:
        if a not in schemas.AMENITIES:
            raise HTTPException(422, f"Unknown amenity '{a}'")
    wanted_type = prefs.room_type if prefs.room_type and prefs.room_type != "Any" else None
    if wanted_type and wanted_type not in schemas.ROOM_TYPES:
        raise HTTPException(422, f"Unknown room type '{wanted_type}'")
    p = Preferences(budget=prefs.budget, max_distance_km=prefs.max_distance_km,
                    amenities=prefs.amenities, weights=prefs.weights)
    results = []
    for h in _all_hostels(db):
        out = hostel_out(h)
        candidates = [r for r in out.rooms if not wanted_type or r.name == wanted_type]
        best = None
        for room in candidates:
            res = score_hostel(price=room.price, distance_km=out.distance_km, amenities=out.amenities,
                               avg_rating=out.avg_rating, review_count=out.review_count,
                               available=room.available, prefs=p)
            if best is None or (res.score, -room.price) > (best[0].score, -best[1].price):
                best = (res, room)
        if best is None:
            continue
        res, room = best
        reasons = ([f"Best fit: {room.name} at KES {room.price:,.0f} per person"] if len(out.rooms) > 1 else []) + res.reasons
        results.append(schemas.RecommendationOut(**out.model_dump(), best_room=room, score=res.score,
                                                 parts=res.parts, reasons=reasons))
    results.sort(key=lambda r: (-r.score, r.best_room.price))
    return results


@router.get("/compare", response_model=schemas.CompareOut)
def compare(ids: str = Query(description="Comma-separated hostel ids, 2 to 3"),
            db: Session = Depends(get_db)):
    """FR4: side-by-side data plus which hostel wins each criterion."""
    try:
        wanted = [int(i) for i in ids.split(",") if i.strip()]
    except ValueError:
        raise HTTPException(422, "ids must be comma-separated integers")
    wanted = list(dict.fromkeys(wanted))
    if not 2 <= len(wanted) <= 3:
        raise HTTPException(422, "Choose 2 or 3 hostels to compare")
    hostels = [hostel_out(_get_or_404(db, i)) for i in wanted]
    best = {
        "price": min(hostels, key=lambda h: h.price_from).id,
        "distance": min(hostels, key=lambda h: h.distance_km).id,
        "rating": max(hostels, key=lambda h: h.avg_rating or 0).id if any(h.avg_rating for h in hostels) else None,
        "amenities": max(hostels, key=lambda h: len(h.amenities)).id,
    }
    return schemas.CompareOut(hostels=hostels, best=best)


@router.post("", response_model=schemas.HostelOut, status_code=201)
def create_hostel(data: schemas.HostelIn, user: models.User = Depends(require_role("owner")),
                  db: Session = Depends(get_db)):
    """FR5: owner publishes a listing."""
    h = models.Hostel(owner_id=user.id, name=data.name.strip(), location=data.location,
                      distance_km=data.distance_km, description=data.description,
                      contact_phone=data.contact_phone)
    h.amenities = _resolve_amenities(db, data.amenities)
    _sync_rooms(h, data.rooms)
    db.add(h)
    db.commit()
    return hostel_out(_get_or_404(db, h.id))


# ---- by id ----

@router.get("/{hostel_id}", response_model=schemas.HostelDetail)
def hostel_detail(hostel_id: int, db: Session = Depends(get_db)):
    h = _get_or_404(db, hostel_id)
    return schemas.HostelDetail(**hostel_out(h).model_dump(),
                                reviews=[review_out(r) for r in h.reviews])


@router.put("/{hostel_id}", response_model=schemas.HostelOut)
def update_hostel(hostel_id: int, data: schemas.HostelUpdate,
                  user: models.User = Depends(require_role("owner")), db: Session = Depends(get_db)):
    """Owner edits room types/prices/availability, amenities, etc. (changes are visible to students at once)."""
    h = _get_or_404(db, hostel_id)
    _owned_or_403(h, user)
    changes = data.model_dump(exclude_unset=True)
    if "amenities" in changes:
        h.amenities = _resolve_amenities(db, changes.pop("amenities") or [])
    if data.rooms is not None:
        changes.pop("rooms", None)
        _sync_rooms(h, data.rooms)
    for key, value in changes.items():
        if value is None and key in ("name", "distance_km"):
            continue  # these columns are required; ignore explicit nulls
        setattr(h, key, value.strip() if key == "name" and isinstance(value, str) else value)
    db.commit()
    return hostel_out(_get_or_404(db, hostel_id))


@router.delete("/{hostel_id}", status_code=204)
def delete_hostel(hostel_id: int, user: models.User = Depends(require_role("owner")),
                  db: Session = Depends(get_db)):
    h = _get_or_404(db, hostel_id)
    _owned_or_403(h, user)
    for p in h.photos:
        if not p.content_type:  # legacy photo stored on disk
            (UPLOAD_DIR / p.filename).unlink(missing_ok=True)
    db.delete(h)
    db.commit()


@router.post("/{hostel_id}/photos", response_model=schemas.HostelOut, status_code=201)
async def upload_photo(hostel_id: int, file: UploadFile = File(...),
                       user: models.User = Depends(require_role("owner")), db: Session = Depends(get_db)):
    h = _get_or_404(db, hostel_id)
    _owned_or_403(h, user)
    if len(h.photos) >= MAX_PHOTOS:
        raise HTTPException(422, f"A hostel can have at most {MAX_PHOTOS} photos")
    data = await file.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(413, "Photo is larger than 5 MB")
    if not _sniff_image(data):
        raise HTTPException(415, "Only JPEG, PNG or WebP images are allowed")
    h.photos.append(models.Photo(filename=f"{uuid.uuid4().hex}.jpg", content_type="image/jpeg",
                                 data=_normalise_image(data)))
    db.commit()
    return hostel_out(_get_or_404(db, hostel_id))


@router.delete("/{hostel_id}/photos/{photo_id}", response_model=schemas.HostelOut)
def delete_photo(hostel_id: int, photo_id: int, user: models.User = Depends(require_role("owner")),
                 db: Session = Depends(get_db)):
    h = _get_or_404(db, hostel_id)
    _owned_or_403(h, user)
    photo = next((p for p in h.photos if p.id == photo_id), None)
    if not photo:
        raise HTTPException(404, "Photo not found")
    if not photo.content_type:
        (UPLOAD_DIR / photo.filename).unlink(missing_ok=True)
    h.photos.remove(photo)
    db.commit()
    return hostel_out(_get_or_404(db, hostel_id))


@router.get("/{hostel_id}/flags", response_model=list[schemas.FlagOut])
def list_flags(hostel_id: int, user: models.User = Depends(require_role("owner")), db: Session = Depends(get_db)):
    """FR7: the owner sees the open reports on their listing (reason and date only, not who reported)."""
    h = _get_or_404(db, hostel_id)
    _owned_or_403(h, user)
    return [f for f in sorted(h.flags, key=lambda f: f.created_at, reverse=True) if not f.resolved]


@router.post("/{hostel_id}/flags/resolve", response_model=schemas.HostelOut)
def resolve_flags(hostel_id: int, user: models.User = Depends(require_role("owner")), db: Session = Depends(get_db)):
    """The owner confirms they have corrected the listing; open reports are cleared."""
    h = _get_or_404(db, hostel_id)
    _owned_or_403(h, user)
    for f in h.flags:
        f.resolved = True
    db.commit()
    return hostel_out(_get_or_404(db, hostel_id))
