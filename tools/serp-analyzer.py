#!/usr/bin/env python3
"""
SERP Analyzer — SEO competition analysis via Jina Reader proxy.
Zero external dependencies (stdlib only).

Searches DuckDuckGo through Jina Reader (bypasses IP-based anti-bot),
classifies competitors by type, and optionally reads competitor pages
for deep content analysis.

Usage:
  python3 tools/serp-analyzer.py --keyword "heavy duty tarp manufacturer usa" --country us
  python3 tools/serp-analyzer.py --keyword "tarp supplier canada" --country ca --output /tmp/serp.md
  python3 tools/serp-analyzer.py --input /tmp/kws.md  # batch mode
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
        """Classify the result by domain type for SEO competition analysis."""
        domain_lower = self.domain.lower()
        url_lower = self.url.lower()

        if any(d in domain_lower for d in ["alibaba", "made-in-china", "globalsources",
                                             "indiamart", "tradeindia", "ecplaza"]):
            self.type_icon = "🌐"
            self.type_label = "B2B Platform"
            self.origin = "Global"
            self.difficulty = "🟡 Medium"
        elif any(d in domain_lower for d in ["amazon", "walmart", "homedepot", "lowes",
                                               "costco", "wayfair", "etsy", "ebay"]):
            self.type_icon = "🛍️"
            self.type_label = "BigBox Retailer"
            self.origin = "Global"
            self.difficulty = "🟢 Low (B2C, not direct comp)"
        elif ".cn" in domain_lower or "china" in domain_lower:
            self.type_icon = "🏭"
            self.type_label = "China Factory Site"
            self.origin = "🇨🇳 China"
            self.difficulty = "🟡 Medium"
        elif any(kw in url_lower for kw in ["manufacturer", "factory", "supplier", "producer"]):
            self.type_icon = "🏭"
            self.type_label = "Manufacturer"
            self.origin = "Local/Other"
            self.difficulty = "🔴 Hard (established domain)"
        elif any(d in domain_lower for d in ["blog", "review", "medium", "substack"]):
            self.type_icon = "📝"
            self.type_label = "Blog/Review"
            self.origin = "Global"
            self.difficulty = "🟡 Medium"
        elif any(d in domain_lower for d in ["wikipedia", "wikihow"]):
            self.type_icon = "📖"
            self.type_label = "Encyclopedia"
            self.origin = "Global"
            self.difficulty = "🟢 Low (beat with product page)"
        elif any(d in domain_lower for d in ["news", "cnn", "bbc", "reuters"]):
            self.type_icon = "📰"
            self.type_label = "News"
            self.origin = "Global"
            self.difficulty = "🟢 Low (ephemeral)"
        elif any(kw in url_lower for kw in ["industry", "trade", "directory", "export"]):
            self.type_icon = "🏪"
            self.type_label = "Industry/Trade Site"
            self.origin = "Global"
            self.difficulty = "🟡 Medium"
        else:
            self.type_icon = "🏪"
            self.type_label = "Niche/Other"
            self.origin = "Local/Unknown"
            self.difficulty = "🟡 Medium"


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

    # Parse DDG's markdown output from Jina
    # Pattern: N.[Title](DDG-redirect-url) followed by description and domain
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

        # Extract description between this link and the next
        num = match.group(1)
        desc_pattern = num + r'\.\s*\[[^\]]+\]\([^)]+\)\s*\n(.*?)(?:\n\d+\.\s*\[|\Z)'
        desc_match = re.search(desc_pattern, content, re.DOTALL)
        description = ""
        if desc_match:
            raw = desc_match.group(1).strip()
            lines = [l for l in raw.split('\n') if l.strip()]
            # Remove trailing domain if present
            if lines and '.' in lines[-1] and ' ' not in lines[-1].strip():
                lines = lines[:-1]
            description = ' '.join(lines[:3])[:250]

        results.append({
            "title": title,
            "url": actual_url,
            "domain": urllib.parse.urlparse(actual_url).netloc,
            "description": description,
        })

    return results


def read_page_content(url: str) -> str:
    """Read a competitor page via Jina Reader to analyze content strategy."""
    proxy_url = f"https://r.jina.ai/{urllib.parse.quote(url, safe='')}"
    req = urllib.request.Request(
        proxy_url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "text/plain"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def guess_origin(domain: str) -> str:
    """Heuristic origin from domain."""
    d = domain.lower()
    tld = domain.split(".")[-1] if "." in domain else ""

    cn_indicators = [".cn", "china", "alibaba", "made-in-china"]
    if any(ind in d for ind in cn_indicators):
        return "🇨🇳 China"

    tld_map = {
        "uk": "🇬🇧 UK", "ca": "🇨🇦 Canada", "au": "🇦🇺 Australia",
        "nz": "🇳🇿 NZ", "de": "🇩🇪 Germany", "fr": "🇫🇷 France",
        "ae": "🇦🇪 UAE", "sa": "🇸🇦 Saudi", "in": "🇮🇳 India",
        "jp": "🇯🇵 Japan", "sg": "🇸🇬 Singapore",
    }
    return tld_map.get(tld, "Global/Unknown")


def analyze_serp(keyword: str, country: str = "us") -> dict:
    """Full SERP analysis for one keyword."""
    query = f"{keyword}"
    print(f"   Searching: {query}", file=sys.stderr)
    results = jina_search(query)

    if not results:
        return {
            "keyword": keyword,
            "country": country,
            "results": [],
            "summary": {"total": 0, "china_share": "0/0", "b2b_platforms": 0,
                       "manufacturers": 0, "easy_to_beat": 0,
                       "difficulty_assessment": "⚠️ No SERP data"},
        }

    serp_results = []
    for i, r in enumerate(results[:10], 1):
        sr = SERPResult(
            rank=i,
            title=r["title"],
            url=r["url"],
            domain=r["domain"],
        )
        sr.classify()
        serp_results.append(sr)

    # Summarize
    total = len(serp_results)
    china_count = sum(1 for r in serp_results if "China" in r.origin)
    b2b_platforms = sum(1 for r in serp_results if "B2B Platform" in r.type_label)
    manufacturers = sum(1 for r in serp_results if "Manufacturer" in r.type_label or "Factory" in r.type_label)
    easy_to_beat = sum(1 for r in serp_results if "Low" in r.difficulty)

    if manufacturers >= 4:
        difficulty = "🔴 High (manufacturers dominate)"
    elif b2b_platforms >= 4:
        difficulty = "🔴 High (B2B platform oligopoly)"
    elif easy_to_beat >= 4:
        difficulty = "🟢 Low (beatable competition)"
    else:
        difficulty = "🟡 Medium (mixed)"

    return {
        "keyword": keyword,
        "country": country,
        "results": serp_results,
        "summary": {
            "total": total,
            "china_share": f"{china_count}/{total} ({china_count/total*100:.0f}%)" if total else "0/0",
            "b2b_platforms": b2b_platforms,
            "manufacturers": manufacturers,
            "easy_to_beat": easy_to_beat,
            "difficulty_assessment": difficulty,
        }
    }


def print_report(analyses: list, output_file: Optional[str] = None):
    """Render SERP analysis as markdown."""
    lines = []
    lines.append("# SERP Competition Analysis\n")
    lines.append(f"**Data source:** DuckDuckGo (via Jina Reader proxy)\n")

    for analysis in analyses:
        kw = analysis["keyword"]
        country = analysis["country"]
        summary = analysis["summary"]
        results = analysis["results"]

        lines.append(f"## Keyword: `{kw}` — {country.upper()}\n")
        lines.append(f"**Difficulty:** {summary['difficulty_assessment']}  ")
        lines.append(f"**Chinese supplier share:** {summary['china_share']}  ")
        lines.append(f"**B2B platforms:** {summary['b2b_platforms']}  ")
        lines.append(f"**Manufacturers/Factories:** {summary['manufacturers']}  ")
        lines.append(f"**Beatable (Low diff):** {summary['easy_to_beat']}\n")

        if not results:
            lines.append("_No SERP data available._\n")
            continue

        lines.append("| Rank | Type | Domain | Title | Difficulty |")
        lines.append("|:----:|:----:|--------|-------|:----------:|")
        for r in results:
            short_title = r.title[:50] + "..." if len(r.title) > 50 else r.title
            lines.append(f"| {r.rank} | {r.type_icon} {r.type_label} | {r.domain} | {short_title} | {r.difficulty} |")
        lines.append("")

    # Cross-keyword summary
    if len(analyses) > 1:
        lines.append("## Cross-Keyword Summary\n")
        lines.append("| Keyword | Difficulty | China Share | B2B Plat. | Mfg | Beatable |")
        lines.append("|---------|:----------:|:-----------:|:---------:|:---:|:--------:|")
        for a in analyses:
            s = a["summary"]
            lines.append(f"| `{a['keyword'][:45]}` | {s['difficulty_assessment'][:20]} | {s['china_share']} | {s['b2b_platforms']} | {s['manufacturers']} | {s['easy_to_beat']} |")

    output = "\n".join(lines)

    if output_file:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w") as f:
            f.write(output)
        print(f"\n✅ Written to {output_file}", file=sys.stderr)
    else:
        print(output)


def parse_keywords_from_file(path: str) -> list:
    """Extract keywords from keyword-finder.py output (markdown table)."""
    with open(path) as f:
        content = f.read()
    keywords = []
    for line in content.split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 5:
            kw = parts[2].strip()
            if kw and not kw.startswith("Keyword") and not kw.startswith("---") and len(kw) > 3:
                keywords.append(kw)
    return keywords


if __name__ == "__main__":
    parser = ArgumentParser(description="SERP competition analysis (Jina proxy)")
    parser.add_argument("--keyword", help="Keyword to analyze")
    parser.add_argument("--country", default="us", help="Target country code")
    parser.add_argument("--input", help="File with keywords (batch mode)")
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    if args.input:
        print(f"🔄 Batch mode: reading keywords from {args.input}", file=sys.stderr)
        keywords = parse_keywords_from_file(args.input)[:5]
        print(f"   Found {len(keywords)} keywords", file=sys.stderr)
    elif args.keyword:
        keywords = [args.keyword]
    else:
        print("❌ Provide --keyword or --input", file=sys.stderr)
        sys.exit(1)

    analyses = []
    for i, kw in enumerate(keywords):
        if i > 0:
            time.sleep(1)
        result = analyze_serp(kw, args.country)
        analyses.append(result)
        print(f"   ✅ {i+1}/{len(keywords)}", file=sys.stderr)

    print_report(analyses, args.output)
