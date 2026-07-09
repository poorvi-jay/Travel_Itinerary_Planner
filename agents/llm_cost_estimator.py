"""
LLM Cost Estimator — Sprint 2.

Uses Groq (same client/model as the Research Agent's normalizer) to give a
typical average per-person USD cost for each activity, given its name,
category, and destination. This is inherently a guess — there is no priced
source to draw from — so it's kept as a separate, swappable piece and the
Budget Agent falls back to a fixed per-category table if this call is
unavailable or fails.
"""
from __future__ import annotations
import json

from models import Activity

GROQ_MODEL = "llama-3.3-70b-versatile"


def estimate_costs(activities: list[Activity], destination: str, api_key: str) -> dict[str, float]:
    """
    Returns a dict mapping activity.id -> estimated USD cost (float, >= 0).
    Raises RuntimeError on missing dependency, API failure, or a malformed
    response; caller is expected to catch and fall back to a heuristic table.
    """
    try:
        from groq import Groq
    except ImportError as e:
        raise RuntimeError(
            "The 'groq' package is required. Install it with: pip install groq"
        ) from e

    if not activities:
        return {}

    client = Groq(api_key=api_key)

    items = [{"name": a.name, "category": a.category} for a in activities]
    prompt = (
        "Estimate a typical average per-person cost in USD for each of the "
        f"following activities in {destination}. Use 0 for activities that "
        "are typically free (e.g. most public parks, walking around a "
        "neighborhood). Give one best-guess number, not a range.\n\n"
        "Return ONLY a JSON array of numbers, same order as the input, no "
        "other text, no markdown fences.\n\n"
        f"Activities:\n{json.dumps(items)}"
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content.strip()
        raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        costs = json.loads(raw_text)
    except Exception as e:
        raise RuntimeError(f"Groq cost-estimation call failed: {e}") from e

    if not isinstance(costs, list) or len(costs) != len(activities):
        raise RuntimeError(
            f"Groq returned {costs if not isinstance(costs, list) else len(costs)} "
            f"costs for {len(activities)} activities."
        )

    return {a.id: max(0.0, float(c)) for a, c in zip(activities, costs)}
