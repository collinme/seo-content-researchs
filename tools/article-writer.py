#!/usr/bin/env python3
"""
Article Writer — Combines content brief + SEO data into a writing prompt
that a human (or Hermes agent) can use to produce the final article.

Usage:
  python3 tools/article-writer.py --keyword "china tarp manufacturer" --country us
                                  --brief /tmp/brief.md --seo /tmp/optimize.md
                                  --output /tmp/writing-prompt.md
"""

import os
import re
import sys
from argparse import ArgumentParser
from typing import Optional


def read_file_safe(path: str) -> str:
    """Read file, return empty string if missing."""
    if path and os.path.exists(path):
        with open(path) as f:
            return f.read()
    return ""


def extract_h2_structure(brief_content: str) -> list:
    """Extract H2 headings from the content brief."""
    h2s = []
    for line in brief_content.split('\n'):
        # Match "N. **H2 Title** — rationale"
        m = re.match(r'\s*\d+\.\s*\*\*(.+?)\*\*', line)
        if m:
            h2s.append(m.group(1).strip())
    return h2s


def extract_competitors(serp_content: str, max_n: int = 3) -> list:
    """Extract top competitor domains from SERP analysis."""
    domains = []
    for line in serp_content.split('\n'):
        m = re.match(r'\|\s*\d+\s*\|\s*[🏪🌐🛍️🏭📖📰📝]+\s*[^|]*\|\s*([^\s|]+)', line)
        if m:
            domain = m.group(1).strip()
            if domain not in domains and domain != 'Domain':
                domains.append(domain)
    return domains[:max_n]


def generate_writing_prompt(keyword: str, country: str,
                             brief_content: str, seo_content: str,
                             serp_content: str = "",
                             competitor_pages: list = None) -> str:
    """Generate a structured writing prompt for article production."""

    country_name = {"us": "USA", "ca": "Canada", "uk": "UK", "au": "Australia",
                    "nz": "New Zealand", "ae": "UAE"}.get(country, country.upper())

    # Extract structure
    h2s = extract_h2_structure(brief_content)
    competitors = extract_competitors(serp_content)

    lines = []
    lines.append(f"""# Writing Prompt: Article for `{keyword}`

## Role
You are an expert SEO content writer specialized in B2B manufacturing content. You write for a Chinese factory that exports heavy duty tarps to international markets. Your tone is professional, factual, and persuasive — like an experienced export sales manager writing to potential buyers.

## Task
Write a complete, publication-ready article targeting the keyword **`{keyword}`** for the **{country_name}** market.

## Title
Choose the best title from these options, or write something better:
""")

    # Extract titles from brief
    in_title = False
    title_count = 0
    for line in brief_content.split('\n'):
        if '## Title Suggestion' in line:
            in_title = True
            continue
        if in_title and line.strip().startswith(str(title_count + 1) + '.'):
            title_count += 1
            lines.append(f"{title_count}. {line.strip()}")
            if title_count >= 3:
                break
        elif in_title and line.strip() == '':
            break

    lines.append(f"""
## Article Structure
Write approximately 1500-2500 words with the following H2 sections:
""")

    for i, h2 in enumerate(h2s, 1):
        lines.append(f"{i}. **{h2}**")

    lines.append(f"""
## Content Requirements

### 1. Opening (First 100 words)
- Hook the reader immediately — state the problem/pain point
- Include the primary keyword naturally
- Promise value: "In this guide, you will learn..."

### 2. Each H2 Section
- Start with a strong sub-header question or assertion
- Include 1 specific data point or example per section
- End section with a transition to the next

### 3. Closing (CTA)
- Summarize key takeaways (2-3 bullet points)
- Clear call to action: "Contact us for a quote" / "Request a sample"
- Include contact information naturally

## Writing Style Rules
- Write in **first-person plural** ("we", "our factory", "our team")
- Use **short paragraphs** (2-4 sentences max)
- Vary sentence length — mix short punchy sentences with longer explanations
- Add **1-2 personal observations** per 500 words ("In our 15 years of exporting to the US, we have found that...")
- Use industry terminology naturally (MOQ, FOB, CIF, lead time, UV resistance, GSM, etc.)
- **NO bullet points or numbered lists longer than 3 items** — convert to prose
- **NO emoji prefixes** — write naturally
- **NO "furthermore", "moreover", "in conclusion"** — sound human

## EEAT Signals to Embed
""")

    # Extract EEAT signals from SEO content
    for line in seo_content.split('\n'):
        if '✅' in line and ('About' in line or 'Contact' in line or '客户' in line or
                              'Factory' in line or 'ISO' in line or 'certification' in line or
                              'case' in line or 'photo' in line):
            lines.append(f"- Incorporate: {line.replace('✅', '').strip()}")

    if competitors:
        lines.append(f"""
## Competitors to Outrank
Your article must be more comprehensive and more trustworthy than:
""")
    for c in competitors:
        lines.append(f"- {c}")

    # Add content gap analysis
    if gaps and len(gaps) > 100:
        lines.append(f"""
### Content Gaps to Exploit

Based on analysis of actual competitor pages (word counts, topics covered, H2 structures):

{gaps}

Use these gaps to differentiate your article. If competitors are all thin on shipping details, go deep on that. If they lack EEAT signals, add factory specifics.
""")

    lines.append(f"""
## AI Detection Avoidance (CRITICAL)
- This article will be manually reviewed. Make it pass as human-written.
- Do NOT start every paragraph the same way
- Do NOT use transitional phrases like "It is important to note that" or "In today's competitive landscape"
- Vary paragraph length significantly (1 sentence to 6 sentences)
- Include 1-2 slightly imperfect sentences (run-ons, fragments — like real human writing)
- Add a personal touch: "Last month, a buyer from Texas asked us..."

## Final Checklist
- [ ] Primary keyword appears in H1, first 100 words, and at least 2 H2 sections
- [ ] Secondary keywords distributed naturally
- [ ] At least 3 EEAT trust signals embedded
- [ ] Internal links: product page, about page, contact page
- [ ] CTA matches B2B intent (quote/sample request)
- [ ] Word count: 1500-2500
- [ ] No AI tells (no structured lists, no formulaic transitions)
""")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = ArgumentParser(description="Generate article writing prompt")
    parser.add_argument("--keyword", required=True, help="Target keyword")
    parser.add_argument("--country", default="us", help="Target country code")
    parser.add_argument("--brief", help="Path to content brief file")
    parser.add_argument("--seo", help="Path to SEO optimization file")
    parser.add_argument("--serp", help="Path to SERP analysis file (optional)")
    parser.add_argument("--gaps", help="Path to competitor gap analysis (optional)")
    parser.add_argument("--output", required=True, help="Output writing prompt file")
    args = parser.parse_args()

    brief = read_file_safe(args.brief)
    seo = read_file_safe(args.seo)
    serp = read_file_safe(args.serp)
    gaps = read_file_safe(args.gaps)

    if not brief:
        print("⚠️  No content brief found. Using defaults.", file=sys.stderr)
    if not seo:
        print("⚠️  No SEO data found. Using defaults.", file=sys.stderr)

    prompt = generate_writing_prompt(args.keyword, args.country, brief, seo, serp)

    with open(args.output, "w") as f:
        f.write(prompt)
    print(f"✅ Writing prompt written to {args.output}", file=sys.stderr)
    print(f"   Article target: {args.keyword} → {args.country}", file=sys.stderr)
    print(f"   Word count target: 1500-2500 words", file=sys.stderr)
