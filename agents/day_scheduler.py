"""
Day Scheduler — Sprint 3.

Orders a single day's activities respecting opening_hours (PRD Section
12), using a category-based duration heuristic since no real duration
data exists anywhere in the pipeline. Kept independent of geographic
clustering (agents/geo_clustering.py) so each concern is testable on its
own before the Scheduler Agent combines them.

Also enforces a concrete "unreasonable zigzag" threshold: if the
time-window order's total path length is more than ZIGZAG_THRESHOLD times
the geographically-nearest-neighbor order's path length, it switches to
the geographic order instead — but only if that doesn't drop any activity
that the time-window order had kept. Opening-hours feasibility always
wins over route shape.
"""
from __future__ import annotations
from datetime import time, datetime

from models import Activity

ZIGZAG_THRESHOLD = 1.5
DAY_START = time(8, 0)

CATEGORY_DURATION_HOURS = {
    "sightseeing": 1.5,
    "museum": 2.5,
    "outdoor": 1.5,
    "dining": 1.0,
    "tour": 3.0,
    "nightlife": 2.0,
    "shopping": 1.0,
    "entertainment": 2.0,
    "other": 1.5,
}


def _parse_window(opening_hours: str) -> tuple[time, time]:
    """Returns (open, close); defaults to a fully-open window if the
    string can't be parsed, rather than hard-failing on messy data."""
    try:
        cleaned = opening_hours.removeprefix("estimated:").strip()
        start_str, end_str = cleaned.split("-")
        start = datetime.strptime(start_str.strip(), "%H:%M").time()
        end = datetime.strptime(end_str.strip(), "%H:%M").time()
        return start, end
    except Exception:
        return time(0, 0), time(23, 59)


def _add_hours(start: time, hours: float) -> time:
    total_minutes = start.hour * 60 + start.minute + round(hours * 60)
    total_minutes = min(total_minutes, 23 * 60 + 59)
    return time(total_minutes // 60, total_minutes % 60)


def _assign_times_in_sequence(
    ordered: list[Activity], day_start: time = DAY_START
) -> tuple[list[tuple[Activity, str]], list[Activity]]:
    """Walks the given order, assigning the earliest feasible start time to
    each activity; drops any activity whose duration can't fit inside its
    opening-hours window given how the day has filled up so far."""
    kept: list[tuple[Activity, str]] = []
    dropped: list[Activity] = []
    current = day_start

    for activity in ordered:
        window_start, window_close = _parse_window(activity.opening_hours)
        duration = CATEGORY_DURATION_HOURS.get(activity.category, CATEGORY_DURATION_HOURS["other"])
        start = max(current, window_start)
        end = _add_hours(start, duration)
        if end > window_close:
            dropped.append(activity)
            continue
        kept.append((activity, start.strftime("%H:%M")))
        current = end

    return kept, dropped


def _nearest_neighbor_order(activities: list[Activity]) -> list[Activity]:
    remaining = list(activities)
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1]
        nearest = min(remaining, key=lambda a: (a.lat - last.lat) ** 2 + (a.long - last.long) ** 2)
        remaining.remove(nearest)
        ordered.append(nearest)
    return ordered


def _path_distance(ordered: list[Activity]) -> float:
    if len(ordered) < 2:
        return 0.0
    return sum(
        ((a.lat - b.lat) ** 2 + (a.long - b.long) ** 2) ** 0.5
        for a, b in zip(ordered, ordered[1:])
    )


def schedule_day(activities: list[Activity]) -> tuple[list[dict], list[str]]:
    """
    Returns (schedule, notes) where schedule is a list of
    {"activity_id": str, "scheduled_time": "HH:MM"} in order, and notes
    describes anything dropped or any unresolved zigzag.
    """
    if not activities:
        return [], []

    time_sorted = sorted(activities, key=lambda a: _parse_window(a.opening_hours)[0])
    kept, dropped = _assign_times_in_sequence(time_sorted)
    notes = [f"dropped '{a.name}' — does not fit its opening hours." for a in dropped]

    kept_activities = [a for a, _ in kept]
    if len(kept_activities) >= 3:
        geo_order = _nearest_neighbor_order(kept_activities)
        time_ordered_dist = _path_distance(kept_activities)
        geo_dist = _path_distance(geo_order)
        ratio = 1.0 if geo_dist == 0 else time_ordered_dist / geo_dist

        if ratio > ZIGZAG_THRESHOLD:
            geo_kept, geo_dropped = _assign_times_in_sequence(geo_order)
            if len(geo_kept) == len(kept):
                kept = geo_kept
            else:
                notes.append(
                    f"route is zigzagged ({ratio:.1f}x the geographically optimal path) "
                    "but reordering would break opening-hours constraints, so the "
                    "time-window order was kept."
                )

    schedule = [{"activity_id": a.id, "scheduled_time": t} for a, t in kept]
    return schedule, notes
