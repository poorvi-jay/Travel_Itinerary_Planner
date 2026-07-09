"""
Search provider abstraction — Sprint 2.

Kept as a small interface so swapping providers (e.g. to Tavily) later is
a one-file change. We chose SerpAPI's Google Local engine because it
returns structured place data (name, category, gps_coordinates, sometimes
hours) straight from Google's Places database, rather than prose that an
LLM would have to guess coordinates/hours from — which is exactly the
hallucination risk the PRD flags in Section 16.

`make_search_tool` below wraps this in a LangChain tool (PRD Section 7.1:
"Research tooling: LangChain + a search tool") so the research agent can
call it through a LangChain tool-calling agent instead of invoking it
directly.
"""
from __future__ import annotations
import json


class SearchProviderError(Exception):
    """Raised when the underlying search API call fails (auth, network, quota)."""


class SerpApiLocalSearch:
    """
    Thin wrapper around SerpAPI's Google Local search engine
    (https://serpapi.com/local-results). Returns structured places:
    title, category ("type"), gps_coordinates, rating, address, and
    sometimes operating hours.
    """

    ENDPOINT = "https://serpapi.com/search"

    def __init__(self, api_key: str):
        if not api_key:
            raise SearchProviderError("SerpAPI key is missing.")
        self.api_key = api_key

    def search(self, query: str, num_results: int = 10) -> list[dict]:
        try:
            import requests
        except ImportError as e:
            raise SearchProviderError(
                "The 'requests' package is required for SerpAPI search. "
                "Install it with: pip install requests"
            ) from e

        params = {
            "engine": "google_local",
            "q": query,
            "api_key": self.api_key,
        }
        try:
            resp = requests.get(self.ENDPOINT, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise SearchProviderError(f"SerpAPI request failed: {e}") from e

        return data.get("local_results", [])[:num_results]


def make_search_tool(search_client: SerpApiLocalSearch):
    """
    Builds a LangChain tool bound to the given search client. Kept as a
    factory (rather than a module-level @tool) so the research agent
    controls the SerpAPI key/client lifecycle, not this module.

    Returns raw place dicts (same shape as `.search()`) JSON-encoded as
    the tool's string output, so the calling agent gets exactly the
    structured search results back — nothing invented in between.
    """
    from langchain_core.tools import tool

    @tool
    def search_local_places(category_query: str, destination: str) -> str:
        """Search for real local places (attractions, museums, parks,
        restaurants, tours, etc.) of a given category in a destination
        city. `category_query` should be a short category phrase (e.g.
        "top attractions", "museums", "notable restaurants"). Returns a
        JSON array of structured place results (title, category,
        gps_coordinates, and hours when available) straight from Google
        Local search — do not alter or summarize the results."""
        results = search_client.search(f"{category_query} in {destination}")
        return json.dumps(results, default=str)

    return search_local_places