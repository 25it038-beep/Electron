"""Live Web Search engine for Electorn AI.

Queries public search indexes without requiring API keys, returning structured
results (title, link, snippet) and formatting them for CLI display and LLM context.
"""

from __future__ import annotations

import html
import re
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import httpx
from rich.table import Table


@dataclass
class SearchResult:
    """Individual web search result entry."""

    title: str
    url: str
    snippet: str


class WebSearchEngine:
    """Autonomous search engine supporting DuckDuckGo HTML and Instant Answer APIs."""

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Perform search and return list of SearchResults.

        Falls back across multiple endpoints if one is temporarily blocked.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        # Strategy 1: DuckDuckGo HTML endpoint
        results = self._search_duckduckgo_html(clean_query, max_results)
        if results:
            return results

        # Strategy 2: DuckDuckGo Instant Answer API
        results = self._search_duckduckgo_instant(clean_query, max_results)
        if results:
            return results

        # Strategy 3: Wikipedia OpenSearch & Summary API
        results = self._search_wikipedia_encyclopedic(clean_query, max_results)
        if results:
            return results

        return []

    def _search_duckduckgo_html(self, query: str, max_results: int) -> list[SearchResult]:
        """Query html.duckduckgo.com and parse result snippets and URLs."""
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query},
                    headers=self.headers,
                )
                if resp.status_code != 200:
                    return []

                text = resp.text

            # Extract result links and snippets
            link_matches = re.findall(
                r'<a class="result__url" href="([^"]+)".*?>(.*?)</a>',
                text,
                re.DOTALL,
            )
            snippet_matches = re.findall(
                r'<a class="result__snippet"[^>]*>(.*?)</a>',
                text,
                re.DOTALL,
            )

            results: list[SearchResult] = []
            count = min(len(snippet_matches), max_results)

            for i in range(count):
                snippet_raw = snippet_matches[i]
                clean_snippet = html.unescape(re.sub(r"<[^>]+>", "", snippet_raw)).strip()

                raw_url = ""
                display_title = ""
                if i < len(link_matches):
                    raw_url = link_matches[i][0]
                    display_title = html.unescape(re.sub(r"<[^>]+>", "", link_matches[i][1])).strip()

                    # Resolve DuckDuckGo redirect uddg parameter
                    if "uddg=" in raw_url:
                        try:
                            parsed = urllib.parse.urlparse(raw_url)
                            qs = urllib.parse.parse_qs(parsed.query)
                            if "uddg" in qs:
                                raw_url = qs["uddg"][0]
                        except Exception:
                            pass

                results.append(
                    SearchResult(
                        title=display_title or f"Result #{i+1}",
                        url=raw_url or "https://duckduckgo.com",
                        snippet=clean_snippet,
                    )
                )

            return results
        except Exception:
            return []

    def _search_duckduckgo_instant(self, query: str, max_results: int) -> list[SearchResult]:
        """Query DuckDuckGo Instant Answer JSON API."""
        try:
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(url, headers=self.headers)
                if resp.status_code not in (200, 202):
                    return []
                data = resp.json()

            results: list[SearchResult] = []

            # 1. Check abstract
            abstract = data.get("AbstractText", "")
            abstract_url = data.get("AbstractURL", "")
            heading = data.get("Heading", query)
            if abstract:
                results.append(
                    SearchResult(
                        title=f"{heading} (Overview)",
                        url=abstract_url or "https://duckduckgo.com",
                        snippet=abstract,
                    )
                )

            # 2. Check related topics
            for topic in data.get("RelatedTopics", []):
                if len(results) >= max_results:
                    break
                if isinstance(topic, dict) and "Text" in topic:
                    results.append(
                        SearchResult(
                            title=topic.get("Text", "")[:60] + "...",
                            url=topic.get("FirstURL", "https://duckduckgo.com"),
                            snippet=topic.get("Text", ""),
                        )
                    )

            return results
        except Exception:
            return []

    def _search_wikipedia_encyclopedic(self, query: str, max_results: int) -> list[SearchResult]:
        """Query Wikipedia OpenSearch and REST Summary APIs for authoritative reference summaries."""
        try:
            url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit={max_results}&namespace=0&format=json"
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": "Electorn/0.1.0"})
                if resp.status_code != 200:
                    return []
                data = resp.json()

            if not isinstance(data, list) or len(data) < 4:
                return []

            titles = data[1]
            descriptions = data[2]
            urls = data[3]
            results: list[SearchResult] = []

            for i in range(min(len(titles), max_results)):
                t = titles[i]
                u = urls[i]
                desc = descriptions[i] if i < len(descriptions) else ""

                if not desc or len(desc) < 20:
                    try:
                        sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(t.replace(' ', '_'))}"
                        with httpx.Client(timeout=4.0, follow_redirects=True) as client:
                            s_resp = client.get(sum_url, headers={"User-Agent": "Electorn/0.1.0"})
                            if s_resp.status_code == 200:
                                desc = s_resp.json().get("extract", "")
                    except Exception:
                        pass

                if desc:
                    results.append(SearchResult(title=t, url=u, snippet=desc))

            return results
        except Exception:
            return []

    def format_table(self, query: str, results: list[SearchResult]) -> Table:
        """Format search results into a clean Rich Table."""
        table = Table(
            title=f"🌐 Web Search Results for: \"{query}\"",
            border_style="cyan",
            title_style="bold cyan",
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Title / Source", style="bold yellow", max_width=35)
        table.add_column("Snippet Summary", style="white")
        table.add_column("URL", style="dim cyan", overflow="fold")

        for idx, res in enumerate(results, 1):
            table.add_row(
                str(idx),
                res.title,
                res.snippet,
                res.url,
            )

        return table

    def format_context_prompt(self, query: str, results: list[SearchResult]) -> str:
        """Format search results as context string for LLM prompting."""
        if not results:
            return ""

        lines = [f"[WEB SEARCH CONTEXT for: '{query}']"]
        for idx, res in enumerate(results, 1):
            lines.append(f"{idx}. {res.title} ({res.url})")
            lines.append(f"   Summary: {res.snippet}")
        lines.append("[END WEB SEARCH CONTEXT]\n")

        return "\n".join(lines)
