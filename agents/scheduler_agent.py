"""
Scheduler Agent — Sprint 1 STUB.

Real version (Sprint 3) splits into two independently-built/tested
concerns per PRD Section 12:
  1. Geographic clustering (group same-day activities by proximity)
  2. Time-window constraint satisfaction (order within a day respecting
     opening/closing hours)
For the walking skeleton, this just dumps activities round-robin into
Day 1 / Day 2 / ... with no clustering and no time-window logic, purely
to prove the pipeline produces a day-by-day structure end-to-end.
"""
from models import Activity, TripRequest, Itinerary, DayPlan


def schedule(trip_request: TripRequest, activities: list[Activity]) -> Itinerary:
    """
    Sprint 1 STUB: round-robins activities across `trip_request.days`,
    with an arbitrary fixed scheduled_time. No clustering, no
    opening-hours checks.

    Real implementation (Sprint 3) must:
      - cluster by lat/long per day (nearest-neighbor or basic clustering)
      - order within each day respecting opening_hours (filter/sort)
      - combine the two only after each is independently tested
      - define and enforce a concrete "unreasonable zigzag" threshold
    """
    days = [DayPlan(day_number=i + 1, activities=[]) for i in range(trip_request.days)]

    for idx, activity in enumerate(activities):
        day = days[idx % trip_request.days]
        day.activities.append({
            "activity_id": activity.id,
            "scheduled_time": "10:00",  # placeholder, no real time logic yet
        })

    status = "complete" if activities else "failed"
    notes = "" if activities else "No activities available to schedule (stub)."

    return Itinerary(
        trip_request_id=trip_request.id,
        days=[{"day_number": d.day_number, "activities": d.activities} for d in days],
        status=status,
        notes=notes,
    )