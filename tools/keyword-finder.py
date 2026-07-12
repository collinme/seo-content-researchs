#!/usr/bin/env python3
"""
Keyword Finder — Multi-source SEO keyword discovery.
Zero external dependencies (stdlib only).

Sources:
  - DuckDuckGo via Jina Reader proxy (r.jina.ai) — bypasses IP-based anti-bot
  - Jina Reader for page content extraction

Usage:
  python3 tools/keyword-finder.py --product "heavy duty tarp" --countries "us,ca,uk"
  python3 tools/keyword-finder.py --product "pvc tarpaulin" --countries "us,ca,uk,au" --output /tmp/kws.md
"""

import os
import re
import sys
import time
import urllib.parse
import urllib.request
from argparse import ArgumentParser
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


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
    # Generic
    {"template": "{product} {country}", "intent": "generic"},
]


@dataclass
class KeywordResult:
    keyword: str
    intent: str
    country: str
    source: str
    competition: str = "🟡 Medium"
    related_terms: list = field(default_factory=list)


def jina_search(query: str) -> list:
    """
    Search DuckDuckGo via Jina Reader proxy.
    Jina handles page rendering on their servers, bypassing IP-based anti-bot.
    Returns list of dicts with 'title', 'url', 'domain', 'description'.
    """
    # Use DDG lite as the search backend, proxied through Jina
    ddg_url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
    proxy_url = f"https://r.jina.ai/{urllib.parse.quote(ddg_url, safe='')}"

    req = urllib.request.Request(
        proxy_url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "text/plain",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return [{"url": "", "title": f"ERROR: {e}", "domain": "", "description": ""}]

    results = []
    seen_urls = set()

    # Jina returns DDG results as clean markdown with format:
    # N.[Title](URL)
    # Description text...
    # domain.com
    #
    # Skip the first "Title:" and "URL Source:" header lines

    # Find all result blocks: number + title + URL in markdown link format
    # Pattern: N.[Title text](URL) followed by optional description and domain
    link_pattern = re.compile(
        r'^(\d+)\.\s*\[([^\]]+)\]\(https://duckduckgo\.com/l/\?uddg=([^&\s]+)',
        re.MULTILINE
    )

    for match in link_pattern.finditer(content):
        num = match.group(1)
        title = match.group(2).strip()
        url_encoded = match.group(3)

        # URL-decode the actual URL from DDG's redirect
        try:
            actual_url = urllib.parse.unquote(url_encoded)
        except Exception:
            actual_url = url_encoded

        # Skip sponsored links (DDG marks them with a note)
        if not actual_url or actual_url in seen_urls:
            continue
        seen_urls.add(actual_url)

        domain = urllib.parse.urlparse(actual_url).netloc

        # Extract description: text between this link and the next link or end
        desc_pattern = num + r'\.\s*\[[^\]]+\]\([^)]+\)\s*\n(.*?)(?:\n\d+\.\s*\[|\Z)'
        desc_match = re.search(desc_pattern, content, re.DOTALL)
        description = ""
        if desc_match:
            raw_desc = desc_match.group(1).strip()
            # Remove the domain line from description
            lines = raw_desc.split('\n')
            desc_lines = [l for l in lines if l.strip() and l.strip() != domain]
            description = ' '.join(desc_lines[:3])[:200] if desc_lines else ""

        results.append({
            "title": title,
            "url": actual_url,
            "domain": domain,
            "description": description,
        })

    # If no results matched via DDG redirect, try direct URL extraction
    if not results:
        # Fallback: extract all URLs from the markdown
        all_urls = re.findall(r'https?://[^\s)"]+', content)
        for url in all_urls:
            if 'duckduckgo.com' in url or 'r.jina.ai' in url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            domain = urllib.parse.urlparse(url).netloc
            results.append({
                "title": domain,
                "url": url,
                "domain": domain,
                "description": "",
            })

    return results


def estimate_competition(keyword: str, pattern: dict) -> str:
    """Heuristic competition estimation based on keyword specificity."""
    intent = pattern.get("intent", "")
    words = len(keyword.split())

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
    if words <= 2:
        return "🔴 High"
    return "🟡 Medium"


def discover_keywords(product: str, countries: list) -> list:
    """Run keyword discovery across all patterns for given countries."""
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

            # Search via Jina proxy
            results = jina_search(query)
            for r in results[:5]:  # top 5 per pattern
                if not r["url"]:
                    continue

                # Extract keyword from result title or use the query itself
                kw = r["title"].strip()
                kw_norm = kw.lower()

                # Dedup: skip if we've seen similar content
                if kw_norm not in seen and len(kw) > 3:
                    seen.add(kw_norm)
                    all_keywords.append(KeywordResult(
                        keyword=kw,
                        intent=pattern["intent"],
                        country=country_lower,
                        source="DDG via Jina",
                        competition=estimate_competition(kw, pattern),
                    ))

            # Polite delay to avoid rate limiting
            time.sleep(0.8)

    return all_keywords


def print_table(keywords: list, product: str, countries_str: str, output_file: Optional[str] = None):
    """Render keyword results as markdown table."""
    lines = []
    lines.append("# SEO Keyword Discovery Results\n")
    lines.append(f"**Product:** {product}  ")
    lines.append(f"**Countries:** {countries_str}  ")
    lines.append(f"**Total keywords found:** {len(keywords)}\n")

    by_country = defaultdict(list)
    for kw in keywords:
        by_country[kw.country].append(kw)

    for country in sorted(by_country.keys()):
        lines.append(f"## {country.upper()} — Keywords\n")
        lines.append("| # | Keyword | Intent | Competition | Source |")
        lines.append("|---|---------|--------|:-----------:|:------:|")
        for i, kw in enumerate(by_country[country], 1):
            lines.append(f"| {i} | {kw.keyword} | {kw.intent} | {kw.competition} | {kw.source} |")
        lines.append("")

    lines.append("## Summary\n")
    lines.append("| Country | Count | Low Comp | Med Comp | High Comp |")
    lines.append("|---------|:-----:|:--------:|:--------:|:---------:|")
    for country in sorted(by_country.keys()):
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
    parser = ArgumentParser(description="Multi-source SEO keyword discovery (Jina proxy)")
    parser.add_argument("--product", required=True, help="Product name (e.g. 'heavy duty tarp')")
    parser.add_argument("--countries", default="us", help="Comma-separated country codes")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    countries = [c.strip() for c in args.countries.split(",") if c.strip()]
    if not countries:
        print("❌ No valid countries specified", file=sys.stderr)
        sys.exit(1)

    print(f"🔄 Discovering keywords for: {args.product}", file=sys.stderr)
    print(f"   Target markets: {', '.join(countries)}", file=sys.stderr)
    print(f"   Source: DuckDuckGo (via Jina Reader proxy, no API key needed)", file=sys.stderr)
    print("", file=sys.stderr)

    results = discover_keywords(args.product, countries)

    if not results:
        print("\n⚠️  No keywords found.", file=sys.stderr)
        print("   Jina Reader returned empty results for all queries.", file=sys.stderr)
        print("   Try: a broader product name, or check network connectivity.", file=sys.stderr)
        sys.exit(1)

    print_table(results, args.product, args.countries, args.output)
