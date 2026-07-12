#!/usr/bin/env python3
"""
Keyword Finder — SEO keyword discovery via Jina Reader proxy.
Zero external dependencies (stdlib only).

V2: Clean keyword output — uses search patterns as keywords, not page titles.
SERP results validate demand and refine competition estimates.

Usage:
  python3 tools/keyword-finder.py --product "heavy duty tarp" --countries "us,ca,uk"
  python3 tools/keyword-finder.py --product "pvc tarpaulin" --countries "us,ca,uk,au" --output /tmp/kws.md
  python3 tools/keyword-finder.py --product "aluminum profile" --countries "us,uk,ae" --clean
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
    {"template": "{product} for {country}", "intent": "application"},
    # Comparison
    {"template": "{product} buying guide {country}", "intent": "comparison/guide"},
    {"template": "best {product} {country}", "intent": "comparison/guide"},
]

# Countries whose codes should be uppercase in search queries
UPPER_COUNTRY = {"us", "uk", "ae"}


@dataclass
class KeywordResult:
    keyword: str
    intent: str
    country: str
    competition: str = "🟡 Medium"
    top_competitors: list = field(default_factory=list)


def jina_search(query: str) -> list:
    """Search DuckDuckGo via Jina Reader proxy. Returns list of result dicts."""
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
        return []

    results = []
    seen_urls = set()

    # Parse DDG markdown output: N.[Title](DDG-redirect-url)
    link_pattern = re.compile(
        r'^(\d+)\.\s*\[([^\]]+)\]\(https://duckduckgo\.com/l/\?uddg=([^&\s]+)',
        re.MULTILINE
    )

    for match in link_pattern.finditer(content):
        title = match.group(2).strip()
        url_encoded = match.group(3)

        try:
            actual_url = urllib.parse.unquote(url_encoded)
        except Exception:
            actual_url = url_encoded

        if not actual_url or actual_url in seen_urls:
            continue
        seen_urls.add(actual_url)

        domain = urllib.parse.urlparse(actual_url).netloc
        results.append({
            "title": title,
            "url": actual_url,
            "domain": domain,
        })

    # Sort: organic results first (DDG shows ads first)
    organic = [r for r in results if not is_ad_domain(r["domain"])]
    ads = [r for r in results if is_ad_domain(r["domain"])]
    # Filter out DDG redirect pages and trackers
    organic = [r for r in organic if "duckduckgo.com" not in r["domain"]]
    return organic + ads


def is_ad_domain(domain: str) -> bool:
    """Check if a domain is likely an ad/tracker."""
    ad_indicators = ["doubleclick", "googlead", "bing.com/aclick", "outbrain"]
    return any(ind in domain.lower() for ind in ad_indicators)


def estimate_competition_from_serp(serp_results: list) -> str:
    """Refine competition estimate based on actual SERP composition.

    Rules:
    - 3+ manufacturers in top 10 → 🔴 High (hard to outrank)
    - 2+ B2B platforms (Alibaba/MIC) in top 5 → 🔴 High
    - Only BigBox/B2C retailers in top 5 → 🟢 Low (not direct comp)
    - Mix of niche sites and guides → 🟡 Medium
    """
    if not serp_results:
        return "🟡 Medium"

    top10 = serp_results[:10]
    domain_text = " ".join(r["domain"].lower() for r in top10)
    title_text = " ".join(r["title"].lower() for r in top10)
    combined = domain_text + " " + title_text

    # Count manufacturer/factory signals
    mfg_signals = ["manufacturer", "factory", "supplier", "producer", "made in"]
    manufacturer_count = sum(1 for r in top10
                             if any(s in r["domain"].lower() or s in r["title"].lower()
                                    for s in mfg_signals))

    # B2B platform count
    b2b_domains = ["alibaba", "made-in-china", "globalsources", "indiamart"]
    b2b_count = sum(1 for r in top10
                    if any(d in r["domain"].lower() for d in b2b_domains))

    # BigBox retailer count
    bigbox_domains = ["amazon", "walmart", "homedepot", "lowes", "costco"]
    bigbox_count = sum(1 for r in top10
                       if any(d in r["domain"].lower() for d in bigbox_domains))

    # Competition assessment
    if manufacturer_count >= 3:
        competitor_names = [r["domain"] for r in top10[:5]
                            if any(s in r["domain"].lower() or s in r["title"].lower()
                                   for s in mfg_signals)]
        return f"🔴 High ({manufacturer_count} manufacturers: {', '.join(competitor_names[:3])})"

    if b2b_count >= 2:
        return f"🔴 High ({b2b_count} B2B platforms dominate)"

    if bigbox_count >= 4:
        return "🟢 Low (BigBox B2C, not direct B2B comp)"

    if manufacturer_count == 0 and b2b_count == 0:
        return "🟢 Low (few direct competitors)"

    return "🟡 Medium (mixed competition)"


def get_top_competitors(serp_results: list, max_n: int = 3) -> list:
    """Extract top competitor domains + types using both domain and title."""
    competitors = []
    for r in serp_results[:max_n]:
        domain = r["domain"]
        title = r["title"].lower()
        combined = domain.lower() + " " + title

        # Type classification — title is more indicative than domain
        if any(d in domain for d in ["alibaba", "made-in-china", "globalsources"]):
            label = "B2B platform"
        elif any(d in domain for d in ["amazon", "walmart", "homedepot"]):
            label = "BigBox retail"
        elif any(kw in combined for kw in ["manufacturer", "manufacturing", "factory",
                                             "made in usa", "made in the usa"]):
            label = "Manufacturer"
        elif ".cn" in domain or "china" in domain:
            label = "China factory"
        elif "tarps" in domain or "tarp" in domain:
            label = "Tarp retailer"
        elif "wholesale" in combined or "wholesaler" in combined:
            label = "Wholesaler"
        else:
            label = "Retail/niche"
        competitors.append(f"{domain} ({label})")
    return competitors


def discover_keywords(product: str, countries: list, clean_mode: bool = False) -> list:
    """Run keyword discovery. In clean mode, output search queries as keywords."""
    all_keywords: list = []
    seen_queries = set()

    for country in countries:
        country_lower = country.strip().lower()
        country_code = country_lower.upper() if country_lower in UPPER_COUNTRY else country_lower
        print(f"  🔍 {country_lower}...", file=sys.stderr)

        for pattern in SEARCH_PATTERNS:
            query = pattern["template"].format(
                product=product,
                country=country_code,
            )

            # Dedup: skip if we already processed this exact query for this country
            query_key = f"{country_lower}:{query.lower()}"
            if query_key in seen_queries:
                continue
            seen_queries.add(query_key)

            # Search via Jina proxy
            serp_results = jina_search(query)

            if clean_mode:
                # In clean mode, the search query IS the keyword
                competition = estimate_competition_from_serp(serp_results)
                competitors = get_top_competitors(serp_results) if serp_results else []

                kw = KeywordResult(
                    keyword=query,
                    intent=pattern["intent"],
                    country=country_lower,
                    competition=competition,
                    top_competitors=competitors,
                )
                all_keywords.append(kw)
            else:
                # Legacy mode: extract keywords from page titles
                for r in serp_results[:3]:
                    title = r["title"].strip()
                    title_norm = title.lower()
                    if title_norm not in seen_queries and len(title) > 5:
                        seen_queries.add(title_norm)
                        kw = KeywordResult(
                            keyword=title,
                            intent=pattern["intent"],
                            country=country_lower,
                            competition="🟡 Medium",
                        )
                        all_keywords.append(kw)

            # Polite delay
            time.sleep(0.8)

    return all_keywords


def print_table(keywords: list, product: str, countries_str: str,
                clean: bool = False, output_file: Optional[str] = None):
    """Render keyword results as markdown table."""
    lines = []
    lines.append("# SEO Keyword Discovery Results\n")
    lines.append(f"**Product:** {product}  ")
    lines.append(f"**Countries:** {countries_str}  ")
    lines.append(f"**Mode:** {'Clean keywords' if clean else 'Raw SERP titles'}  ")
    lines.append(f"**Total keywords found:** {len(keywords)}\n")

    by_country = defaultdict(list)
    for kw in keywords:
        by_country[kw.country].append(kw)

    for country in sorted(by_country.keys()):
        country_kws = by_country[country]
        lines.append(f"## {country.upper()} — {len(country_kws)} Keywords\n")

        if clean:
            lines.append("| # | Keyword | Intent | Competition | Top Competitors |")
            lines.append("|---|---------|--------|:-----------:|:---------------:|")
            for i, kw in enumerate(country_kws, 1):
                comps = ", ".join(kw.top_competitors[:2]) if kw.top_competitors else "-"
                lines.append(f"| {i} | `{kw.keyword}` | {kw.intent} | {kw.competition} | {comps} |")
        else:
            lines.append("| # | Keyword | Intent | Competition |")
            lines.append("|---|---------|--------|:-----------:|")
            for i, kw in enumerate(country_kws, 1):
                lines.append(f"| {i} | {kw.keyword} | {kw.intent} | {kw.competition} |")

        lines.append("")

    # Summary
    lines.append("## Summary\n")
    lines.append("| Country | Count |")
    lines.append("|---------|:-----:|")
    for country in sorted(by_country.keys()):
        lines.append(f"| {country.upper()} | {len(by_country[country])} |")

    output = "\n".join(lines)

    if output_file:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w") as f:
            f.write(output)
        print(f"\n✅ Written to {output_file}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    parser = ArgumentParser(description="SEO keyword discovery (clean keyword output)")
    parser.add_argument("--product", required=True, help="Product name")
    parser.add_argument("--countries", default="us", help="Comma-separated country codes")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--clean", action="store_true",
                        help="Clean mode: output search queries as keywords (recommended)")
    args = parser.parse_args()

    countries = [c.strip() for c in args.countries.split(",") if c.strip()]
    if not countries:
        print("❌ No valid countries specified", file=sys.stderr)
        sys.exit(1)

    print(f"🔄 Discovering keywords for: {args.product}", file=sys.stderr)
    print(f"   Target markets: {', '.join(countries)}", file=sys.stderr)
    print(f"   Mode: {'Clean' if args.clean else 'Legacy (SERP titles)'}", file=sys.stderr)
    print(f"   Source: DuckDuckGo via Jina Reader proxy", file=sys.stderr)
    print("", file=sys.stderr)

    results = discover_keywords(args.product, countries, clean_mode=args.clean)

    if not results:
        print("\n⚠️  No keywords found.", file=sys.stderr)
        print("   Jina Reader returned empty results.", file=sys.stderr)
        sys.exit(1)

    print_table(results, args.product, args.countries, clean=args.clean, output_file=args.output)
