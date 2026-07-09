"""
Research Agent — Sprint 2.

Real implementation: queries SerpAPI's Local Results across several
category searches to get real destination/activity data, then normalizes
results into the Activity schema via OpenAI (category + opening-hours
only — no invented coordinates, no cost estimation).

Falls back to the Sprint 1 stub (3 hardcoded activities, tagged with a
distinct source so it's traceable in output) if SERPAPI_API_KEY /
OPENAI_API_KEY aren't set, or if the live pipeline errors for any reason.
This keeps the CLI and golden-scenario tests runnable without live API
keys, and means adding keys later requires zero code changes.
"""
from __future__ import annotations
import os
import sys

from models import Activity
from agents.search_providers import SerpApiLocalSearch, SearchProviderError
from agents.llm_normalizer import normalize_places

CATEGORY_QUERIES = [
    "top attractions",
    "museums",
    "parks",
    "notable restaurants",
    "guided tours",
]


def _stub_activities(trip_request, reason: str) -> list[Activity]:
    print(f"[research_agent] Falling back to stub data: {reason}", file=sys.stderr)
    stub_activities = [
        {
            "name": "City Walking Tour",
            "category": "sightseeing",
            "lat": 0.0,
            "long": 0.0,
            "opening_hours": "09:00-17:00",
            "source": "stub:fallback-no-api-keys",
        },
        {
            "name": "Local History Museum",
            "category": "museum",
            "lat": 0.01,
            "long": 0.01,
            "opening_hours": "10:00-18:00",
            "source": "stub:fallback-no-api-keys",
        },
        {
            "name": "Riverside Park Picnic",
            "category": "outdoor",
            "lat": 0.02,
            "long": -0.01,
            "opening_hours": "06:00-20:00",
            "source": "stub:fallback-no-api-keys",
        },
    ]
    return [Activity(trip_request_id=trip_request.id, **a) for a in stub_activities]


def _dedupe(raw_places: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for p in raw_places:
        key = p.get("place_id") or p.get("title")
        if key and key not in seen:
            seen.add(key)
            deduped.append(p)
    return deduped


def research_activities(trip_request) -> list[Activity]:
    """
    Returns a candidate list of Activity objects for the trip's
    destination — real data if SERPAPI_API_KEY and GROQ_API_KEY are
    set, otherwise the Sprint 1 stub.
    """
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    if not serpapi_key or not groq_key:
        return _stub_activities(
            trip_request,
            reason="SERPAPI_API_KEY and/or GROQ_API_KEY not set in environment.",
        )

    try:
        search = SerpApiLocalSearch(api_key=serpapi_key)
        raw_places: list[dict] = []
        for category_query in CATEGORY_QUERIES:
            query = f"{category_query} in {trip_request.destination}"
            raw_places.extend(search.search(query))

        raw_places = _dedupe(raw_places)
        if not raw_places:
            return _stub_activities(trip_request, reason="SerpAPI returned no results.")

        normalized = normalize_places(raw_places, api_key=groq_key)
    except (SearchProviderError, RuntimeError) as e:
        return _stub_activities(trip_request, reason=f"Research pipeline error: {e}")
    except Exception as e:  # noqa: BLE001 - last-resort guard so the CLI never crashes here
        return _stub_activities(trip_request, reason=f"Unexpected research error: {e}")

    if not normalized:
        return _stub_activities(trip_request, reason="No activities could be normalized.")

    return [Activity(trip_request_id=trip_request.id, **a) for a in normalized]