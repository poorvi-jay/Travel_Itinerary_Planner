"""
Research Agent — Sprint 2, orchestration migrated to LangChain.

Real implementation: runs a LangChain tool-calling agent (Groq-backed,
via langchain-groq) that calls the SerpAPI search tool
(agents/search_providers.make_search_tool) across several category
searches to get real destination/activity data, then normalizes results
into the Activity schema via Groq (category + opening-hours only — no
invented coordinates, no cost estimation).

The LangChain agent only orchestrates tool calls — candidate places are
read back out of the tool-call results (ToolMessage contents), never out
of the agent's own generated text, so it has no path to fabricate places
(PRD Section 16: "no activity without a source").

Falls back to the Sprint 1 stub (3 hardcoded activities, tagged with a
distinct source so it's traceable in output) if SERPAPI_API_KEY /
GROQ_API_KEY aren't set, or if a *technical* error occurs (network, auth,
LLM failure) — that keeps the CLI and golden-scenario tests runnable
without live API keys, and means adding keys later requires zero code
changes.

PRD Section 13 draws a line this file has to respect: a technical hiccup
may fall back to demo data, but an *unrecognized/no-data destination* may
not — that would be exactly the "hallucinated itinerary for a place with
no real data" the PRD calls out. So when keys ARE configured and a real
search genuinely turns up nothing, `research_activities` returns an
*empty* candidate list plus a clear, destination-specific explanation
instead of the generic stub — never both a real search attempt and fake
results. It also flags (PRD Section 13's other named scenario) when a
destination returns real but too few candidates for the requested trip
length, since that's a different problem (destination coverage) than
budget, and deserves a different message than "budget too tight."
"""
from __future__ import annotations
import json
import os
import sys

from models import Activity
from agents.search_providers import SerpApiLocalSearch, SearchProviderError, make_search_tool
from agents.llm_normalizer import normalize_places, GROQ_MODEL
from agents.budget_agent import MIN_VIABLE_PER_DAY

CATEGORY_QUERIES = [
    "top attractions",
    "museums",
    "parks",
    "notable restaurants",
    "guided tours",
]

RESEARCH_SYSTEM_PROMPT = (
    "You are a travel research assistant gathering real candidate "
    "activities for a trip, broader than what will ultimately be used, "
    "so a later budget-filtering step has room to choose from. Call the "
    "search_local_places tool once for each of these categories against "
    "the given destination: "
    + ", ".join(f'"{q}"' for q in CATEGORY_QUERIES)
    + ". Do not skip categories, and do not invent, summarize, or "
    "describe places yourself — only call the tool and let its results "
    "speak for themselves."
)


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


def _no_real_data(trip_request, reason: str) -> tuple[list[Activity], str]:
    """
    PRD Section 13: "Unfamiliar/unrecognized destination -> Clear error
    message; no hallucinated itinerary for a place with no real data."
    Called only when keys were configured and a real search was
    attempted — deliberately does NOT fall back to the generic stub,
    since that would produce exactly the fabricated-looking itinerary
    the PRD warns against.
    """
    print(f"[research_agent] No real activity data found (not using stub): {reason}", file=sys.stderr)
    note = (
        f'We couldn\'t find real activity data for "{trip_request.destination}". '
        "It may be unrecognized, misspelled, or not well covered by our search "
        "source — please check the spelling or try a nearby larger destination."
    )
    return [], note


