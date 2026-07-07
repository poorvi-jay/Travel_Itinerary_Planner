"""
CLI entrypoint — Sprint 1 walking skeleton.

Usage:
    python main.py "Paris" 3 300
    python main.py --destination "Paris" --days 3 --budget 300
"""
import argparse
import json
import sys

from models import TripRequest
from pipeline.pipeline import run_pipeline


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Travel Itinerary Planner (Sprint 1 stub pipeline)")
    parser.add_argument("destination", nargs="?", help="Trip destination, e.g. 'Paris'")
    parser.add_argument("days", nargs="?", type=int, help="Number of days")
    parser.add_argument("budget", nargs="?", type=float, help="Total budget")
    parser.add_argument("--destination", dest="destination_flag")
    parser.add_argument("--days", dest="days_flag", type=int)
    parser.add_argument("--budget", dest="budget_flag", type=float)
    parser.add_argument("--json", action="store_true", help="Print raw JSON only")
    return parser


def resolve_args(args) -> tuple[str, int, float]:
    destination = args.destination_flag or args.destination
    days = args.days_flag or args.days
    budget = args.budget_flag or args.budget
    if not destination or not days or budget is None:
        print("Error: destination, days, and budget are all required.", file=sys.stderr)
        sys.exit(1)
    return destination, days, budget


def print_itinerary(trip_request: TripRequest, itinerary) -> None:
    print(f"\nTrip to {trip_request.destination} — {trip_request.days} day(s), budget ${trip_request.budget:.2f}")
    print(f"Status: {itinerary.status}")
    if itinerary.notes:
        print(f"Notes: {itinerary.notes}")
    for day in itinerary.days:
        print(f"\n  Day {day['day_number']}:")
        if not day["activities"]:
            print("    (no activities scheduled)")
        for act in day["activities"]:
            print(f"    - [{act['scheduled_time']}] activity_id={act['activity_id']}")


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    destination, days, budget = resolve_args(args)

    trip_request = TripRequest(destination=destination, days=days, budget=budget)
    itinerary = run_pipeline(trip_request)

    if args.json:
        print(json.dumps(itinerary.to_dict(), indent=2))
    else:
        print_itinerary(trip_request, itinerary)


if __name__ == "__main__":
    main()