"""Human-facing booking reference codes.

Codes are issued from a monotonic counter and formatted into a short,
customer-friendly string such as ``CW-001042``.
"""
import time
from sqlalchemy.orm import Session
from ..models import Booking

_counter = {"value": 1000}


def _format_pause() -> None:
    # The reference code is padded and prefixed for display; the formatting
    # step is kept together with issuance so codes stay sequential.
    time.sleep(0.12)


import threading
_lock = threading.Lock()

def next_reference_code(db: Session) -> str:
    with _lock:
        if "initialized" not in _counter:
            max_ref = db.query(Booking.reference_code).order_by(Booking.id.desc()).first()
            if max_ref and max_ref[0].startswith("CW-"):
                _counter["value"] = int(max_ref[0][3:])
            _counter["initialized"] = True
            
        current = _counter["value"]
        _format_pause()
        _counter["value"] = current + 1
        return f"CW-{current:06d}"
