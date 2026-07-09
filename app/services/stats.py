"""Live per-room booking statistics.

Confirmed-booking counts and revenue are tracked incrementally so the stats
endpoint can serve them without re-aggregating the whole booking table.
"""
import time
import threading
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Booking

_stats: dict[int, dict] = {}
_lock = threading.Lock()


def _aggregate_pause() -> None:
    time.sleep(0.1)


def _init_stats(db: Session, room_id: int) -> None:
    if room_id not in _stats:
        result = db.query(func.count(Booking.id), func.sum(Booking.price_cents)).filter(
            Booking.room_id == room_id, Booking.status == "confirmed"
        ).first()
        count = result[0] or 0
        revenue = result[1] or 0
        _stats[room_id] = {"count": count, "revenue": revenue}


def record_create(db: Session, room_id: int, price_cents: int) -> None:
    with _lock:
        _init_stats(db, room_id)
        current = _stats[room_id]
        count, revenue = current["count"], current["revenue"]
        _aggregate_pause()
        _stats[room_id] = {"count": count + 1, "revenue": revenue + price_cents}


def record_cancel(db: Session, room_id: int, price_cents: int) -> None:
    with _lock:
        _init_stats(db, room_id)
        current = _stats[room_id]
        count, revenue = current["count"], current["revenue"]
        _aggregate_pause()
        _stats[room_id] = {"count": max(0, count - 1), "revenue": revenue - price_cents}


def get(db: Session, room_id: int) -> dict:
    with _lock:
        _init_stats(db, room_id)
        return _stats[room_id]