def _day_count_feasibility_note(trip_request, activities: list[Activity]) -> str:
    """
    PRD Section 13: "Day count mismatched to destination size ... Flag
    explicitly ... decided deliberately, not left to fall out of
    prompting." v1 chooses to flag rather than pad with nearby/day-trip
    options (the PRD's other allowed choice) — padding would need a
    "search nearby towns" capability this agent doesn't have, and risks
    fabricating filler content, which Section 16 explicitly rules out.

    Uses the Budget Agent's MIN_VIABLE_PER_DAY (Section 11) as the same
    "enough coverage" threshold, applied to raw candidate count before
    any budget filtering — this is about destination content scarcity,
    not budget, so it has to be checked independently of the budget
    feedback loop.
    """
    if not activities:
        return ""  # handled separately by _no_real_data
    target = MIN_VIABLE_PER_DAY * trip_request.days
    if len(activities) >= target:
        return ""
    suggested_days = max(1, len(activities) // MIN_VIABLE_PER_DAY)
    return (
        f"Found only {len(activities)} real candidate activities for "
        f"{trip_request.destination} — not enough to comfortably fill a "
        f"{trip_request.days}-day trip (~{MIN_VIABLE_PER_DAY}/day recommended). "
        f"Consider a shorter trip (around {suggested_days} day(s)) or a larger "
        "nearby destination."
    )


def _dedupe(raw_places: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for p in raw_places:
        key = p.get("place_id") or p.get("title")
        if key and key not in seen:
            seen.add(key)
            deduped.append(p)
    return deduped


def _agent_search(destination: str, serpapi_key: str, groq_key: str) -> list[dict]:
    """
    Runs a LangChain tool-calling agent (Groq-backed) that calls the
    SerpAPI search tool once per category. Candidate places are collected
    from the tool-call results themselves (ToolMessage contents), not
    from the agent's final text — the agent decides *which* searches to
    run, it never gets to originate place data.
    """
    from langchain_core.messages import ToolMessage
    from langchain_groq import ChatGroq
    from langchain.agents import create_agent

    search_client = SerpApiLocalSearch(api_key=serpapi_key)
    search_tool = make_search_tool(search_client)
    llm = ChatGroq(model=GROQ_MODEL, api_key=groq_key, temperature=0)
    agent = create_agent(model=llm, tools=[search_tool], system_prompt=RESEARCH_SYSTEM_PROMPT)

    result = agent.invoke({
        "messages": [(
            "user",
            f"Research candidate activities for a trip to {destination}.",
        )],
    })

    raw_places: list[dict] = []
    for message in result.get("messages", []):
        if not isinstance(message, ToolMessage):
            continue
        try:
            raw_places.extend(json.loads(message.content))
        except (json.JSONDecodeError, TypeError):
            continue
    return raw_places


def research_activities(trip_request) -> tuple[list[Activity], str]:
    """
    Returns (candidate_activities, note).

    `note` is "" in the normal case. It carries a user-facing PRD
    Section 13 explanation in two cases: no real data could be found for
    the destination at all (candidate_activities will be empty — see
    `_no_real_data`), or real data was found but not enough to cover the
    requested trip length (see `_day_count_feasibility_note`). It stays
    "" for the no-keys/technical-fallback stub paths — those are demo
    mode, not a Section 13 error condition.
    """
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    if not serpapi_key or not groq_key:
        return _stub_activities(
            trip_request,
            reason="SERPAPI_API_KEY and/or GROQ_API_KEY not set in environment.",
        ), ""

    try:
        raw_places = _agent_search(trip_request.destination, serpapi_key, groq_key)
        raw_places = _dedupe(raw_places)
        if not raw_places:
            return _no_real_data(trip_request, reason="SerpAPI returned no results.")

        normalized = normalize_places(raw_places, api_key=groq_key)
    except (SearchProviderError, RuntimeError) as e:
        return _stub_activities(trip_request, reason=f"Research pipeline error: {e}"), ""
    except Exception as e:  # noqa: BLE001 - last-resort guard so the CLI never crashes here
        return _stub_activities(trip_request, reason=f"Unexpected research error: {e}"), ""

    if not normalized:
        return _no_real_data(trip_request, reason="No activities could be normalized.")

    activities = [Activity(trip_request_id=trip_request.id, **a) for a in normalized]
    return activities, _day_count_feasibility_note(trip_request, activities)