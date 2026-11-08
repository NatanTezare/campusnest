from . import models, schemas


def hostel_out(h: models.Hostel) -> schemas.HostelOut:
    ratings = [r.rating for r in h.reviews]
    rooms = sorted(h.rooms, key=lambda r: (r.price, r.name))
    bookable = [r for r in rooms if r.available]
    return schemas.HostelOut(
        id=h.id, owner_id=h.owner_id, name=h.name, location=h.location,
        distance_km=h.distance_km, price_from=min(r.price for r in (bookable or rooms)),
        available=bool(bookable),
        rooms=[schemas.RoomOut(id=r.id, name=r.name, price=r.price, available=r.available) for r in rooms],
        description=h.description,
        contact_phone=h.contact_phone,
        amenities=sorted(a.name for a in h.amenities),
        photos=[f"/api/photos/{p.id}" if p.content_type else f"/uploads/{p.filename}" for p in h.photos],
        photo_ids=[p.id for p in h.photos],
        avg_rating=round(sum(ratings) / len(ratings), 2) if ratings else None,
        review_count=len(ratings),
        flag_count=sum(1 for f in h.flags if not f.resolved),
    )


def review_out(r: models.Review) -> schemas.ReviewOut:
    first = (r.student.name or "Student").split()[0]
    return schemas.ReviewOut(id=r.id, student_name=first, rating=r.rating,
                             comment=r.comment, created_at=r.created_at)
