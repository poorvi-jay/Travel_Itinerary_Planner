# Travel Itinerary Planner — Sprint 1 Walking Skeleton

Implements Sprint 1 of the PRD: a stubbed but fully-wired pipeline
(Research → Budget → Scheduler), callable via CLI, tested against the
golden scenarios.

## What's real vs. stubbed right now

| Piece | Status |
|---|---|
| `agents/research_agent.py` | **Stub** — always returns the same 3 hardcoded activities, ignores destination |
| `agents/budget_agent.py` | **Stub** — pure passthrough, no filtering |
| `agents/scheduler_agent.py` | **Stub** — round-robins activities into days, no clustering, no opening-hours logic |
| `pipeline/pipeline.py` | Real wiring — chains the three agents; function boundaries match future ADK agent nodes |
| `main.py` | Real CLI entrypoint |
| `tests/golden_scenarios.py` | Real — the 5 scenarios from PRD §17 |
| `tests/test_pipeline_skeleton.py` | Real — checks the pipeline runs end-to-end without crashing and returns well-formed output |

Nothing here checks budget adherence, opening hours, or geography yet —
that's Sprint 2/3 per the PRD.

## Run it

```bash
# positional args
python main.py "Paris" 3 300

# flag style
python main.py --destination "Paris" --days 3 --budget 300

# raw JSON output
python main.py --destination "Paris" --days 3 --budget 300 --json
```

## Run the golden scenario checks

```bash
python tests/test_pipeline_skeleton.py
```

## Next up (Sprint 2, per PRD)

- Research agent: LangChain + a real search tool for actual activity data
- Budget agent: real cost estimation + filtering, plus the feedback loop
  rules in PRD §11 (max 2 retry rounds, category-drop then +15% ceiling)