"""Database engine/session. SQLite by default; set DATABASE_URL for PostgreSQL."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

def normalise_database_url(url: str) -> str:
    """Hosting providers give 'postgres://' or 'postgresql://' URLs; SQLAlchemy needs the psycopg driver named."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = normalise_database_url(os.getenv("DATABASE_URL", "sqlite:///./campusnest.db"))
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# pool_pre_ping: cloud databases (e.g. Neon) drop idle connections; test each one before use.
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
