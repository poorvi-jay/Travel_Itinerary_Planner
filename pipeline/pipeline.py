"""
Pipeline orchestration — migrated to Google ADK.

PRD Section 14 specifies orchestration via ADK (Agent Development Kit).
This runs the three stages (Research -> Budget -> Scheduler) as a real
ADK `SequentialAgent` of `BaseAgent` wrappers (agents/adk_agents.py),
communicating through ADK session state rather than plain function
chaining/return values. `run_pipeline` stays a synchronous function with
the same signature as before the migration (`main.py` and the
golden-scenario tests are unchanged) — it drives ADK's async Runner via
`asyncio.run`.

Note on `google.adk.agents.SequentialAgent`: as of google-adk 2.4.0 it is
deprecated in favor of a newer `Workflow`/`Node` graph DSL
(`google.adk.workflow`), but is not yet removed and works correctly
(verified directly against this ADK version before writing this file).
Migrating to `Workflow` is a reasonable future follow-up, not done here
to stay within this migration's scope.

The Research<->Budget feedback loop (PRD Section 11) is *not* a
cross-agent ADK loop here: it stays exactly as it was pre-migration,
self-contained inside the Budget stage's call to `filter_by_budget`,
which re-filters the same single Research candidate list across its 3
internal rounds rather than calling back into Research. PRD Section 11's
literal "research -> budget -> research -> budget -> stop" framing
implies a bidirectional loop that was never actually built this way, in
Sprint 2 or here — ADK's `LoopAgent` could support a true bidirectional
version, but building that is a behavior change to the feedback loop's
retry semantics, which this migration deliberately does not make (see
Non-goals).
"""
from __future__ import annotations
import asyncio
import uuid

from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from models import TripRequest, Itinerary
from agents.adk_agents import ResearchADKAgent, BudgetADKAgent, SchedulerADKAgent

APP_NAME = "travel_itinerary_planner"


def _build_pipeline_agent() -> SequentialAgent:
    return SequentialAgent(
        name="travel_pipeline",
        sub_agents=[
            ResearchADKAgent(name="research_agent"),
            BudgetADKAgent(name="budget_agent"),
            SchedulerADKAgent(name="scheduler_agent"),
        ],
    )


async def _run_pipeline_async(trip_request: TripRequest) -> Itinerary:
    session_service = InMemorySessionService()
    user_id = "cli"
    session_id = f"{trip_request.id}-{uuid.uuid4().hex[:8]}"

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state={"trip_request": trip_request},
    )

    runner = Runner(agent=_build_pipeline_agent(), app_name=APP_NAME, session_service=session_service)
    trigger_message = types.Content(role="user", parts=[types.Part(text="run")])

    async for _event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=trigger_message
    ):
        pass  # stages communicate via session state, not event content

    final_session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    return final_session.state["itinerary"]


def run_pipeline(trip_request: TripRequest) -> Itinerary:
    """Runs the full pipeline: research -> budget filter -> schedule, via ADK."""
    return asyncio.run(_run_pipeline_async(trip_request))
