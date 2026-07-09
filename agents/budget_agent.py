"""
Budget Agent — Sprint 2.

Real implementation: estimates a per-activity cost via Groq (through
agents/llm_cost_estimator.py), then greedily selects the largest
cheapest-first subset of activities that fits the trip's total budget, and
runs the PRD Section 11 feedback loop when that isn't enough to leave at
least MIN_VIABLE_PER_DAY activities per day:

  Round 0: fit within trip_request.budget as-is.
  Round 1: if still short, drop the single most expensive category from
           the candidate pool entirely and retry at the same budget.
  Round 2: if still short, raise the effective budget ceiling by 15% and
           retry against the round-1 (category-reduced) pool.

If round 2 is still short, stop and return the best of all three attempts
(by activity count) — the caller (pipeline) is responsible for marking the
resulting itinerary "partial" using the `insufficient` flag.

Falls back to a fixed per-category cost table if GROQ_API_KEY isn't set or
the LLM cost-estimation call fails for any reason, so the CLI never breaks.
"""
from __future__ import annotations

import os
import sys

from models import Activity, TripRequest
from agents.llm_cost_estimator import estimate_costs

MIN_VIABLE_PER_DAY = 3
ROUND2_CEILING_MULTIPLIER = 1.15

# Fallback used only if the Groq cost-estimation call is unavailable/fails.
FALLBACK_COST_BY_CATEGORY = {
    "sightseeing": 15.0,
    "museum": 20.0,
    "outdoor": 0.0,
    "dining": 30.0,
    "tour": 50.0,
    "nightlife": 40.0,
    "shopping": 10.0,
    "entertainment": 25.0,
    "other": 15.0,
}


def _get_costs(trip_request: TripRequest, activities: list[Activity], api_key: str | None) -> dict[str, float]:
    if api_key:
        try:
            return estimate_costs(activities, trip_request.destination, api_key)
        except Exception as e:  # noqa: BLE001 - fall back rather than break the CLI
            print(f"[budget_agent] Falling back to heuristic costs: {e}", file=sys.stderr)
    else:
        print("[budget_agent] GROQ_API_KEY not set; using heuristic costs.", file=sys.stderr)

    return {
        a.id: FALLBACK_COST_BY_CATEGORY.get(a.category, FALLBACK_COST_BY_CATEGORY["other"])
        for a in activities
    }


def _select_within_budget(activities: list[Activity], costs: dict[str, float], budget: float) -> list[Activity]:
    """Greedy cheapest-first: maximizes activity COUNT that fits the budget."""
    ordered = sorted(activities, key=lambda a: costs.get(a.id, 0.0))
    selected = []
    spent = 0.0
    for a in ordered:
        cost = costs.get(a.id, 0.0)
        if spent + cost <= budget:
            selected.append(a)
            spent += cost
    return selected


def _drop_most_expensive_category(activities: list[Activity], costs: dict[str, float]) -> list[Activity]:
    if not activities:
        return activities
    by_category: dict[str, list[float]] = {}
    for a in activities:
        by_category.setdefault(a.category, []).append(costs.get(a.id, 0.0))
    avg_cost_by_category = {cat: sum(vals) / len(vals) for cat, vals in by_category.items()}
    most_expensive_category = max(avg_cost_by_category, key=avg_cost_by_category.get)
    return [a for a in activities if a.category != most_expensive_category]


def filter_by_budget(
    trip_request: TripRequest, activities: list[Activity], api_key: str | None = None
) -> tuple[list[Activity], bool, str]:
    """
    Returns (selected_activities, insufficient, notes).

    `insufficient` is True if even after both feedback-loop rounds fewer
    than MIN_VIABLE_PER_DAY * trip_request.days activities are affordable —
    the caller should mark the resulting itinerary "partial".
    """
    api_key = api_key or os.getenv("GROQ_API_KEY")

    if not activities:
        return [], True, "No candidate activities to filter."

    costs = _get_costs(trip_request, activities, api_key)
    target = MIN_VIABLE_PER_DAY * trip_request.days

    # Round 0: as-is.
    best = _select_within_budget(activities, costs, trip_request.budget)
    if len(best) >= target:
        return best, False, ""

    # Round 1: drop the most expensive category, retry at the same budget.
    reduced_pool = _drop_most_expensive_category(activities, costs)
    round1 = _select_within_budget(reduced_pool, costs, trip_request.budget)
    if len(round1) > len(best):
        best = round1
    if len(round1) >= target:
        return round1, False, "Dropped the most expensive category to fit the budget."

    # Round 2: raise the ceiling by 15%, retry against the reduced pool.
    raised_budget = trip_request.budget * ROUND2_CEILING_MULTIPLIER
    round2 = _select_within_budget(reduced_pool, costs, raised_budget)
    if len(round2) > len(best):
        best = round2
    if len(round2) >= target:
        return round2, False, (
            "Dropped the most expensive category and raised the effective "
            f"budget by 15% (to ${raised_budget:.2f}) to fit enough activities."
        )

    notes = (
        f"Budget feedback loop exhausted: only {len(best)} of a target "
        f"{target} activities ({MIN_VIABLE_PER_DAY}/day) fit even after dropping "
        "the priciest category and raising the budget by 15%."
    )
    return best, True, notes
