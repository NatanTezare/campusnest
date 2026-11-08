from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import require_role
from ..serializers import review_out

router = APIRouter(prefix="/hostels/{hostel_id}", tags=["reviews"])


def _hostel_or_404(db: Session, hostel_id: int) -> models.Hostel:
    h = db.get(models.Hostel, hostel_id)
    if not h:
        raise HTTPException(404, "Hostel not found")
    return h


@router.post("/reviews", response_model=schemas.ReviewOut, status_code=201)
def add_review(hostel_id: int, data: schemas.ReviewIn,
               user: models.User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """FR6: a student rates/reviews a hostel. One review per student; posting again updates it."""
    _hostel_or_404(db, hostel_id)
    review = db.scalar(select(models.Review).where(models.Review.hostel_id == hostel_id,
                                                   models.Review.student_id == user.id))
    if review:
        review.rating, review.comment = data.rating, data.comment.strip()
    else:
        review = models.Review(hostel_id=hostel_id, student_id=user.id,
                               rating=data.rating, comment=data.comment.strip())
        db.add(review)
    db.commit()
    db.refresh(review)
    return review_out(review)


@router.post("/flag", status_code=201)
def flag_listing(hostel_id: int, data: schemas.FlagIn,
                 user: models.User = Depends(require_role("student")), db: Session = Depends(get_db)):
    """FR7: a student reports a listing as outdated or inaccurate."""
    _hostel_or_404(db, hostel_id)
    existing = db.scalar(select(models.Flag).where(models.Flag.hostel_id == hostel_id,
                                                   models.Flag.student_id == user.id))
    if existing and not existing.resolved:
        raise HTTPException(409, "You have already flagged this listing")
    if existing:  # an earlier report was resolved; the problem has come back, so reopen it
        existing.resolved, existing.reason = False, data.reason.strip()
    else:
        db.add(models.Flag(hostel_id=hostel_id, student_id=user.id, reason=data.reason.strip()))
    db.commit()
    return {"detail": "Thanks, the owner has been notified that this listing may be inaccurate."}
