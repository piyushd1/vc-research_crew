from __future__ import annotations

import json
import os
from urllib import error, request

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared helpers (same pattern as tavily_tool.py)
# ---------------------------------------------------------------------------

_TAVILY_SEARCH_URL = "https://api.tavily.com/search"
_TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"


def _get_api_key() -> str | None:
    return os.environ.get("TAVILY_API_KEY") or None


def _post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    """POST *payload* as JSON to *url* and return the decoded response."""
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _tavily_search(api_key: str, query: str, max_results: int = 3) -> dict:
    """Run a Tavily search and return the raw response dict."""
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
    }
    return _post_json(_TAVILY_SEARCH_URL, payload)


def _tavily_extract(api_key: str, url: str) -> dict:
    """Run a Tavily extract on a single URL and return the raw response dict."""
    payload = {
        "api_key": api_key,
        "urls": [url],
    }
    return _post_json(_TAVILY_EXTRACT_URL, payload)


def _search_and_extract(
    api_key: str,
    search_query: str,
    source_label: str,
    max_content_chars: int = 5000,
) -> str:
    """Search for a page, extract the first result, and return formatted content.

    This is the shared pattern used by Tofler, Tracxn, Crunchbase, and
    Play Store tools.
    """
    # Step 1: Search
    try:
        search_data = _tavily_search(api_key, search_query)
    except error.URLError as exc:
        return f"{source_label} search failed: {exc}"

    results = search_data.get("results", [])
    if not results:
        return f"No {source_label} results found for query: {search_query}"

    first_url = results[0].get("url", "")
    first_title = results[0].get("title", "Untitled")

    if not first_url:
        return f"{source_label} search returned a result without a URL."

    # Step 2: Extract full page content
    try:
        extract_data = _tavily_extract(api_key, first_url)
    except error.URLError as exc:
        # Fall back to search snippet if extract fails
        snippet = results[0].get("content", "No content available.")
        return (
            f"{source_label} extract failed (falling back to search snippet): {exc}\n"
            f"Source: {first_url}\n"
            f"{snippet[:max_content_chars]}"
        )

    extracted_results = extract_data.get("results", [])
    if not extracted_results:
        # Fall back to search snippet
        snippet = results[0].get("content", "No content available.")
        return (
            f"{source_label}: No content extracted from {first_url}\n"
            f"Search snippet: {snippet[:max_content_chars]}"
        )

    raw_content = extracted_results[0].get("raw_content", "")
    if not raw_content:
        raw_content = extracted_results[0].get("content", "")

    truncated = raw_content[:max_content_chars]
    lines = [
        f"{source_label} result: {first_title}",
        f"Source: {first_url}",
        f"Content length: {len(raw_content)} chars (showing first {len(truncated)})",
        "",
        truncated,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class CompanyNameInput(BaseModel):
    company_name: str = Field(
        ...,
        description="Name of the Indian company to look up.",
    )


# ---------------------------------------------------------------------------
# Tool 1: Tofler (MCA / ROC filings)
# ---------------------------------------------------------------------------


class ToflerCompanyTool(BaseTool):
    """Looks up Indian company MCA/ROC filing data on Tofler.in."""

    name: str = "tofler_company_lookup"
    description: str = (
        "Looks up Indian company MCA/ROC filing data on Tofler.in. "
        "Returns CIN, directors, capital, filing status."
    )
    args_schema: type[BaseModel] = CompanyNameInput

    def _run(self, company_name: str) -> str:
        api_key = _get_api_key()
        if not api_key:
            return "TAVILY_API_KEY is not configured."

        query = f'site:tofler.in "{company_name}"'
        return _search_and_extract(api_key, query, "Tofler")


# ---------------------------------------------------------------------------
# Tool 2: Tracxn (startup funding data)
# ---------------------------------------------------------------------------


class TracxnCompanyTool(BaseTool):
    """Looks up startup data on Tracxn."""

    name: str = "tracxn_company_lookup"
    description: str = (
        "Looks up startup data on Tracxn. "
        "Returns funding rounds, investors, valuation, employee count."
    )
    args_schema: type[BaseModel] = CompanyNameInput

    def _run(self, company_name: str) -> str:
        api_key = _get_api_key()
        if not api_key:
            return "TAVILY_API_KEY is not configured."

        query = f'site:tracxn.com "{company_name}" India'
        return _search_and_extract(api_key, query, "Tracxn")


# ---------------------------------------------------------------------------
# Tool 3: Crunchbase (funding history and investors)
# ---------------------------------------------------------------------------


class CrunchbaseCompanyTool(BaseTool):
    """Looks up company on Crunchbase."""

    name: str = "crunchbase_company_lookup"
    description: str = (
        "Looks up company on Crunchbase. "
        "Returns funding history, investors, key people."
    )
    args_schema: type[BaseModel] = CompanyNameInput

    def _run(self, company_name: str) -> str:
        api_key = _get_api_key()
        if not api_key:
            return "TAVILY_API_KEY is not configured."

        query = f'site:crunchbase.com/organization "{company_name}"'
        return _search_and_extract(api_key, query, "Crunchbase")


# ---------------------------------------------------------------------------
# Tool 4: Google Play Store (app metrics)
# ---------------------------------------------------------------------------


class GooglePlayStoreTool(BaseTool):
    """Looks up app data on Google Play Store."""

    name: str = "google_play_store_lookup"
    description: str = (
        "Looks up app data on Google Play Store. "
        "Returns rating, downloads, reviews."
    )
    args_schema: type[BaseModel] = CompanyNameInput

    def _run(self, company_name: str) -> str:
        api_key = _get_api_key()
        if not api_key:
            return "TAVILY_API_KEY is not configured."

        query = f'site:play.google.com "{company_name}" app'
        return _search_and_extract(api_key, query, "Google Play Store")


# ---------------------------------------------------------------------------
# Tool 5: India Job Signal (Naukri + Indeed)
# ---------------------------------------------------------------------------


class IndiaJobSignalTool(BaseTool):
    """Searches for job postings on Naukri.com and Indeed India."""

    name: str = "india_job_signal"
    description: str = (
        "Searches for job postings on Naukri.com and Indeed India. "
        "Hiring velocity = growth signal."
    )
    args_schema: type[BaseModel] = CompanyNameInput

    def _run(self, company_name: str) -> str:
        api_key = _get_api_key()
        if not api_key:
            return "TAVILY_API_KEY is not configured."

        query = f'"{company_name}" jobs India site:naukri.com OR site:indeed.co.in'
        try:
            search_data = _tavily_search(api_key, query, max_results=5)
        except error.URLError as exc:
            return f"India job signal search failed: {exc}"

        results = search_data.get("results", [])
        if not results:
            return f"No job postings found for '{company_name}' on Naukri or Indeed India."

        lines = [
            f"Job signal for: {company_name}",
            f"Listings found: {len(results)}",
            "",
        ]
        for item in results:
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            content = item.get("content", "")
            lines.append(f"- {title}")
            lines.append(f"  URL: {url}")
            if content:
                lines.append(f"  {content[:300]}")
        return "\n".join(lines)
