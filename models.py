"""
Data model for the Travel Itinerary Planner.
Mirrors PRD Section 15 (TripRequest, Activity, Itinerary).
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import uuid


def _new_id() -> str:
    return str(uuid.uuid4())[:8]


@dataclass
class TripRequest:
    destination: str
    days: int
    budget: float
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Activity:
    name: str
    category: str
    estimated_cost: float
    lat: float
    long: float
    opening_hours: str  # e.g. "09:00-17:00"
    source: str
    trip_request_id: str
    id: str = field(default_factory=_new_id)


@dataclass
class DayPlan:
    day_number: int
    activities: list  # list of {"activity_id": str, "scheduled_time": "HH:MM"}


@dataclass
class Itinerary:
    trip_request_id: str
    days: list  # list[DayPlan]
    status: str = "complete"  # complete | partial | failed
    notes: str = ""
    id: str = field(default_factory=_new_id)

    def to_dict(self):
        d = asdict(self)
        return d