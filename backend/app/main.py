import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, SessionLocal, engine, get_db
from .routers import auth, feedback, hostels, reviews


def _ensure_photo_columns() -> None:
    """create_all() does not add columns to tables that already exist, so databases made before photos moved
    into the database get the two new columns added here (safe to run every start)."""
    cols = {c["name"] for c in inspect(engine).get_columns("photos")}
    blob = "BYTEA" if engine.dialect.name == "postgresql" else "BLOB"
    with engine.begin() as conn:
        if "data" not in cols:
            conn.execute(text(f"ALTER TABLE photos ADD COLUMN data {blob}"))
        if "content_type" not in cols:
            conn.execute(text("ALTER TABLE photos ADD COLUMN content_type VARCHAR(30)"))


def init_db() -> None:
    Base.metadata.create_all(engine)
    _ensure_photo_columns()
    with SessionLocal() as db:
        existing = set(db.scalars(select(models.Amenity.name)).all())
        for name in schemas.AMENITIES:
            if name not in existing:
                db.add(models.Amenity(name=name))
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="CampusNest API", version="0.5.0",
              description="Hostel search, fuzzy-logic recommendation and reviews for USIU-Africa students.",
              lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(hostels.router)
api.include_router(reviews.router)
api.include_router(feedback.router)


@api.get("/amenities", tags=["meta"])
def list_amenities():
    return schemas.AMENITIES


@api.get("/photos/{photo_id}", tags=["meta"], include_in_schema=False)
def get_photo(photo_id: int, db: Session = Depends(get_db)):
    photo = db.get(models.Photo, photo_id)
    if not photo or photo.data is None:
        raise HTTPException(404, "Photo not found")
    # a photo's bytes never change (a new upload gets a new id), so browsers may cache it for a year
    return Response(photo.data, media_type=photo.content_type or "image/jpeg",
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})


@api.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(api)

_uploads = Path(os.getenv("UPLOAD_DIR", "uploads"))
_uploads.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads), name="uploads")
