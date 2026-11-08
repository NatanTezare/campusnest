"""ORM models. Mirrors the ER diagram in the proposal (Chapter 4.2):
User (student/owner), Hostel, Amenity, Hostel_Amenity (junction), Review,
plus Photo and Flag which support FR5 and FR7."""
from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        LargeBinary, String, Table, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now():
    return datetime.now(timezone.utc)


hostel_amenity = Table(
    "hostel_amenity", Base.metadata,
    Column("hostel_id", ForeignKey("hostels.id", ondelete="CASCADE"), primary_key=True),
    Column("amenity_id", ForeignKey("amenities.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(10))  # "student" | "owner"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Amenity(Base):
    __tablename__ = "amenities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)


class Hostel(Base):
    __tablename__ = "hostels"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    distance_km: Mapped[float] = mapped_column(Float)  # from USIU-Africa
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    owner: Mapped[User] = relationship()
    amenities: Mapped[list[Amenity]] = relationship(secondary=hostel_amenity)
    rooms: Mapped[list["RoomType"]] = relationship(cascade="all, delete-orphan", order_by="RoomType.price")
    photos: Mapped[list["Photo"]] = relationship(cascade="all, delete-orphan", order_by="Photo.id")
    reviews: Mapped[list["Review"]] = relationship(cascade="all, delete-orphan", order_by="Review.id.desc()")
    flags: Mapped[list["Flag"]] = relationship(cascade="all, delete-orphan")


class RoomType(Base):
    """A kind of room offered by a hostel (Single room, Twin sharing, Studio...).
    `price` is KES per PERSON per month, so a twin room shows each person's share."""
    __tablename__ = "room_types"
    __table_args__ = (UniqueConstraint("hostel_id", "name", name="one_room_type_per_hostel"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(30))
    price: Mapped[int] = mapped_column(Integer)
    available: Mapped[bool] = mapped_column(Boolean, default=True)


class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[int] = mapped_column(primary_key=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(80))
    # New photos live in the database so they survive hosts that wipe the disk. `content_type` is set only for
    # those rows; older rows (data is NULL) are still served from the uploads folder. `data` is deferred so
    # listing hostels never drags image bytes along.
    content_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("hostel_id", "student_id", name="one_review_per_student"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    comment: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    student: Mapped[User] = relationship()


class Flag(Base):
    __tablename__ = "flags"
    __table_args__ = (UniqueConstraint("hostel_id", "student_id", name="one_flag_per_student"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(300), default="")
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Feedback(Base):
    """One evaluation response per student (Objective v: does CampusNest save time?)."""
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    manual_hours: Mapped[float | None] = mapped_column(Float, nullable=True)  # time the old way took
    campusnest_minutes: Mapped[int] = mapped_column(Integer)                  # time it took with CampusNest
    ease: Mapped[int] = mapped_column(Integer)                                # 1 (very hard) - 5 (very easy)
    would_recommend: Mapped[bool] = mapped_column(Boolean)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
