#!/usr/bin/env python3
"""
Competitor Research — Fetches competitor pages via Jina Reader,
analyzes content structure, identifies gaps for differentiation.
Zero external dependencies (stdlib only).

Usage:
  python3 tools/competitor-research.py --keyword "china tarp manufacturer" --urls "https://derflex.com,https://tarpsfactory.com"
  python3 tools/competitor-research.py --keyword "china tarp manufacturer" --serp /tmp/serp.md --output /tmp/gaps.md
"""

import os
import re
import sys
import urllib.parse
import urllib.request
from argparse import ArgumentParser
from typing import Optional


def jina_read(url: str) -> str:
    """Fetch page content via Jina Reader."""
    proxy_url = f"https://r.jina.ai/{urllib.parse.quote(url, safe='')}"
    req = urllib.request.Request(
        proxy_url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "text/plain"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"ERROR: {e}"


def extract_urls_from_serp(serp_path: str) -> list:
    """Extract competitor URLs from SERP analysis markdown."""
    urls = []
    with open(serp_path) as f:
        for line in f:
            # Match table rows with URLs
            m = re.match(r'\|\s*\d+\s*\|\s*[^\|]+\|\s*([^\s|]+)', line)
            if m:
                domain = m.group(1).strip()
                if domain and domain != 'Domain' and '.' in domain:
                    urls.append(f"https://{domain}")
    return urls[:4]  # top 4 competitors


def analyze_content(content: str, max_words: int = 300) -> dict:
    """Analyze a competitor page: extract H2s, topics, word count."""
    if content.startswith("ERROR:"):
        return {"error": content, "h2s": [], "topics": [], "word_count": 0}

    # Extract H2 headings
    h2s = re.findall(r'##\s+(.+?)(?:\n|$)', content)
    h2s = [h.strip() for h in h2s if h.strip()]

    # Count words (rough)
    words = len(content.split())

    # Extract topic keywords
    topics = []
    topic_signals = ["manufacturer", "factory", "quality", "price", "shipping",
                     "custom", "MOQ", "lead time", "certification", "PVC", "PE",
                     "wholesale", "OEM", "sample", "warranty", "china"]
    for signal in topic_signals:
        count = content.lower().count(signal)
        if count >= 2:
            topics.append(f"{signal} ({count}x)")

    # Summary (first meaningful paragraph)
    summary = ""
    for line in content.split('\n'):
        clean = line.strip()
        if clean and len(clean) > 80 and not clean.startswith('#') and not clean.startswith('[') and not clean.startswith('!'):
            summary = clean[:max_words]
            break

    return {
        "h2s": h2s,
        "topics": topics,
        "word_count": words,
        "summary": summary,
    }


def generate_gap_report(keyword: str, analyses: list) -> str:
    """Generate content gap analysis from competitor pages."""
    lines = []
    lines.append(f"## Content Gap Analysis: `{keyword}`\n")

    if not analyses:
        lines.append("_No competitor pages analyzed._\n")
        return "\n".join(lines)

    # Collect all H2s across competitors
    all_h2s = []
    for a in analyses:
        all_h2s.extend(a.get("h2s", []))
    all_h2s = list(set(all_h2s))  # deduplicate

    # Collect all topics
    all_topics = {}
    for a in analyses:
        for t in a.get("topics", []):
            topic_name = t.split(" (")[0]
            count = int(re.search(r'\((\d+)x\)', t).group(1)) if re.search(r'\((\d+)x\)', t) else 1
            all_topics[topic_name] = all_topics.get(topic_name, 0) + count

    # Sort topics by frequency
    sorted_topics = sorted(all_topics.items(), key=lambda x: -x[1])

    # H2 gap analysis
    lines.append("### Competitor H2 Coverage\n")
    lines.append("| # | H2 Heading | Covered by |")
    lines.append("|---|-----------|:----------:|")
    for i, h2 in enumerate(all_h2s[:15], 1):
        covered_by = []
        for j, a in enumerate(analyses):
            if h2 in a.get("h2s", []):
                covered_by.append(f"C{j+1}")
        coverage = ", ".join(covered_by) if covered_by else "❌ No one"
        lines.append(f"| {i} | {h2[:50]} | {coverage} |")
    lines.append("")

    # Topic frequency
    lines.append("### Topic Frequency\n")
    lines.append("| Topic | Occurrences | Saturation |")
    lines.append("|-------|:-----------:|:----------:|")
    for topic, count in sorted_topics[:10]:
        if count >= len(analyses) * 2:
            saturation = "🔴 High — saturated"
        elif count >= len(analyses):
            saturation = "🟡 Medium"
        else:
            saturation = "🟢 Low — differentiator"
        lines.append(f"| {topic} | {count} | {saturation} |")
    lines.append("")

    # Top competitor overview
    lines.append("### Competitor Overview\n")
    for i, a in enumerate(analyses, 1):
        wc = a.get("word_count", 0)
        summary = a.get("summary", "")[:200]
        lines.append(f"**C{i}:** ~{wc} words  ")
        if summary:
            lines.append(f"_{summary}_  ")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = ArgumentParser(description="Research competitor pages for gap analysis")
    parser.add_argument("--keyword", required=True, help="Target keyword")
    parser.add_argument("--urls", help="Comma-separated competitor URLs")
    parser.add_argument("--serp", help="SERP analysis markdown file (to extract URLs)")
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    # Get competitor URLs
    urls = []
    if args.urls:
        urls = [u.strip() for u in args.urls.split(",") if u.strip()]
    elif args.serp:
        urls = extract_urls_from_serp(args.serp)
        print(f"🔍 Extracted {len(urls)} competitor URLs from SERP", file=sys.stderr)

    if not urls:
        print("⚠️  No competitor URLs found. Provide --urls or --serp", file=sys.stderr)
        sys.exit(0)

    # Fetch and analyze each competitor
    analyses = []
    for url in urls:
        print(f"   Reading: {url}", file=sys.stderr)
        content = jina_read(url)
        analysis = analyze_content(content)
        analyses.append(analysis)
        wc = analysis.get("word_count", 0)
        h2_count = len(analysis.get("h2s", []))
        print(f"   → {wc} words, {h2_count} H2s", file=sys.stderr)

    # Generate gap report
    report = generate_gap_report(args.keyword, analyses)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\n✅ Gap analysis written to {args.output}", file=sys.stderr)
    else:
        print(report)

    # Also print quick stats to stderr
    print(f"\n📊 Summary:", file=sys.stderr)
    for i, a in enumerate(analyses, 1):
        wc = a.get("word_count", 0)
        topics = a.get("topics", [])[:5]
        print(f"   C{i}: ~{wc}w | Topics: {', '.join(topics)}", file=sys.stderr)
