"""
Persistent booking tracker — stores all bookings in a local JSON file.
"""

import json
import os
from datetime import datetime
from pathlib import Path

BOOKINGS_FILE = Path(__file__).parent / "bookings.json"


def _load() -> list[dict]:
    if BOOKINGS_FILE.exists():
        return json.loads(BOOKINGS_FILE.read_text())
    return []


def _save(bookings: list[dict]):
    BOOKINGS_FILE.write_text(json.dumps(bookings, indent=2))


def add_booking(service: str, booking_id: str | int, details: str,
                client_name: str = "", client_email: str = "") -> dict:
    """Record a new booking."""
    bookings = _load()
    entry = {
        "id": len(bookings) + 1,
        "service": service,
        "booking_id": str(booking_id),
        "client_name": client_name,
        "client_email": client_email,
        "details": details,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
    }
    bookings.append(entry)
    _save(bookings)
    return entry


def cancel_booking(local_id: int) -> dict | None:
    """Mark a booking as cancelled by local ID."""
    bookings = _load()
    for b in bookings:
        if b["id"] == local_id:
            b["status"] = "cancelled"
            _save(bookings)
            return b
    return None


def get_all_bookings(include_cancelled: bool = False) -> list[dict]:
    """Get all bookings, optionally including cancelled ones."""
    bookings = _load()
    if include_cancelled:
        return bookings
    return [b for b in bookings if b["status"] == "confirmed"]


def get_booking(local_id: int) -> dict | None:
    bookings = _load()
    for b in bookings:
        if b["id"] == local_id:
            return b
    return None


def get_summary() -> str:
    """Human-readable summary of active bookings."""
    active = get_all_bookings(include_cancelled=False)
    if not active:
        return "No active bookings."
    lines = []
    for b in active:
        client = f"{b.get('client_name', 'Unknown')} ({b.get('client_email', 'no email')})"
        lines.append(f"#{b['id']} [{b['service']}] Client: {client} — {b['details']} (API ID: {b['booking_id']})")
    return "\n".join(lines)
