# Travel Itinerary Planner

## Current status: Sprint 2 (in progress) — real Research + Budget Agents

| Piece | Status |
|---|---|
| `agents/research_agent.py` | **Real** — SerpAPI Local Results (multiple category queries) + Groq normalization. Falls back automatically to stub data if `SERPAPI_API_KEY` / `GROQ_API_KEY` aren't set, or on any pipeline error, so the CLI never breaks. |
| `agents/search_providers.py` | **Real** — SerpAPI wrapper, kept behind a small interface so swapping providers later is a one-file change |
| `agents/llm_normalizer.py` | **Real** — Groq call that only categorizes + fills in missing hours (labeled `estimated:`); never invents names/coordinates/cost |
| `agents/llm_cost_estimator.py` | **Real** — Groq call that gives a typical per-activity USD cost; Budget Agent falls back to a fixed per-category table if this is unavailable/fails |
| `agents/budget_agent.py` | **Real** — greedy cheapest-first selection to fit `TripRequest.budget`, plus the PRD §11 feedback loop (round 1: drop most expensive category; round 2: raise ceiling 15%; still short after both → return best-effort set and flag itinerary "partial") |
| `agents/scheduler_agent.py` | **Stub** — round-robins activities into days, no clustering, no opening-hours logic (Sprint 3) |
| `pipeline/pipeline.py` | Real wiring — chains the three agents and applies the Budget Agent's partial-itinerary flag; function boundaries match future ADK agent nodes |
| `main.py` | Real CLI entrypoint |
| `tests/golden_scenarios.py` + `test_pipeline_skeleton.py` | Real — 5 scenarios from PRD §17, pass via fallback path with no keys set |

## Setup

```bash
pip install -r requirements.txt
```

To use real search, normalization, and cost estimation instead of stub/heuristic data, set these environment variables (see `.env.example`):

```bash
# macOS/Linux
export SERPAPI_API_KEY=your-key
export GROQ_API_KEY=your-key

# Windows cmd.exe
set SERPAPI_API_KEY=your-key
set GROQ_API_KEY=your-key
```

Without `SERPAPI_API_KEY`/`GROQ_API_KEY` set, the research agent automatically uses Sprint 1 stub data (3 hardcoded activities) and prints a note to stderr. Without `GROQ_API_KEY` specifically, the budget agent uses a fixed per-category cost table instead of LLM cost estimates. Either way, nothing breaks and nothing needs configuring to run.

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

## Next up (Sprint 3, per PRD)

- Scheduler agent: geographic clustering (PRD §12) + time-window
  constraint satisfaction against `opening_hours`, built and tested
  independently before combining, plus a concrete "unreasonable zigzag"
  threshold.