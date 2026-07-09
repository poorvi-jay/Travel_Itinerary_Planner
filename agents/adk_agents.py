"""
ADK orchestration wrappers.

PRD Section 14 specifies Google ADK for agent orchestration. Each class
here wraps the existing Sprint 2/3 stage logic *unchanged* (no research/
budget/scheduling decision logic changes) so it can run as a real ADK
BaseAgent inside pipeline.py's SequentialAgent, instead of the plain
Python function chain used since Sprint 1.

State flows through `ctx.session.state` (a plain dict on the ADK
Session), written via `Event(actions=EventActions(state_delta=...))` per
ADK's event-sourced state model rather than direct mutation:
  - "trip_request": TripRequest — set by pipeline.py before the run starts
  - "candidates": list[Activity] — written by ResearchADKAgent
  - "research_note": str — written by ResearchADKAgent; a PRD Section 13
    explanation (unrecognized/no-data destination, or too few real
    candidates for the requested trip length) — see research_agent.py
  - "affordable": list[Activity] — written by BudgetADKAgent
  - "budget_insufficient": bool, "budget_notes": str — written by BudgetADKAgent
  - "itinerary": Itinerary — written by SchedulerADKAgent

Note: the budget feedback loop (PRD Section 11) stays entirely inside
BudgetADKAgent's call to `filter_by_budget`, which is self-contained
(it re-filters the same Research candidate list across its 3 rounds; it
does not call back into Research). That mirrors the pre-migration
behavior — see the pipeline.py module docstring for why a true
cross-agent Research<->Budget loop is a deliberate non-goal here.
"""
from __future__ import annotations
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from agents.research_agent import research_activities
from agents.budget_agent import filter_by_budget
from agents.scheduler_agent import schedule


class ResearchADKAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        trip_request = ctx.session.state["trip_request"]
        candidates, research_note = research_activities(trip_request)
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={
                "candidates": candidates,
                "research_note": research_note,
            }),
        )


class BudgetADKAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        trip_request = ctx.session.state["trip_request"]
        candidates = ctx.session.state.get("candidates", [])
        affordable, insufficient, notes = filter_by_budget(trip_request, candidates)
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={
                "affordable": affordable,
                "budget_insufficient": insufficient,
                "budget_notes": notes,
            }),
        )


class SchedulerADKAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        trip_request = ctx.session.state["trip_request"]
        candidates = ctx.session.state.get("candidates", [])
        affordable = ctx.session.state.get("affordable", [])
        research_note = ctx.session.state.get("research_note", "")

        itinerary = schedule(trip_request, affordable)

        insufficient = ctx.session.state.get("budget_insufficient", False)
        budget_notes = ctx.session.state.get("budget_notes", "")

        if not candidates and research_note:
            # PRD Section 13: unrecognized/no-data destination — research
            # found nothing real to work with, so surface that specific
            # explanation directly rather than the generic "no activities
            # to schedule" message the empty-candidates path would
            # otherwise produce.
            itinerary.status = "failed"
            itinerary.notes = research_note
        else:
            if insufficient and itinerary.status == "complete":
                itinerary.status = "partial"
            if research_note and itinerary.status == "complete":
                itinerary.status = "partial"
            itinerary.notes = " ".join(
                part for part in [itinerary.notes, research_note, budget_notes] if part
            ).strip()

        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"itinerary": itinerary}),
        )
