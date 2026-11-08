"""Pydantic request/response models."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

AMENITIES = ["WiFi", "Water backup", "Security", "Kitchen", "Study desk", "Laundry"]
ROOM_TYPES = ["Single room", "Twin sharing", "Triple sharing", "Bedsitter", "Studio"]


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)
    role: Literal["student", "owner"] = "student"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RoomIn(BaseModel):
    name: str
    price: int = Field(gt=0, le=500_000, description="KES per person per month")
    available: bool = True

    @field_validator("name")
    @classmethod
    def _known_type(cls, v: str) -> str:
        v = v.strip()
        if v not in ROOM_TYPES:
            raise ValueError(f"Unknown room type '{v}'. Allowed: {', '.join(ROOM_TYPES)}")
        return v


def _unique_rooms(rooms):
    names = [r.name for r in rooms]
    if len(names) != len(set(names)):
        raise ValueError("Each room type can only be listed once per hostel")
    return rooms


class HostelIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    distance_km: float = Field(ge=0, le=50)
    rooms: list[RoomIn] = Field(min_length=1, max_length=6)
    amenities: list[str] = []
    description: str | None = Field(default=None, max_length=1000)
    contact_phone: str | None = Field(default=None, max_length=30)

    _rooms_unique = field_validator("rooms")(_unique_rooms)


class HostelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    distance_km: float | None = Field(default=None, ge=0, le=50)
    rooms: list[RoomIn] | None = Field(default=None, min_length=1, max_length=6)
    amenities: list[str] | None = None
    description: str | None = Field(default=None, max_length=1000)
    contact_phone: str | None = Field(default=None, max_length=30)

    @field_validator("rooms")
    @classmethod
    def _rooms_unique(cls, v):
        return _unique_rooms(v) if v else v


class RoomOut(BaseModel):
    id: int
    name: str
    price: int
    available: bool


class HostelOut(BaseModel):
    id: int
    owner_id: int
    name: str
    location: str | None
    distance_km: float
    price_from: int  # cheapest bookable room (falls back to cheapest overall)
    available: bool  # true if at least one room type is available
    rooms: list[RoomOut]
    description: str | None
    contact_phone: str | None
    amenities: list[str]
    photos: list[str]
    photo_ids: list[int]
    avg_rating: float | None
    review_count: int
    flag_count: int


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=3, max_length=1000)


class ReviewOut(BaseModel):
    id: int
    student_name: str  # first name only (NFR: privacy)
    rating: int
    comment: str
    created_at: datetime


class HostelDetail(HostelOut):
    reviews: list[ReviewOut]


class FlagIn(BaseModel):
    reason: str = Field(default="", max_length=300)


class FlagOut(BaseModel):
    """What an owner sees about a report: the reason and when, never who sent it."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    reason: str
    created_at: datetime


class RecommendIn(BaseModel):
    budget: int = Field(gt=0, le=500_000, description="KES per person per month")
    room_type: str | None = None  # None / "Any" = all room types
    max_distance_km: float = Field(gt=0, le=50)
    amenities: list[str] = []
    weights: dict[str, float] | None = None


class RecommendationOut(HostelOut):
    best_room: RoomOut
    score: int
    parts: dict[str, float]
    reasons: list[str]


class CompareOut(BaseModel):
    hostels: list[HostelOut]
    best: dict[str, int | None]  # criterion -> hostel id with the best value


class FeedbackIn(BaseModel):
    manual_hours: float | None = Field(default=None, ge=0, le=500,
                                       description="Hours the old way (walking around, asking friends) took")
    campusnest_minutes: int = Field(ge=0, le=600, description="Minutes it took with CampusNest")
    ease: int = Field(ge=1, le=5)
    would_recommend: bool
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackOut(FeedbackIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class FeedbackSummary(BaseModel):
    responses: int
    avg_ease: float | None
    avg_campusnest_minutes: float | None
    avg_manual_hours: float | None
    time_saved_pct: float | None  # CampusNest vs the old way, only students who answered both
    would_recommend_pct: float | None
