"""
Research Agent — Sprint 1 STUB.

Real version (Sprint 2) will use LangChain + a search tool to find real
destination/activity data. For the walking skeleton, this returns a fixed
list of 3 hardcoded activities regardless of destination, so the pipeline
can be wired end-to-end before real research logic exists.
"""
from models import Activity


def research_activities(trip_request) -> list[Activity]:
    """
    Sprint 1 STUB: ignores destination/budget entirely, returns 3 fixed
    candidate activities. Real implementation (Sprint 2) must:
      - search for real activities near `trip_request.destination`
      - return a candidate list broader than needed (so budget agent has
        room to filter, per PRD 7.1)
      - attach a real `source` per activity (no un-sourced activities,
        per PRD Risk table Section 16)
    """
    stub_activities = [
        {
            "name": "City Walking Tour",
            "category": "sightseeing",
            "estimated_cost": 20.0,
            "lat": 0.0,
            "long": 0.0,
            "opening_hours": "09:00-17:00",
            "source": "stub:hardcoded",
        },
        {
            "name": "Local History Museum",
            "category": "museum",
            "estimated_cost": 15.0,
            "lat": 0.01,
            "long": 0.01,
            "opening_hours": "10:00-18:00",
            "source": "stub:hardcoded",
        },
        {
            "name": "Riverside Park Picnic",
            "category": "outdoor",
            "estimated_cost": 5.0,
            "lat": 0.02,
            "long": -0.01,
            "opening_hours": "06:00-20:00",
            "source": "stub:hardcoded",
        },
    ]

    return [
        Activity(trip_request_id=trip_request.id, **a)
        for a in stub_activities
    ]