"""
ADK Pipeline — Sprint 1 STUB wiring.

PRD Section 14 specifies orchestration via ADK (Agent Development Kit),
with a Research <-> Budget feedback loop (max 2 rounds, Section 11) feeding
into the Scheduler Agent. For Sprint 1 this is wired as a plain Python
function so the walking skeleton is demoable via CLI without pulling in
the ADK dependency yet. The feedback loop is NOT implemented here — budget
agent is a passthrough stub, so there's nothing to loop on yet. Swapping
this for a real ADK pipeline is a Sprint 2+ task; the function boundaries
below are deliberately kept 1:1 with the future ADK agent nodes so that
swap is mechanical.
"""
from models import TripRequest, Itinerary
from agents.research_agent import research_activities
from agents.budget_agent import filter_by_budget
from agents.scheduler_agent import schedule


def run_pipeline(trip_request: TripRequest) -> Itinerary:
    """Runs the full stub pipeline: research -> budget filter -> schedule."""
    candidates = research_activities(trip_request)
    affordable = filter_by_budget(trip_request, candidates)
    itinerary = schedule(trip_request, affordable)
    return itinerary