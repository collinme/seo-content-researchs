#!/usr/bin/env python3
"""
Content Brief Generator — Generate EEAT-aligned SEO content briefs.
Zero external dependencies (stdlib only).

Produces structured content briefs suitable for human writers or AI
content generation with proper EEAT signals.

Usage:
  python3 tools/content-brief-gen.py --keyword "heavy duty tarp manufacturer canada"
  python3 tools/content-brief-gen.py --keyword "pvc tarpaulin supplier usa" --country us --output /tmp/brief.md
"""

import os
import sys
from argparse import ArgumentParser
from dataclasses import dataclass


TITLE_FORMULAS = {
    "B2B procurement": [
        "{keyword} | {year} Guide",
        "Top {keyword} - Direct From Factory",
        "{keyword}: How to Choose the Right Partner",
    ],
    "wholesale": [
        "Bulk {keyword} - {country_upper} Wholesale Pricing {year}",
        "Where to Buy {keyword} in {country_upper}",
    ],
    "import/supply chain": [
        "How to Import {product_proper} from China to {country_upper}",
        "{product_proper} Import Guide {country_upper} - Customs, Shipping & Costs",
    ],
    "comparison/guide": [
        "{product_proper} Buying Guide {year} | Types, Prices & Reviews",
        "{product_proper} vs {competitor}: What's the Difference?",
    ],
    "application": [
        "{product_proper} for {country_upper} Market: Complete Overview",
        "The Ultimate Guide to {product_proper} in {country_upper}",
    ],
    "OEM/custom": [
        "Custom {product_proper} Manufacturer | OEM/ODM Solutions",
        "Custom {product_proper} - Your Design, Our Factory",
    ],
    "generic": [
        "{product_proper} {country_upper} - Complete Guide for Buyers",
        "Everything You Need to Know About {product_proper} in {country_upper}",
    ],
}


H2_STRUCTURES = {
    "B2B procurement": [
        ("Why {country_upper} Businesses Choose {product_proper} from China",
         "Market context - show demand exists"),
        ("Key Factors When Selecting a {product_proper} Manufacturer",
         "Quality criteria - certifications, MOQ, lead time"),
        ("Our Manufacturing Process & Quality Control",
         "EEAT - factory transparency builds trust"),
        ("Custom {product_proper} Solutions for {country_upper} Clients",
         "Differentiator - OEM/custom capabilities"),
        ("Shipping & Logistics: From Our Factory to {country_upper}",
         "Practical info - reduces buyer friction"),
        ("Frequently Asked Questions About {product_proper}",
         "FAQ - captures voice search + featured snippet"),
    ],
    "wholesale": [
        ("{product_proper} Wholesale Market Overview in {country_upper}",
         "Size the market need"),
        ("Bulk Pricing Tiers & MOQ for {product_proper}",
         "Pricing transparency builds trust"),
        ("{product_proper} vs Competitor Products: Value Comparison",
         "Help buyer justify decision"),
        ("Shipping Costs & Lead Times to {country_upper}",
         "Logistics - key B2B purchase factor"),
        ("Why Source {product_proper} from Our Factory",
         "EEAT + differentiation"),
        ("Volume Discounts & Long-Term Partnership Options",
         "Call to action for large buyers"),
    ],
    "import/supply chain": [
        ("Why {country_upper} Imports {product_proper} from China",
         "Market context + trade data"),
        ("Step-by-Step Import Process from China to {country_upper}",
         "Practical guide - builds authority"),
        ("Customs Duties & Tax Considerations for {country_upper}",
         "High-value practical content"),
        ("Quality Control: Factory Audits & Third-Party Inspection",
         "Risk mitigation for importer"),
        ("Lead Times, Shipping Methods & Costs",
         "Logistics detail"),
        ("Finding a Reliable {product_proper} Factory in China",
         "Lead gen to our factory"),
    ],
}


COMPETITOR_GUESSES = {
    "tarp": "Poly Tarpaulin / Canvas Tarpaulin",
    "tarpaulin": "Poly Tarp / Canvas Tarp",
    "pe tarpaulin": "PVC Tarpaulin",
    "pvc tarpaulin": "PE Tarpaulin / HDPE Tarpaulin",
    "heavy duty tarp": "Lightweight Tarp / Poly Tarp",
}


