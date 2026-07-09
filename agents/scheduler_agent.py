"""
Scheduler Agent — Sprint 3.

Real implementation, combining two independently-tested concerns per PRD
Section 12:
  1. Geographic clustering (agents/geo_clustering.py) — assign activities
     to `trip_request.days` day-buckets by lat/long proximity.
  2. Time-window scheduling (agents/day_scheduler.py) — order each day's
     activities respecting opening_hours, using a category-based duration
     heuristic, with a concrete "unreasonable zigzag" threshold (1.5x the
     geographically optimal path length) that reorders for geography when
     it can do so without breaking opening-hours feasibility.

Itinerary status is "partial" (with explanatory notes) if any activity
had to be dropped from a day for not fitting its opening-hours window, or
if a day's route stayed zigzagged because reordering would have broken
opening hours; "failed" only if there's nothing to schedule at all.
"""
from __future__ import annotations

from models import Activity, TripRequest, Itinerary
from agents.geo_clustering import cluster_by_day
from agents.day_scheduler import schedule_day


def schedule(trip_request: TripRequest, activities: list[Activity]) -> Itinerary:
    if not activities:
        return Itinerary(
            trip_request_id=trip_request.id,
            days=[{"day_number": i + 1, "activities": []} for i in range(trip_request.days)],
            status="failed",
            notes="No activities available to schedule.",
        )

    clusters = cluster_by_day(activities, trip_request.days)

    days = []
    all_notes = []
    for i, day_activities in enumerate(clusters):
        day_schedule, notes = schedule_day(day_activities)
        days.append({"day_number": i + 1, "activities": day_schedule})
        all_notes.extend(f"Day {i + 1}: {note}" for note in notes)

    status = "partial" if all_notes else "complete"

    return Itinerary(
        trip_request_id=trip_request.id,
        days=days,
        status=status,
        notes=" ".join(all_notes),
    )
