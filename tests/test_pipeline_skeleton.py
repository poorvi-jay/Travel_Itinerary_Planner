"""
Sprint 1 walking-skeleton test.

Checks that every golden scenario (PRD Section 17) makes it through the
full stub pipeline (research -> budget -> scheduler) and produces a
well-formed Itinerary: right number of days, non-crashing, valid status.

This intentionally does NOT check budget adherence, opening-hours
correctness, or geographic sensibility yet — those checks get real
teeth once the corresponding agents stop being stubs (Sprint 2/3).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import TripRequest
from pipeline.pipeline import run_pipeline
from tests.golden_scenarios import GOLDEN_SCENARIOS


def run_all():
    failures = []
    for scenario in GOLDEN_SCENARIOS:
        trip_request = TripRequest(
            destination=scenario.destination,
            days=scenario.days,
            budget=scenario.budget,
        )
        try:
            itinerary = run_pipeline(trip_request)
        except Exception as e:
            failures.append(f"[{scenario.name}] pipeline raised: {e}")
            continue

        if len(itinerary.days) != scenario.days:
            failures.append(
                f"[{scenario.name}] expected {scenario.days} days, got {len(itinerary.days)}"
            )
        if itinerary.status not in ("complete", "partial", "failed"):
            failures.append(f"[{scenario.name}] invalid status: {itinerary.status}")

        print(f"OK  [{scenario.name}] {scenario.destination} -> status={itinerary.status}, "
              f"days={len(itinerary.days)}, "
              f"total_activities={sum(len(d['activities']) for d in itinerary.days)}")

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    else:
        print(f"All {len(GOLDEN_SCENARIOS)} golden scenarios passed the walking-skeleton check.")


if __name__ == "__main__":
    run_all()