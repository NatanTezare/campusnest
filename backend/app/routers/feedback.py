from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import current_user, require_role

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=schemas.FeedbackOut, status_code=201)
def submit_feedback(data: schemas.FeedbackIn, user: models.User = Depends(require_role("student")),
                    db: Session = Depends(get_db)):
    """A student submits (or updates) their evaluation. One response per student."""
    fb = db.scalar(select(models.Feedback).where(models.Feedback.user_id == user.id))
    values = data.model_dump()
    values["comment"] = (values["comment"] or "").strip() or None
    if fb:
        for k, v in values.items():
            setattr(fb, k, v)
    else:
        fb = models.Feedback(user_id=user.id, **values)
        db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@router.get("/mine", response_model=schemas.FeedbackOut | None)
def my_feedback(user: models.User = Depends(require_role("student")), db: Session = Depends(get_db)):
    return db.scalar(select(models.Feedback).where(models.Feedback.user_id == user.id))


def _avg(values):
    return round(sum(values) / len(values), 2) if values else None


@router.get("/summary", response_model=schemas.FeedbackSummary)
def feedback_summary(_: models.User = Depends(current_user), db: Session = Depends(get_db)):
    """Aggregated results only (no names, no comments) for the project evaluation chapter."""
    rows = db.scalars(select(models.Feedback)).all()
    paired = [r for r in rows if r.manual_hours]  # students who gave both the old-way and CampusNest times
    saved = None
    if paired:
        manual = sum(r.manual_hours for r in paired) / len(paired)
        campusnest_hours = sum(r.campusnest_minutes for r in paired) / len(paired) / 60
        saved = round((1 - campusnest_hours / manual) * 100, 1)
    return schemas.FeedbackSummary(
        responses=len(rows),
        avg_ease=_avg([r.ease for r in rows]),
        avg_campusnest_minutes=_avg([r.campusnest_minutes for r in rows]),
        avg_manual_hours=_avg([r.manual_hours for r in paired]),
        time_saved_pct=saved,
        would_recommend_pct=round(100 * sum(r.would_recommend for r in rows) / len(rows), 1) if rows else None,
    )
