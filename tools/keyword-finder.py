#!/usr/bin/env python3
"""
Keyword Finder — SEO keyword discovery.
Zero external dependencies (stdlib only).

Data sources:
  - DuckDuckGo via Jina Reader proxy (default, stable, unlimited)
  - Startpage via Google Alliance (opt-in with --google, sometimes captcha)

Usage:
  python3 tools/keyword-finder.py --product "heavy duty tarp" --countries "us,ca,uk"
  python3 tools/keyword-finder.py --product "pvc tarpaulin" --countries "us,ca,uk,au" --clean --output /tmp/kws.md
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
    {"template": "{product} manufacturer {country}", "intent": "B2B procurement"},
    {"template": "{product} supplier {country}", "intent": "B2B procurement"},
    {"template": "{product} factory {country}", "intent": "B2B procurement"},
    {"template": "wholesale {product} {country}", "intent": "wholesale"},
    {"template": "bulk {product} {country}", "intent": "wholesale"},
    {"template": "custom {product} {country}", "intent": "OEM/custom"},
    {"template": "OEM {product} {country}", "intent": "OEM/custom"},
    {"template": "import {product} from china to {country}", "intent": "import/supply chain"},
    {"template": "china {product} export {country}", "intent": "import/supply chain"},
    {"template": "{product} for {country}", "intent": "application"},
    {"template": "{product} buying guide {country}", "intent": "comparison/guide"},
    {"template": "best {product} {country}", "intent": "comparison/guide"},
]

UPPER_COUNTRY = {"us", "uk", "ae"}


# ─── Search engine selection ─────────────────────────────────────────────────

def _build_opener(use_proxy: bool = False):
    """Build urllib opener, optionally via v2raya SOCKS5 proxy."""
    if use_proxy:
        proxy_handler = urllib.request.ProxyHandler({
            "http": "socks5://localhost:20170",
            "https": "socks5://localhost:20170",
        })
        return urllib.request.build_opener(proxy_handler)
    return urllib.request.build_opener()


def _try_startpage(query: str, use_proxy: bool) -> list:
    """Single Startpage attempt with delay."""
    mode = "v2raya proxy" if use_proxy else "direct"
    print(f"     \u2192 Startpage {mode}", file=sys.stderr)

    url = f"https://www.startpage.com/sp/search?query={urllib.parse.quote(query)}&num=10"
    opener = _build_opener(use_proxy)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
    )
    try:
        with opener.open(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"       \u26a0\ufe0f Error: {e}", file=sys.stderr)
        return []

    if "captcha" in html.lower()[:5000]:
        print(f"       \u26a0\ufe0f Captcha", file=sys.stderr)
        return []

    # Extract results from Startpage's specific HTML format:
    # <a class="result-title result-link css-xxx" href="URL">
    #   <h2 class="wgl-title css-xxx">TITLE</h2>
    # </a>
    # <p class="description css-xxx">DESCRIPTION</p>
    results = []
    seen_urls = set()

    # Find all result-title links with their href
    for match in re.finditer(
        r'class="result-title result-link[^"]*"\s*href="(https?://[^"]+)".*?<h2[^>]*class="wgl-title[^"]*"[^>]*>(.*?)</h2>',
        html, re.DOTALL
    ):
        url = match.group(1)
        title_html = match.group(2)
        title = re.sub(r'<[^>]+>', '', title_html).strip()

        clean_url = re.sub(r'\?srsltid=.*', '', url)
        if clean_url in seen_urls or len(title) < 5:
            continue
        seen_urls.add(clean_url)
        results.append({
            "title": title,
            "url": clean_url,
            "domain": urllib.parse.urlparse(clean_url).netloc,
        })

    if results:
        print(f"       ✅ {len(results)} results (Google quality)", file=sys.stderr)
        time.sleep(4)
    else:
        print("       ⚠️ No results parsed (Startpage captcha or empty)", file=sys.stderr)

    return results


def startpage_search(query: str) -> list:
    """
    Search via Startpage (Google Search Alliance \u2192 real Google results).
    Returns list of dicts with title/url/domain, or empty on captcha/failure.
    """
    url = f"https://www.startpage.com/sp/search?query={urllib.parse.quote(query)}&num=10"

    for use_proxy in [False, True]:  # try direct first, then proxy
        opener = _build_opener(use_proxy)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with opener.open(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            continue

        # Check if captcha page
        if "captcha" in html.lower()[:5000]:
            print(f"     \u26a0\ufe0f Startpage captcha (proxy={'direct' if not use_proxy else 'v2raya'}), trying next...", file=sys.stderr)
            time.sleep(3)
            continue

        # Extract result URLs
        results = []
        seen_urls = set()
        for match in re.finditer(
            r'class="result-title result-link[^"]*"\s*href="(https?://[^"]+)".*?<h2[^>]*class="wgl-title[^"]*"[^>]*>(.*?)</h2>',
            html, re.DOTALL
        ):
            url = match.group(1)
            title_html = match.group(2)
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            clean_url = re.sub(r'\?srsltid=.*', '', url)
            if clean_url in seen_urls or len(title) < 5:
                continue
            seen_urls.add(clean_url)
            results.append({
                "title": title,
                "url": clean_url,
                "domain": urllib.parse.urlparse(clean_url).netloc,
            })

        if results:
            source = "Startpage-direct" if not use_proxy else "Startpage-v2raya"
            print(f"     \u2705 {source}: {len(results)} results", file=sys.stderr)
            return results

    return []


def jina_search(query: str) -> list:
    """Search DuckDuckGo via Jina Reader proxy (unlimited fallback)."""
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
        if not actual_url or actual_url in seen_urls or "duckduckgo.com" in actual_url:
            continue
        seen_urls.add(actual_url)
        results.append({
            "title": title,
            "url": actual_url,
            "domain": urllib.parse.urlparse(actual_url).netloc,
        })

    return results


def search(query: str, use_google: bool = False) -> list:
    """Search keywords. Default: DDG via Jina (stable, unlimited)."""
    if use_google:
        # Try Startpage (Google quality), fallback to Jina
        for use_proxy in [False, True]:
            sp_results = _try_startpage(query, use_proxy)
            if sp_results:
                return sp_results
            time.sleep(2)
    # Default: DDG via Jina (stable)
    return jina_search(query)


def _try_startpage(query: str, use_proxy: bool) -> list:
    """Single Startpage attempt with delay."""
    mode = "v2raya proxy" if use_proxy else "direct"
    print(f"     → Startpage {mode}", file=sys.stderr)

    url = f"https://www.startpage.com/sp/search?query={urllib.parse.quote(query)}&num=10"
    opener = _build_opener(use_proxy)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
    )
    try:
        with opener.open(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"       ⚠️ Error: {e}", file=sys.stderr)
        return []

    if "captcha" in html.lower()[:5000]:
        print(f"       ⚠️ Captcha", file=sys.stderr)
        return []

    # Extract results
    results = []
    seen_urls = set()
    for match in re.finditer(r'href="(https?://[^"]+)"[^>]*>([^<]+)</a>', html):
        url = match.group(1)
        title = match.group(2).strip()
        clean_url = re.sub(r'\?srsltid=.*', '', url)
        if any(skip in clean_url for skip in
               ['startpage.com', 'cdn.startpage', 'googlead', 'doubleclick',
                'facebook', 'twitter.com']):
            continue
        if clean_url in seen_urls or not clean_url.startswith("http") or len(title) < 5:
            continue
        seen_urls.add(clean_url)
        results.append({
            "title": title,
            "url": clean_url,
            "domain": urllib.parse.urlparse(clean_url).netloc,
        })

    if results:
        print(f"       ✅ {len(results)} results (Google quality)", file=sys.stderr)
        time.sleep(4)  # polite delay between Startpage queries
    return results


# ─── Competition estimation ──────────────────────────────────────────────────

@dataclass
class KeywordResult:
    keyword: str
    intent: str
    country: str
    competition: str = "🟡 Medium"
    source: str = ""
    top_competitors: list = field(default_factory=list)


def estimate_competition_from_serp(serp_results: list) -> str:
    """Estimate competition from actual SERP composition."""
    if not serp_results:
        return "🟡 Medium"

    top10 = serp_results[:10]
    combined = " ".join(r["domain"].lower() + " " + r["title"].lower() for r in top10)

    mfg_kw = ["manufacturer", "factory", "supplier", "made in usa", "made in"]
    mfg_count = sum(1 for r in top10
                    if any(k in (r["domain"] + " " + r["title"]).lower() for k in mfg_kw))

    b2b_domains = ["alibaba", "made-in-china", "globalsources"]
    b2b_count = sum(1 for r in top10 if any(d in r["domain"] for d in b2b_domains))

    if mfg_count >= 3:
        names = [r["domain"] for r in top10[:5]
                 if any(k in (r["domain"] + " " + r["title"]).lower()
                        for k in ["manufacturer", "factory", "made in"])]
        return f"🔴 High ({mfg_count} manufacturers: {', '.join(names[:3])})"
    if b2b_count >= 2:
        return f"🔴 High (B2B platforms dominate)"
    if mfg_count == 0 and b2b_count == 0:
        return "🟢 Low (few direct competitors)"
    return "🟡 Medium (mixed competition)"


def get_top_competitors(serp_results: list, max_n: int = 3) -> list:
    """Classify and label top competitors."""
    competitors = []
    for r in serp_results[:max_n]:
        domain = r["domain"]
        combined = domain.lower() + " " + r["title"].lower()

        if any(d in domain for d in ["alibaba", "made-in-china"]):
            label = "B2B platform"
        elif any(kw in combined for kw in ["manufacturer", "manufacturing", "factory",
                                             "made in usa", "made in the usa"]):
            label = "Manufacturer"
        elif any(d in domain for d in ["amazon", "walmart", "homedepot"]):
            label = "BigBox retail"
        elif ".cn" in domain or "china" in domain:
            label = "China factory"
        elif "tarp" in domain or "tarpaulin" in domain:
            label = "Tarp retailer"
        else:
            label = "Retail/niche"
        competitors.append(f"{domain} ({label})")
    return competitors


# ─── Main discovery loop ─────────────────────────────────────────────────────

def discover_keywords(product: str, countries: list, use_google: bool = False) -> list:
    """Run keyword discovery across all patterns for given countries."""
    all_keywords: list = []
    seen_queries = set()

    for country in countries:
        country_lower = country.strip().lower()
        country_code = country_lower.upper() if country_lower in UPPER_COUNTRY else country_lower
        print(f"  🔍 {country_lower}...", file=sys.stderr)

        for i, pattern in enumerate(SEARCH_PATTERNS):
            query = pattern["template"].format(product=product, country=country_code)
            query_key = f"{country_lower}:{query.lower()}"
            if query_key in seen_queries:
                continue
            seen_queries.add(query_key)

            print(f"    {i+1}/{len(SEARCH_PATTERNS)}: `{query}`", file=sys.stderr)
            serp_results = search(query, use_google=use_google)

            competition = estimate_competition_from_serp(serp_results)
            competitors = get_top_competitors(serp_results) if serp_results else []

            # Determine source label
            source = "Google (Startpage)" if serp_results and any(
                s in str(serp_results[0]) for s in ["Startpage"]) else "DDG (Jina)"

            kw = KeywordResult(
                keyword=query,
                intent=pattern["intent"],
                country=country_lower,
                competition=competition,
                source=source,
                top_competitors=competitors,
            )
            all_keywords.append(kw)

            time.sleep(0.5)

    return all_keywords


# ─── Output ──────────────────────────────────────────────────────────────────

def print_table(keywords: list, product: str, countries_str: str, output_file: Optional[str] = None):
    """Render keyword results as markdown."""
    lines = []
    lines.append("# SEO Keyword Discovery Results\n")
    lines.append(f"**Product:** {product}  ")
    lines.append(f"**Countries:** {countries_str}  ")
    lines.append(f"**Total keywords found:** {len(keywords)}\n")
    lines.append(f"**Note:** First 3 queries use Startpage (Google results), remaining use DDG via Jina.  \n")

    by_country = defaultdict(list)
    for kw in keywords:
        by_country[kw.country].append(kw)

    for country in sorted(by_country.keys()):
        country_kws = by_country[country]
        google_count = sum(1 for k in country_kws if "Google" in k.source)
        lines.append(f"## {country.upper()} — {len(country_kws)} Keywords ({google_count} from Google)\n")
        lines.append("| # | Keyword | Intent | Competition | Source | Top Competitors |")
        lines.append("|---|---------|--------|:-----------:|:------:|:---------------:|")
        for i, kw in enumerate(country_kws, 1):
            source_icon = "🟢" if "Google" in kw.source else "🟡"
            comps = ", ".join(kw.top_competitors[:2]) if kw.top_competitors else "-"
            lines.append(f"| {i} | `{kw.keyword}` | {kw.intent} | {kw.competition} | {source_icon} | {comps} |")
        lines.append("")

    lines.append("## Summary\n")
    lines.append("| Country | Keywords | Google-sourced |")
    lines.append("|---------|:--------:|:--------------:|")
    for country in sorted(by_country.keys()):
        kws = by_country[country]
        gc = sum(1 for k in kws if "Google" in k.source)
        lines.append(f"| {country.upper()} | {len(kws)} | {gc} |")

    output = "\n".join(lines)
    if output_file:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w") as f:
            f.write(output)
        print(f"\n✅ Written to {output_file}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    parser = ArgumentParser(description="SEO keyword discovery (multi-source)")
    parser.add_argument("--product", required=True, help="Product name")
    parser.add_argument("--countries", default="us", help="Comma-separated country codes")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--google", action="store_true",
                        help="Try Startpage for Google-quality results (may hit captcha)")
    args = parser.parse_args()

    countries = [c.strip() for c in args.countries.split(",") if c.strip()]
    if not countries:
        print("❌ No valid countries", file=sys.stderr)
        sys.exit(1)

    print(f"🔄 Discovering keywords for: {args.product}", file=sys.stderr)
    print(f"   Target markets: {', '.join(countries)}", file=sys.stderr)
    if args.google:
        print(f"   Sources: Startpage (Google) + DDG via Jina (fallback)", file=sys.stderr)
    else:
        print(f"   Sources: DuckDuckGo via Jina Reader (stable)", file=sys.stderr)
    print("", file=sys.stderr)

    results = discover_keywords(args.product, countries, use_google=args.google)

    if not results:
        print("\n⚠️  No keywords found.", file=sys.stderr)
        sys.exit(1)

    print_table(results, args.product, args.countries, args.output)
