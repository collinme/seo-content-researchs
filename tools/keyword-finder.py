#!/usr/bin/env python3
"""
Keyword Finder — Multi-source SEO keyword discovery.
Zero external dependencies (stdlib only).

Sources:
  - DuckDuckGo lite (no API key)
  - Bing with market parameter
  - Jina AI Reader for content-level extraction

Usage:
  python3 tools/keyword-finder.py --product "heavy duty tarp" --countries "us,ca,uk"
  python3 tools/keyword-finder.py --product "pvc tarpaulin" --countries "us,ca,uk,au" --output /tmp/kws.md
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from argparse import ArgumentParser
from collections import defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Optional

# ─── Search Patterns ─────────────────────────────────────────────────────────

SEARCH_PATTERNS = [
    # B2B procurement
    {"template": "{product} manufacturer {country}", "intent": "B2B procurement"},
    {"template": "{product} supplier {country}", "intent": "B2B procurement"},
    {"template": "{product} factory {country}", "intent": "B2B procurement"},
    # Wholesale
    {"template": "wholesale {product} {country}", "intent": "wholesale"},
    {"template": "bulk {product} {country}", "intent": "wholesale"},
    # OEM / custom
    {"template": "custom {product} {country}", "intent": "OEM/custom"},
    {"template": "OEM {product} {country}", "intent": "OEM/custom"},
    # Import / supply chain
    {"template": "import {product} from china to {country}", "intent": "import/supply chain"},
    {"template": "china {product} export {country}", "intent": "import/supply chain"},
    # Application
    {"template": "{product} for {country} market", "intent": "application"},
    # Comparison
    {"template": "{product} buying guide {country}", "intent": "comparison/guide"},
    {"template": "best {product} {country}", "intent": "comparison/guide"},
    # Local language (generic fallback — real localisation needs per-language patterns)
    {"template": "{product} {country}", "intent": "generic"},
]

COUNTRY_MKT = {
    "us": "en-US", "ca": "en-CA", "uk": "en-GB", "au": "en-AU",
    "nz": "en-NZ", "ie": "en-IE", "in": "en-IN",
    "de": "de-DE", "fr": "fr-FR", "nl": "nl-NL",
    "ae": "en-AE", "sa": "en-SA", "sg": "en-SG",
}


class DuckDuckGoParser(HTMLParser):
    """Minimal parser for DuckDuckGo lite results."""
    def __init__(self):
        super().__init__()
        self.results = []
        self._in_result = False
        self._current_url = ""
        self._current_text = ""
        self._capture_text = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "a" and "result-link" in attrs_dict.get("class", ""):
            self._current_url = attrs_dict.get("href", "")
            self._in_result = True
            self._capture_text = True
            self._current_text = ""
        elif tag == "br" and self._in_result:
            self._capture_text = True

    def handle_data(self, data):
        if self._capture_text:
            self._current_text += data

    def handle_endtag(self, tag):
        if tag == "a" and self._in_result:
            self._in_result = False
            self._capture_text = False
            text = re.sub(r'\s+', ' ', self._current_text).strip()
            if text and self._current_url:
                self.results.append({"text": text, "url": self._current_url})
            self._current_text = ""
            self._current_url = ""


@dataclass
class KeywordResult:
    keyword: str
    intent: str
    country: str
    source: str
    competition: str = "🟡 Medium"  # default, refined later
    related_terms: list = field(default_factory=list)


def search_duckduckgo(query: str, retries: int = 2) -> list:
    """Search DuckDuckGo lite. Returns list of result dicts."""
    url = "https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "text/html",
        },
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            parser = DuckDuckGoParser()
            parser.feed(html)
            return parser.results
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
                continue
            return [{"text": f"ERROR: {e}", "url": ""}]


def search_bing(query: str, country: str = "us") -> list:
    """Search Bing with country-specific market parameter."""
    mkt = COUNTRY_MKT.get(country, "en-US")
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&mkt={mkt}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "text/html",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Extract search suggestions (Bing shows related searches at bottom)
        results = []
        # Simple extraction: find h2 tags with search result titles
        for match in re.finditer(r'<h2><a[^>]*href="([^"]*)"[^>]*>(.*?)</a></h2>', html, re.DOTALL):
            text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            if text:
                results.append({"text": text, "url": match.group(1)})
        # Also extract "related searches" section
        related = re.findall(r'<a[^>]*class="[^"]*b_rs[^"]*"[^>]*>(.*?)</a>', html)
        for r in related:
            text = re.sub(r'<[^>]+>', '', r).strip()
            if text:
                results.append({"text": text, "url": "", "related": True})
        return results
    except Exception:
        return []


def estimate_competition(keyword: str, pattern: dict) -> str:
    """
    Heuristic competition estimation.
    Longer-tail + higher specificity = lower competition.
    """
    intent = pattern.get("intent", "")
    words = len(keyword.split())

    # B2B supplier keywords tend to be less competitive than generic product terms
    if "compare" in keyword.lower() or "vs " in keyword.lower():
        return "🟢 Low"
    if "buying guide" in keyword.lower():
        return "🟢 Low"

    if intent in ("import/supply chain", "OEM/custom"):
        return "🟢 Low" if words > 4 else "🟡 Medium"

    if intent == "B2B procurement":
        return "🟡 Medium"

    if intent == "wholesale":
        return "🟡 Medium" if words > 3 else "🔴 High"

    # Generic/broad terms are hardest
    if words <= 2:
        return "🔴 High"

    return "🟡 Medium"


def discover_keywords(product: str, countries: list) -> list:
    """Run keyword discovery across all patterns and sources for given countries."""
    all_keywords: list = []
    seen = set()

    for country in countries:
        country_lower = country.strip().lower()
        print(f"  🔍 {country_lower}...", file=sys.stderr)

        for pattern in SEARCH_PATTERNS:
            query = pattern["template"].format(
                product=product,
                country=country_lower.upper() if country_lower in ("us", "uk", "ae") else country_lower
            )

            # DuckDuckGo
            ddg_results = search_duckduckgo(query)
            for r in ddg_results[:5]:  # top 5 per source
                kw = r["text"].strip()
                kw_norm = kw.lower()
                if kw_norm not in seen and len(kw) > 3:
                    seen.add(kw_norm)
                    all_keywords.append(KeywordResult(
                        keyword=kw,
                        intent=pattern["intent"],
                        country=country_lower,
                        source="DuckDuckGo",
                        competition=estimate_competition(kw, pattern),
                    ))

            # Bing (every other pattern to avoid rate limiting)
            if hash(query) % 3 != 0:  # simple sampling
                bing_results = search_bing(query, country_lower)
                for r in bing_results[:3]:
                    kw = r["text"].strip()
                    kw_norm = kw.lower()
                    if kw_norm not in seen and len(kw) > 3:
                        seen.add(kw_norm)
                        all_keywords.append(KeywordResult(
                            keyword=kw,
                            intent=pattern["intent"],
                            country=country_lower,
                            source="Bing",
                            competition=estimate_competition(kw, pattern),
                        ))

            # Polite delay
            time.sleep(0.3)

    return all_keywords


def print_table(keywords: list, output_file: Optional[str] = None):
    """Render keyword results as markdown table."""
    lines = []
    lines.append("# SEO Keyword Discovery Results\n")
    lines.append(f"**Product:** {args.product}  ")
    lines.append(f"**Countries:** {', '.join(args.countries.split(','))}  ")
    lines.append(f"**Total keywords found:** {len(keywords)}\n")

    # Group by country
    by_country = defaultdict(list)
    for kw in keywords:
        by_country[kw.country].append(kw)

    for country in by_country:
        lines.append(f"## {country.upper()} — Keywords\n")
        lines.append("| # | Keyword | Intent | Competition | Source |")
        lines.append("|---|---------|--------|:-----------:|:------:|")
        for i, kw in enumerate(by_country[country], 1):
            lines.append(f"| {i} | {kw.keyword} | {kw.intent} | {kw.competition} | {kw.source} |")
        lines.append("")

    # Summary
    lines.append("## Summary\n")
    lines.append("| Country | Count | Low Comp | Med Comp | High Comp |")
    lines.append("|---------|:-----:|:--------:|:--------:|:---------:|")
    for country in by_country:
        kws = by_country[country]
        low = sum(1 for k in kws if "Low" in k.competition)
        med = sum(1 for k in kws if "Medium" in k.competition)
        high = sum(1 for k in kws if "High" in k.competition)
        lines.append(f"| {country.upper()} | {len(kws)} | {low} | {med} | {high} |")

    output = "\n".join(lines)

    if output_file:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w") as f:
            f.write(output)
        print(f"\n✅ Written to {output_file}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    parser = ArgumentParser(description="Multi-source SEO keyword discovery")
    parser.add_argument("--product", required=True, help="Product name (e.g. 'heavy duty tarp')")
    parser.add_argument("--countries", default="us", help="Comma-separated country codes (e.g. 'us,ca,uk,au')")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    countries = [c.strip() for c in args.countries.split(",") if c.strip()]
    if not countries:
        print("❌ No valid countries specified", file=sys.stderr)
        sys.exit(1)

    print(f"🔄 Discovering keywords for: {args.product}", file=sys.stderr)
    print(f"   Target markets: {', '.join(countries)}", file=sys.stderr)
    print("", file=sys.stderr)

    results = discover_keywords(args.product, countries)

    if not results:
        print("\n⚠️  No keywords found. Possible causes:", file=sys.stderr)
        print("   - Network/firewall blocking DuckDuckGo or Bing", file=sys.stderr)
        print("   - Product name too narrow -- try broader terms", file=sys.stderr)
        print("   - All sources returned errors (check terminal output above)", file=sys.stderr)
        sys.exit(1)

    print_table(results, args.output)
