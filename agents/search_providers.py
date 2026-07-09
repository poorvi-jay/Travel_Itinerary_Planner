"""
Search provider abstraction — Sprint 2.

Kept as a small interface so swapping providers (e.g. to Tavily) later is
a one-file change. We chose SerpAPI's Google Local engine because it
returns structured place data (name, category, gps_coordinates, sometimes
hours) straight from Google's Places database, rather than prose that an
LLM would have to guess coordinates/hours from — which is exactly the
hallucination risk the PRD flags in Section 16.
"""
from __future__ import annotations


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