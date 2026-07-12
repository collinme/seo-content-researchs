#!/usr/bin/env python3
"""
SERP Analyzer — SEO competition analysis for international markets.
Zero external dependencies (stdlib only).

Analyzes top search results for a given keyword + country, classifies
competitor types, and assesses ranking difficulty.

Usage:
  python3 tools/serp-analyzer.py --keyword "pvc tarpaulin manufacturer usa" --country us
  python3 tools/serp-analyzer.py --keyword "heavy duty tarp supplier canada" --country ca --output /tmp/serp.md
  python3 tools/serp-analyzer.py --input /tmp/kws.md  # batch mode: read keywords from file
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from argparse import ArgumentParser
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Optional


@dataclass
class SERPResult:
    rank: int
    title: str
    url: str
    domain: str
    type_icon: str = ""
    type_label: str = ""
    origin: str = ""
    difficulty: str = ""

    def classify(self):
        """Classify the result by domain type."""
        domain_lower = self.domain.lower()
        url_lower = self.url.lower()

        # B2B platforms
        if any(d in domain_lower for d in ["alibaba", "made-in-china", "globalsources", "tradeindia",
                                             "ecplaza", "indiamart", "exportersindia", "go4worldbusiness"]):
            self.type_icon = "\U0001f310"
            self.type_label = "B2B Platform"
            self.origin = "Global"
            self.difficulty = "\U0001f7e1 Medium \u2014 beatable with indep. site"
        # Big retailers / marketplace
        elif any(d in domain_lower for d in ["amazon", "walmart", "homedepot", "lowes", "costco",
                                               "wayfair", "etsy", "ebay"]):
            self.type_icon = "\U0001f6cd\ufe0f"
            self.type_label = "BigBox Retailer"
            self.origin = "Global"
            self.difficulty = "\U0001f7e2 Low \u2014 targets B2C, not direct comp"
        # China factory sites (indep.)
        elif any(d in domain_lower for d in [".cn", "china", "-china"]):
            self.type_icon = "\U0001f3ed"
            self.type_label = "Factory Site"
            self.origin = "\U0001f1e8\U0001f1f3 China"
            self.difficulty = "\U0001f534 Hard \u2014 well-optimized factory site"
        # Non-China manufacturers
        elif any(kw in url_lower for kw in ["manufacturer", "factory", "supplier", "producer"]):
            self.type_icon = "\U0001f3ed"
            self.type_label = "Manufacturer"
            self.origin = "Local/Other"
            self.difficulty = "\U0001f534 Hard \u2014 established domain"
        # Blog / review sites
        elif any(d in domain_lower for d in ["blog", "review", "medium", "substack"]):
            self.type_icon = "\U0001f4dd"
            self.type_label = "Blog/Review"
            self.origin = "Global"
            self.difficulty = "\U0001f7e1 Medium"
        # Guides / encyclopedias
        elif any(d in domain_lower for d in ["wikipedia", "wikihow", "howto", "guide"]):
            self.type_icon = "\U0001f4d6"
            self.type_label = "Encyclopedia/Guide"
            self.origin = "Global"
            self.difficulty = "\U0001f7e2 Low \u2014 beat with product page"
        # News
        elif any(d in domain_lower for d in ["news", "cnn", "bbc", "reuters", "bloomberg"]):
            self.type_icon = "\U0001f4f0"
            self.type_label = "News"
            self.origin = "Global"
            self.difficulty = "\U0001f7e2 Low \u2014 ephemeral content"
        # Niche industry / trade
        elif any(kw in url_lower for kw in ["industry", "trade", "directory", "export", "import"]):
            self.type_icon = "\U0001f3ea"
            self.type_label = "Industry/Trade Site"
            self.origin = "Global"
            self.difficulty = "\U0001f7e1 Medium"
        else:
            self.type_icon = "\U0001f3ea"
            self.type_label = "Niche Site"
            self.origin = "Local/Unknown"
            self.difficulty = "\U0001f7e1 Medium"


class BingSERPParser(HTMLParser):
    """Parse Bing SERP page for organic results."""
    def __init__(self):
        super().__init__()
        self.results = []
        self._current = {}
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "a" and "href" in attrs_dict:
            href = attrs_dict["href"]
            if href.startswith("http") and "bing.com" not in href:
                self._current = {"url": href, "title": ""}
                self._in_title = True

    def handle_data(self, data):
        if self._in_title:
            self._current["title"] = (self._current.get("title", "") + data).strip()

    def handle_endtag(self, tag):
        if tag == "a" and self._in_title:
            self._in_title = False
            if self._current.get("title") and self._current.get("url"):
                self.results.append(self._current)
            self._current = {}


def search_bing_serp(keyword: str, country: str = "us") -> list:
    """Fetch Bing SERP for a keyword-country pair."""
    mkt_map = {
        "us": "en-US", "ca": "en-CA", "uk": "en-GB", "au": "en-AU",
        "nz": "en-NZ", "de": "de-DE", "fr": "fr-FR", "nl": "nl-NL",
        "ae": "en-AE", "sa": "en-SA", "sg": "en-SG",
    }
    mkt = mkt_map.get(country, "en-US")
    url = f"https://www.bing.com/search?q={urllib.parse.quote(keyword)}&mkt={mkt}&count=10"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"   \u26a0\ufe0f  Bing search failed: {e}", file=sys.stderr)
        return []

    parser = BingSERPParser()
    parser.feed(html)

    results = []
    seen_urls = set()
    rank = 0

    for r in parser.results:
        url = r.get("url", "")
        url_key = re.sub(r'https?://', '', url).rstrip('/')
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)

        rank += 1
        domain = urllib.parse.urlparse(url).netloc

        serp = SERPResult(
            rank=rank,
            title=r.get("title", "").strip(),
            url=url,
            domain=domain,
        )
        serp.classify()
        results.append(serp)

        if rank >= 10:
            break

    return results


def guess_country_origin(domain: str) -> str:
    """Heuristic to guess site origin from domain."""
    domain_lower = domain.lower()
    tld = domain.split(".")[-1] if "." in domain else ""

    country_tlds = {
        "cn": "\U0001f1e8\U0001f1f3 China", "uk": "\U0001f1ec\U0001f1e7 UK", "de": "\U0001f1e9\U0001f1ea Germany",
        "fr": "\U0001f1eb\U0001f1f7 France", "au": "\U0001f1e6\U0001f1fa Australia", "ca": "\U0001f1e8\U0001f1e6 Canada",
        "in": "\U0001f1ee\U0001f1f3 India", "ae": "\U0001f1e6\U0001f1ea UAE", "sa": "\U0001f1f8\U0001f1e6 Saudi",
        "jp": "\U0001f1ef\U0001f1f5 Japan", "sg": "\U0001f1f8\U0001f1ec Singapore", "nz": "\U0001f1f3\U0001f1ff NZ",
        "nl": "\U0001f1f3\U0001f1f1 Netherlands", "it": "\U0001f1ee\U0001f1f9 Italy", "es": "\U0001f1ea\U0001f1f8 Spain",
        "br": "\U0001f1e7\U0001f1f7 Brazil", "ru": "\U0001f1f7\U0001f1fa Russia", "kr": "\U0001f1f0\U0001f1f7 Korea",
        "com": "Global",
    }

    if ".cn" in domain_lower or "china" in domain_lower:
        return "\U0001f1e8\U0001f1f3 China"
    if "alibaba" in domain_lower or "made-in-china" in domain_lower:
        return "\U0001f1e8\U0001f1f3 China (B2B platform)"

    return country_tlds.get(tld, "Global/Unknown")


def analyze_serp(keyword: str, country: str) -> dict:
    """Full SERP analysis for one keyword + country."""
    print(f"   Fetching SERP for: {keyword}", file=sys.stderr)
    results = search_bing_serp(keyword, country)

    if not results:
        return {
            "keyword": keyword,
            "country": country,
            "results": [],
            "summary": {
                "total": 0,
                "china_share": 0,
                "b2b_platforms": 0,
                "difficulty_assessment": "\u26a0\ufe0f No data",
            }
        }

    total = len(results)
    china_count = sum(1 for r in results if "China" in r.origin)
    b2b_platforms = sum(1 for r in results if "B2B Platform" in r.type_label)
    manufacturer_count = sum(1 for r in results if "Manufacturer" in r.type_label or "Factory" in r.type_label)
    easy_to_beat = sum(1 for r in results if "Low" in r.difficulty)

    if manufacturer_count >= 4:
        difficulty = "\U0001f534 High \u2014 established manufacturers dominate"
    elif b2b_platforms >= 4:
        difficulty = "\U0001f534 High \u2014 B2B platform oligopoly"
    elif easy_to_beat >= 4:
        difficulty = "\U0001f7e2 Low \u2014 lots of beatable competition"
    else:
        difficulty = "\U0001f7e1 Medium \u2014 mix of competitors"

    return {
        "keyword": keyword,
        "country": country,
        "results": results,
        "summary": {
            "total": total,
            "china_share": f"{china_count}/{total} ({china_count/total*100:.0f}%)" if total else "0/0",
            "b2b_platforms": b2b_platforms,
            "manufacturers": manufacturer_count,
            "easy_to_beat": easy_to_beat,
            "difficulty_assessment": difficulty,
        }
    }


def print_serp_report(analyses: list, output_file: Optional[str] = None):
    """Render SERP analysis as markdown."""
    lines = []
    lines.append("# SERP Competition Analysis\n")

    for analysis in analyses:
        kw = analysis["keyword"]
        country = analysis["country"]
        summary = analysis["summary"]
        results = analysis["results"]

        lines.append(f"## Keyword: `{kw}` \u2014 {country.upper()}\n")
        lines.append(f"**Difficulty:** {summary['difficulty_assessment']}  ")
        lines.append(f"**Chinese supplier share:** {summary['china_share']}  ")
        lines.append(f"**B2B platforms:** {summary['b2b_platforms']}  ")
        lines.append(f"**Manufacturers:** {summary['manufacturers']}  ")
        lines.append(f"**Beatable (Low diff):** {summary['easy_to_beat']}\n")

        if not results:
            lines.append("_No SERP data available._\n")
            continue

        lines.append("| Rank | Type | Domain | Origin | Difficulty |")
        lines.append("|:----:|:----:|--------|:------:|:----------:|")
        for r in results:
            lines.append(f"| {r.rank} | {r.type_icon} {r.type_label} | {r.domain} | {r.origin} | {r.difficulty} |")

        lines.append("")

    lines.append("## Cross-Keyword Summary\n")
    lines.append("| Keyword | Country | Difficulty | China Share | B2B Plat. | Beatable |")
    lines.append("|---------|:------:|:----------:|:-----------:|:---------:|:--------:|")
    for a in analyses:
        s = a["summary"]
        lines.append(f"| `{a['keyword'][:50]}...` | {a['country'].upper()} | {s['difficulty_assessment'][:20]} | {s['china_share']} | {s['b2b_platforms']} | {s['easy_to_beat']} |")

    output = "\n".join(lines)

    if output_file:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w") as f:
            f.write(output)
        print(f"\n\u2705 Written to {output_file}", file=sys.stderr)
    else:
        print(output)


def parse_keywords_from_file(path: str) -> list:
    """Parse keyword list from a markdown file (generated by keyword-finder.py)."""
    with open(path) as f:
        content = f.read()

    keywords = []
    for line in content.split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 5:
            kw = parts[2].strip() if len(parts) > 2 else ""
            if kw and not kw.startswith("Keyword") and not kw.startswith("---") and len(kw) > 3:
                keywords.append(kw)

    return keywords


if __name__ == "__main__":
    parser = ArgumentParser(description="SERP competition analysis")
    parser.add_argument("--keyword", help="Keyword to analyze")
    parser.add_argument("--country", default="us", help="Target country code")
    parser.add_argument("--input", help="File with keywords (batch mode)")
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    if args.input:
        print(f"\U0001f504 Batch mode: reading keywords from {args.input}", file=sys.stderr)
        keywords = parse_keywords_from_file(args.input)
        keywords = keywords[:5]
        print(f"   Found {len(keywords)} keywords to analyze", file=sys.stderr)
    elif args.keyword:
        keywords = [args.keyword]
    else:
        print("\u274c Provide --keyword or --input", file=sys.stderr)
        sys.exit(1)

    analyses = []
    for i, kw in enumerate(keywords):
        if i > 0:
            time.sleep(0.5)
        result = analyze_serp(kw, args.country)
        analyses.append(result)
        print(f"   \u2705 {i+1}/{len(keywords)}", file=sys.stderr)

    print_serp_report(analyses, args.output)
