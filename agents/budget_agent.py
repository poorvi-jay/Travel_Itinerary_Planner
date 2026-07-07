"""
Budget Agent — Sprint 1 STUB.

Real version (Sprint 2) will estimate cost per activity and filter the
candidate list to fit the stated budget (PRD 7.2), plus participate in the
research/budget feedback loop (PRD Section 11) when too much gets filtered
out. For the walking skeleton, this is a pure passthrough: no filtering,
no feedback loop, just proving the pipeline wiring.
"""
from models import Activity, TripRequest


def filter_by_budget(trip_request: TripRequest, activities: list[Activity]) -> list[Activity]:
    """
    Sprint 1 STUB: passthrough, returns all activities unfiltered.
    Real implementation (Sprint 2) must:
      - sum estimated costs and drop/flag activities that blow the budget
      - implement the feedback loop rules from PRD Section 11:
          max 2 retry rounds; round 1 drops most expensive category,
          round 2 raises effective ceiling by 15%; stop and return partial
          itinerary if round 2 still yields < N (default 3) viable
          activities per day.
    """
    return activities