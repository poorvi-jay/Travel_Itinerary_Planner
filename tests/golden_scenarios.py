"""
Golden test scenarios — PRD Section 17.

Maintained from Sprint 1 onward. Re-run after every sprint; used to
manually (and later automatically) check for opening-hours violations,
budget overruns, and zigzagging against the feasibility metric (PRD
Section 8).

In Sprint 1, the pipeline is a stub, so these scenarios only verify that
the pipeline runs end-to-end and produces a well-formed itinerary object
for each case — not real budget/schedule correctness yet.
"""
from dataclasses import dataclass


@dataclass
class GoldenScenario:
    name: str
    destination: str
    days: int
    budget: float
    description: str


GOLDEN_SCENARIOS = [
    GoldenScenario(
        name="major_city",
        destination="Paris, France",
        days=4,
        budget=800.0,
        description="Well-covered major city, generous multi-day budget.",
    ),
    GoldenScenario(
        name="small_town",
        destination="Hallstatt, Austria",
        days=3,
        budget=400.0,
        description="Smaller/less-documented destination.",
    ),
    GoldenScenario(
        name="tight_budget",
        destination="Bangkok, Thailand",
        days=3,
        budget=30.0,
        description="Very tight budget — should stress the budget/feedback loop in later sprints.",
    ),
    GoldenScenario(
        name="generous_budget",
        destination="Tokyo, Japan",
        days=5,
        budget=5000.0,
        description="Generous budget — should not artificially sparse-fill days.",
    ),
    GoldenScenario(
        name="short_trip",
        destination="Amsterdam, Netherlands",
        days=1,
        budget=150.0,
        description="Short (1-day) trip.",
    ),
]