"""
ADK Pipeline — Sprint 2 wiring.

PRD Section 14 specifies orchestration via ADK (Agent Development Kit),
with a Research <-> Budget feedback loop (max 2 rounds, Section 11) feeding
into the Scheduler Agent. This is still wired as a plain Python function so
the pipeline is demoable via CLI without pulling in the ADK dependency yet.
The Budget Agent's feedback loop (Section 11) is now real; the Scheduler
Agent remains a Sprint 1 stub (real clustering/opening-hours logic is
Sprint 3). Swapping this for a real ADK pipeline is a later task; the
function boundaries below are deliberately kept 1:1 with the future ADK
agent nodes so that swap is mechanical.
"""
from models import TripRequest, Itinerary
from agents.research_agent import research_activities
from agents.budget_agent import filter_by_budget
from agents.scheduler_agent import schedule


def run_pipeline(trip_request: TripRequest) -> Itinerary:
    """Runs the full pipeline: research -> budget filter -> schedule."""
    candidates = research_activities(trip_request)
    affordable, insufficient, budget_notes = filter_by_budget(trip_request, candidates)
    itinerary = schedule(trip_request, affordable)

    if insufficient and itinerary.status == "complete":
        itinerary.status = "partial"
    if budget_notes:
        itinerary.notes = f"{itinerary.notes} {budget_notes}".strip()

    return itinerary