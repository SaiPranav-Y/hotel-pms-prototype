"""SQLite data model for the voice agent (SQLAlchemy).

Schema per steering §9:
  rooms(id, type, capacity, price_per_night, active, location)
  bookings(id, room_id, guest_name, phone, check_in, check_out, guests, status, created_at)

`id` on bookings is a short, speakable 4-6 digit code (not a UUID).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, String, ForeignKey, create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(String, nullable=False, index=True)  # e.g. "Srisailam"
    type = Column(String, nullable=False)                  # "AC" | "Non-AC"
    capacity = Column(Integer, nullable=False, default=1)  # rooms of this type
    price_per_night = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Room {self.location} {self.type} x{self.capacity} @{self.price_per_night}>"


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(String, primary_key=True)  # short speakable code, e.g. "4821"
    location = Column(String, nullable=False, index=True)
    room_type = Column(String, nullable=False)
    guest_name = Column(String, nullable=False)
    phone = Column(String, nullable=False, index=True)
    check_in = Column(Date, nullable=False, index=True)
    check_out = Column(Date, nullable=False)
    guests = Column(Integer, nullable=False, default=1)
    num_rooms = Column(Integer, nullable=False, default=1)
    price_total = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="confirmed")  # confirmed|cancelled
    created_at = Column(DateTime, nullable=False,
                        default=lambda: datetime.now(timezone.utc))


# --- Engine / session factory ---
_engine = None
_Session = None


def init_db(db_path: str):
    """Create the engine + tables. Idempotent."""
    global _engine, _Session
    _engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(_engine)
    _Session = sessionmaker(bind=_engine, future=True, expire_on_commit=False)
    return _engine


def get_session():
    if _Session is None:
        raise RuntimeError("DB not initialised — call init_db() first.")
    return _Session()
