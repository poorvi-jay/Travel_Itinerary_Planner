# Travel Itinerary Planner

## Current status: Sprint 3 complete + ADK/LangChain orchestration migration — real Research, Budget, and Scheduler Agents

| Piece | Status |
|---|---|
| `agents/research_agent.py` | **Real** — a LangChain tool-calling agent (`langchain-groq` `ChatGroq`, `langchain.agents.create_agent`) calls the SerpAPI search tool once per category, then Groq normalizes the results. Falls back automatically to stub data if `SERPAPI_API_KEY` / `GROQ_API_KEY` aren't set, or on any pipeline error, so the CLI never breaks. |
| `agents/search_providers.py` | **Real** — SerpAPI wrapper, plus `make_search_tool()` which exposes it as a LangChain `@tool` (PRD §7.1: "LangChain + a search tool") |
| `agents/llm_normalizer.py` | **Real** — Groq call that only categorizes + fills in missing hours (labeled `estimated:`); never invents names/coordinates/cost |
| `agents/llm_cost_estimator.py` | **Real** — Groq call that gives a typical per-activity USD cost; Budget Agent falls back to a fixed per-category table if this is unavailable/fails |
| `agents/budget_agent.py` | **Real** — greedy cheapest-first selection to fit `TripRequest.budget`, plus the PRD §11 feedback loop (round 1: drop most expensive category; round 2: raise ceiling 15%; still short after both → return best-effort set and flag itinerary "partial") |
| `agents/geo_clustering.py` | **Real** — k-means (scikit-learn) groups activities into `days` day-buckets by lat/long, then rebalances so k-means's occasional lopsided clusters don't leave a day empty |
| `agents/day_scheduler.py` | **Real** — orders each day's activities against `opening_hours` using a category-based duration heuristic (no real duration data exists), drops activities that don't fit, and enforces a concrete "unreasonable zigzag" threshold (1.5x the geographically-nearest-neighbor path length) — swaps to the geographic order only if that doesn't drop anything the time-window order kept |
| `agents/scheduler_agent.py` | **Real** — combines the two independently-tested pieces above per PRD §12; flags itinerary "partial" if anything got dropped or a zigzag couldn't be resolved |
| `agents/adk_agents.py` | **Real** — Google ADK `BaseAgent` wrappers (Research/Budget/Scheduler) around the three stages above, unchanged logic; communicate via ADK session state |
| `pipeline/pipeline.py` | **Real** — Google ADK orchestration (PRD §14): a `SequentialAgent` of the three ADK wrappers, run through ADK's `Runner` + `InMemorySessionService`. `run_pipeline()` keeps its original sync signature (drives the async ADK runner via `asyncio.run`), so `main.py` and the golden-scenario tests needed no changes. |
| `main.py` | Real CLI entrypoint |
| `tests/golden_scenarios.py` + `test_pipeline_skeleton.py` | Real — 5 scenarios from PRD §17, pass via fallback path with no keys set |

### ADK/LangChain migration notes
- **Orchestration**: `google-adk` 2.4.0's `SequentialAgent`/`BaseAgent` classes are used per PRD §14. Note: this ADK version has already deprecated `SequentialAgent` in favor of a newer `Workflow`/`Node` graph DSL (`google.adk.workflow`) — it still works correctly (verified directly against this version), but migrating to `Workflow` is a reasonable future follow-up, not done here to keep this migration scoped to orchestration wiring only.
- **Feedback loop scope**: PRD §11 describes the budget feedback loop as bidirectional ("research → budget → research → budget → stop"), but the real implementation — before and after this migration — is self-contained inside the Budget stage: its 3 rounds re-filter the *same* single Research candidate list rather than calling back into Research. This migration preserved that behavior deliberately rather than changing feedback-loop semantics; a true cross-agent loop (e.g. via ADK's `LoopAgent`) is a possible future enhancement, not built here.
- **Verification caveat**: no `SERPAPI_API_KEY`/`GROQ_API_KEY` were available in the environment this migration was built in, so the real (non-stub) LangChain/ADK path could only be verified up to the network boundary — confirmed with a throwaway fake key that the new code reaches Groq's API (gets a real 401) and still falls back to stub data cleanly, exactly like the pre-migration code did on any research error. The golden scenarios and CLI were fully verified end-to-end on the stub-fallback path.

### PRD §13 error handling
Closed the two gaps found in a PRD-compliance pass (Sprint 3 had listed "Add error handling (Section 13)" as done, but two of the four scenarios weren't actually built):
- **Unrecognized/no-data destination**: previously, *any* research failure — including a genuine, keys-configured search that found nothing — silently fell back to the same generic 3-activity stub, which is exactly the "hallucinated itinerary for a place with no real data" §13 warns against. Now `research_activities()` (`agents/research_agent.py`) only falls back to stub data for *technical* failures (no keys, network/auth/LLM errors); a real search that genuinely finds nothing returns an empty candidate list and a destination-specific message, and the pipeline surfaces that as itinerary `status="failed"` with a clear explanation instead of fake activities.
- **Day count mismatched to destination size**: `research_agent.py` now flags explicitly (v1 choice: flag rather than pad with nearby/day-trip options, since padding would need a "search nearby towns" capability that doesn't exist and risks fabricating filler) when real candidate count is too low for the requested trip length, independent of budget — e.g. "Found only 4 real candidate activities... not enough to comfortably fill a 5-day trip... consider a shorter trip (around 1 day(s))."
- **Suggested minimum budget**: `budget_agent.py`'s exhausted-feedback-loop message now computes and reports a suggested minimum (cost of the cheapest target-count activities) when the shortfall is genuinely a budget problem, not a destination-coverage one — the two messages are kept mutually exclusive so they don't contradict each other.

Verified via golden scenarios (unchanged on the stub-fallback path) plus a standalone script that monkeypatches the network boundary to exercise the no-data, day-count-mismatch, and full-ADK-pipeline-failed-status paths, plus the budget suggested-minimum branch with a synthetic activity pool — all pass.

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

## Next up

- Sprint 4: frontend (React form + day-by-day itinerary display) and an API layer in front of the pipeline.
- Revisit the Research↔Budget feedback loop as a true bidirectional ADK `LoopAgent` loop, instead of the current one-shot drop-category/raise-ceiling passes self-contained in the Budget stage.
- Consider migrating `pipeline/pipeline.py` off ADK's deprecated `SequentialAgent` onto the newer `Workflow`/`Node` DSL once it's more established.