@dataclass
class ContentBrief:
    keyword: str
    country: str = "us"
    intent: str = "B2B procurement"
    audience: str = "B2B procurement manager"
    product_name: str = ""
    year: str = "2026"

    def __post_init__(self):
        if not self.product_name:
            words = self.keyword.split()
            for stop in ["manufacturer", "supplier", "factory", "wholesale", "buy",
                          "guide", "best", "import", "china", "usa", "uk", "canada"]:
                words = [w for w in words if w.lower() != stop]
            self.product_name = " ".join(words).strip() if words else self.keyword

    def infer_intent(self) -> str:
        kw_lower = self.keyword.lower()
        if any(w in kw_lower for w in ["manufacturer", "supplier", "factory", "oem"]):
            return "B2B procurement"
        if any(w in kw_lower for w in ["wholesale", "bulk", "distributor"]):
            return "wholesale"
        if any(w in kw_lower for w in ["import", "export", "ship", "shipping", "from china"]):
            return "import/supply chain"
        if any(w in kw_lower for w in ["guide", "buying", "best", "vs", "review", "top"]):
            return "comparison/guide"
        if any(w in kw_lower for w in ["custom", "design"]):
            return "OEM/custom"
        if any(w in kw_lower for w in ["for", "application", "use"]):
            return "application"
        return "B2B procurement"

    def infer_audience(self) -> str:
        intent = self.infer_intent()
        if intent in ("B2B procurement", "OEM/custom"):
            return "B2B procurement / sourcing manager"
        if intent == "wholesale":
            return "Wholesale buyer / distributor"
        if intent == "import/supply chain":
            return "Importer / supply chain manager"
        return "Business decision-maker"

    def country_full(self) -> str:
        names = {
            "us": "USA", "ca": "Canada", "uk": "UK", "au": "Australia",
            "nz": "New Zealand", "de": "Germany", "fr": "France",
            "ae": "UAE", "sa": "Saudi Arabia", "sg": "Singapore",
            "nl": "Netherlands", "in": "India",
        }
        return names.get(self.country, self.country.upper())

    def generate(self) -> str:
        intent = self.infer_intent()
        audience = self.infer_audience()
        country_full = self.country_full()
        product_proper = " ".join(w.capitalize() for w in self.product_name.split())
        competitor = COMPETITOR_GUESSES.get(self.keyword.lower(), f"Alternative {product_proper}")

        titles = TITLE_FORMULAS.get(intent, TITLE_FORMULAS["generic"])
        title_suggestions = []
        for t in titles:
            title_suggestions.append(t.format(
                keyword=self.keyword,
                product_proper=product_proper,
                country_upper=country_full,
                competitor=competitor,
                year=self.year,
            ))

        h2s = H2_STRUCTURES.get(intent, H2_STRUCTURES["B2B procurement"])
        h2_lines = []
        for i, (heading, rationale) in enumerate(h2s, 1):
            formatted = heading.format(
                keyword=self.keyword,
                product_proper=product_proper,
                country_upper=country_full,
                competitor=competitor,
                year=self.year,
            )
            h2_lines.append(f"  {i}. **{formatted}** - _{rationale}_")

        stats = [
            f"Market size / year-over-year growth of {product_proper} in {country_full}",
            f"Price comparison table across quality tiers",
            f"Specification comparison (weight, durability, UV rating, etc.)",
        ]

        eeat = [
            f"Factory tour / production line photos",
            f"Quality certifications (ISO, SGS, etc.)",
            f"Client testimonials from {country_full}",
            f"Case study: {product_proper} shipped to {country_full}",
            f"Internal links to Product pages, About Us, Contact",
        ]

        brief = f"""# Content Brief: {self.keyword}

## Target Market
**Country:** {country_full} ({self.country.upper()})
**Language:** English

## Primary Keyword
`{self.keyword}`

## Secondary Keywords (Suggested)
- {product_proper} manufacturer {self.country.upper()}
- {product_proper} factory {self.country.upper()}
- wholesale {self.product_name.lower()} {self.country.upper()}
- buy {self.product_name.lower()} from china
- custom {self.product_name.lower()} {self.country.upper()}

## Search Intent
{intent}

## Target Audience
{audience}

## Title Suggestions
1. {title_suggestions[0] if title_suggestions else '{product_proper} {country_full} | Quality Manufacturer'}
2. {title_suggestions[1] if len(title_suggestions) > 1 else '{product_proper} Supplier {country_full} - Factory Direct'}
3. {title_suggestions[2] if len(title_suggestions) > 2 else 'The Complete Guide to {product_proper} in {country_full}'}

## Competitors to Analyze
_Run serp-analyzer.py for `{self.keyword}` / `{self.country}` to fill this in_

## Recommended H2 Structure
{chr(10).join(h2_lines)}

## Key Data Points to Include
- {chr(10).join('- ' + s for s in stats)}

## EEAT Signals Needed
- {chr(10).join('- ' + s for s in eeat)}

## Internal Links
- Product category page -> anchor text: "{product_proper}"
- About Us page -> anchor text: "our factory"
- Contact page -> anchor text: "get a quote"

## AI Detection Avoidance
- Write in natural paragraph flow, not structured lists
- Add 1-2 personal observations per section
- Vary sentence length (mix short and long sentences)
- Avoid formulaic transition words ("furthermore", "moreover", "in conclusion")
- Use concrete numbers and specific examples over vague claims

## Word Count Target
1500-2500 words (comprehensive enough to outrank competitors)
"""
        return brief


if __name__ == "__main__":
    parser = ArgumentParser(description="Generate SEO content brief")
    parser.add_argument("--keyword", required=True, help="Target keyword")
    parser.add_argument("--country", default="us", help="Target country code")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument("--product", help="Product name (auto-inferred from keyword if omitted)")
    args = parser.parse_args()

    brief = ContentBrief(
        keyword=args.keyword,
        country=args.country,
        product_name=args.product or "",
    )

    content = brief.generate()

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(content)
        print(f"\u2705 Content brief written to {args.output}", file=sys.stderr)
    else:
        print(content)
