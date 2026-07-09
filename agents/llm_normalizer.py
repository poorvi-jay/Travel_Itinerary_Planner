"""
LLM Normalizer — Sprint 2.

Takes raw, inconsistent place dicts from the search provider and uses
Groq (free-tier, OpenAI-style chat API, fast Llama inference) to
normalize them into the fields our Activity model needs: category (from
a fixed taxonomy) and a best-effort opening_hours string when the source
doesn't have one (explicitly prefixed "estimated:" so it's never confused
with a confirmed hour).

Deliberately does NOT:
  - invent a name or coordinates (those come straight from the search
    provider, or the place is skipped — PRD Section 16: "no activity
    without a source")
  - estimate cost (that's the Budget Agent's job, PRD Section 10)
"""
from __future__ import annotations
import json

CATEGORY_TAXONOMY = [
    "sightseeing", "museum", "outdoor", "dining", "tour",
    "nightlife", "shopping", "entertainment", "other",
]

# Groq free-tier model. "llama-3.3-70b-versatile" is a good quality/speed
# balance; swap to "llama-3.1-8b-instant" if you want faster/cheaper-on-
# rate-limit at slightly lower quality.
GROQ_MODEL = "llama-3.3-70b-versatile"


def normalize_places(raw_places: list[dict], api_key: str) -> list[dict]:
    """
    Returns a list of dicts shaped for Activity(**dict): name, category,
    lat, long, opening_hours, source. Raises on missing dependency or API
    failure; caller is expected to catch and fall back to the stub.
    """
    try:
        from groq import Groq
    except ImportError as e:
        raise RuntimeError(
            "The 'groq' package is required. Install it with: pip install groq"
        ) from e

    if not raw_places:
        return []

    client = Groq(api_key=api_key)

    prompt = (
        "You are normalizing raw local-search results into a fixed schema. "
        "Do not invent facts — only categorize and, if hours are missing, "
        "give a plausible typical range for that category.\n\n"
        f"Allowed categories: {CATEGORY_TAXONOMY}\n\n"
        "For each place (same order as input), return an object with:\n"
        "  - category: best-fit from the allowed list\n"
        "  - opening_hours: use the source's hours if present in the input; "
        "otherwise give a plausible TYPICAL range for that category, "
        "prefixed with 'estimated: ' (e.g. 'estimated: 09:00-17:00')\n\n"
        "Return ONLY a JSON array, no other text, no markdown fences.\n\n"
        f"Places:\n{json.dumps(raw_places, default=str)}"
    )

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = response.choices[0].message.content.strip()
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    normalized_meta = json.loads(raw_text)

    results = []
    for place, meta in zip(raw_places, normalized_meta):
        gps = place.get("gps_coordinates", {}) or {}
        name = place.get("title") or place.get("name")
        if not name:
            continue  # skip un-named junk rather than fabricate one
        results.append({
            "name": name,
            "category": meta.get("category", "other"),
            "lat": gps.get("latitude", 0.0),
            "long": gps.get("longitude", 0.0),
            "opening_hours": meta.get("opening_hours", "estimated: unknown"),
            "source": f"serpapi:{place.get('place_id', 'unknown')}",
        })
    return results