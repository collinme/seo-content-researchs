---
name: seo-content-research
description: >-
  Multi-source SEO content research for B2B/B2C international markets.
  Discovers keywords via Startpage / DuckDuckGo / Bing / Jina Reader (zero API
  cost), analyzes SERP competition by country, generates content briefs with
  EEAT alignment. For factory owners, exporters, independent station operators
  needing data-driven international SEO content strategies without expensive
  paid tools.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [seo, keyword-research, content-strategy, b2b, international, export]
    related_skills: [b2b-international-seo, b2b-international-seo-research, geo-optimization]
---

# SEO Content Research Skill Pack

## Overview

A complete Hermes Agent skill pack for SEO content research targeting international markets. Uses zero-cost data sources (DuckDuckGo, Bing, Jina Reader) to discover keywords, analyze competition, and generate EEAT-aligned content briefs.

Designed for Chinese factories/exporters, cross-border sellers, and independent station operators who need professional SEO research without $99+/month Ahrefs subscriptions.

**Three core capabilities this skill provides:**

1. **Keyword Discovery** — Multi-source keyword hunting via DuckDuckGo through Jina Reader proxy (bypasses IP-based anti-bot), intent classification, competition estimation
2. **SERP Competition Analysis** — Market-by-market competitive landscape, Chinese supplier share, ranking difficulty scoring via Jina-proxied search
3. **Content Brief Generation** — EEAT-aligned outlines, H2/H3 structure, internal linking suggestions, AI detection avoidance

## Data Source Architecture

All search queries are routed through **Jina Reader** (`r.jina.ai`) as a proxy layer:

```python
# Jina fetches the page on its servers, handles captcha/JS rendering
# We get back clean markdown — no API key needed
r.jina.ai/https://lite.duckduckgo.com/lite/?q=search+query
```

This solves the VPS IP anti-bot problem: DDG/Bing/Startpage all block data center IPs, but Jina's renderer on their infrastructure bypasses these blocks.

## When to Use

- User wants to find SEO keywords for a product/industry targeting overseas markets
- User needs to analyze what competitors rank for in a specific country
- User wants a content brief/buying guide outline for a target keyword
- User asks "这个产品的SEO关键词怎么做" or similar SEO research queries
- User wants to compare SEO difficulty across multiple international markets

**Not for:** Domestic Chinese SEO (高竞争/内卷 — user prefers international markets); paid-tool data (Ahrefs/SEMrush login management); social media content strategy.

## Core Workflow

### Phase 1: Product & Market Scoping

Before searching, establish the scope:

| Question | Why it matters |
|----------|---------------|
| What's the exact product? | Sub-categories have different keyword profiles (tarpaulin vs PVC tarpaulin vs heavy duty tarp) |
| Target countries? | Each market needs separate research |
| Buyer intent? | B2B (procurement/supplier) vs B2C (retail/consumer) → different keywords |
| Existing channels? | Warehouse/branch in country → hybrid "China factory + local service" positioning |
| Budget tier? | Low/mid/high → different keyword targets |

Default market preference (user prefers international over Chinese):
1. Canada / Australia / NZ — low competition, English, import-dependent
2. UK / Netherlands — English-friendly, trade-oriented
3. Middle East (UAE/Saudi) — high import dependency, low SEO competition
4. Southeast Asia (English for B2B, localize for B2C)
5. US — largest but highest competition, chase long-tail only
6. Germany/France — must localize language, higher effort

#### Search Backend Priority

Search engines block VPS/server IPs aggressively. When automated tools fail (403/captcha), use this priority:

1. **Startpage** (`startpage.com`) — **推荐首选**. Uses Google Search Alliance results. ~2 queries before captcha. Best for English B2B keywords.
2. **Jina AI Reader** (`r.jina.ai/URL`) — Read competitor pages for keyword ideas and SERP insight
3. **DuckDuckGo Lite** — Often 403 from VPS IPs; fallback only
4. **Bing** — Multi-word misinterpretation; captcha from VPS IPs; last resort

**If all search backends are blocked:** Use Jina Reader to read known competitor page titles and meta descriptions for keyword ideas. Fall back from automated tools to manual website analysis.

### Phase 2: Multi-Source Keyword Discovery

Run the built-in `keyword-finder.py` tool. It searches across:

- **Startpage** — primary source (Google Alliance results)
- **DuckDuckGo** (lite API) — secondary
- **Bing** (mkt parameter) — tertiary
- **Jina AI Reader** (r.jina.ai) — page-level content extraction

**Search patterns to use for each country:**

| Intent | Pattern | Example |
|--------|---------|---------|
| Supplier search | `[product] manufacturer [country]` | `pvc tarpaulin manufacturer usa` |
| Wholesale | `wholesale [product] [country]` | `wholesale heavy duty tarp canada` |
| Import | `import [product] from china to [country]` | `import tarpaulin from china to uk` |
| Application | `[product] for [industry] [country]` | `agricultural tarpaulin australia` |
| Local language | Translate to target language | `قماش مقاوم للماء الإمارات` (Arabic) |
| Comparison | `[product A] vs [product B]` | `PVC vs PE tarpaulin` |

**Output:** A list of 15-30 keywords per country, each with:
- Keyword text
- Search intent label (B2B procurement / wholesale / OEM / application / comparison)
- Estimated competition level (🟢 Low / 🟡 Medium / 🔴 High)
- Source of discovery

### Phase 3: SERP Competition Analysis

Run `serp-analyzer.py` on top keywords to classify the competitive landscape:

Classify each top-10 result by type:

| Type | Icon | Difficulty | Strategy |
|------|:----:|:----------:|----------|
| Factory/Manufacturer site | 🏭 | Hard to outrank | Differentiate on service/speed |
| B2B platform (Alibaba, Faire) | 🌐 | Beatable | Independent site + content depth beats template pages |
| BigBox retailer | 🛍️ | Not direct comp | They target B2C, you target B2B |
| Niche industry site | 🏪 | Moderate | Match content quality first |
| Encyclopedia/guide | 📖 | Easy | Product page + buying guide beats generic info |
| Blog/review | 📝 | Moderate | Out-detail competitors |

**Track metrics per market:**
- Chinese supplier share in top 10 (🗺️)
- Alibaba/MIC dominance (🛒)
- Average page quality (thin content vs comprehensive)
- Local brand presence
- Backdoor keywords (easy-to-rank terms competitors missed)

### Phase 4: Content Brief Generation

Run `content-brief-gen.py` with target keyword + country to produce:

```
# Content Brief: [Target Keyword]

## Target: [Country/Language]

## Primary Keyword: [KW]
## Secondary Keywords: [3-5 related KWs]

## Search Intent
[Commercial / Informational / Transactional / Navigational]

## Target Audience
[B2B procurement manager / B2C end-customer / Wholesale buyer]

## Competitors to Beat
1. [URL] — [Type] — [Their angle]
2. [URL] — [Type] — [Their angle]

## Recommended H2 Structure
1. [H2] — Why this heading
2. [H2] — Angle to differentiate from competitors

## Key Stats / Data Points to Include
- [Stat 1]
- [Stat 2]

## EEAT Signals Needed
- [Author bio / Factory tour / Certifications / Case studies]
- [Internal links to product pages / about page]

## AI Detection Note
- [Rewrite structured lists as natural paragraphs]
- [Add personal experience touchpoints]
```

## Tool Scripts

All tools are in `tools/` and use Python stdlib only (no pip dependencies).

| Tool | File | What it does |
|------|------|-------------|
| Keyword Finder | `tools/keyword-finder.py` | Multi-source keyword discovery, dedup, intent classification |
| SERP Analyzer | `tools/serp-analyzer.py` | Top-10 SERP analysis, competitor type classification, matrix output |
| Content Brief Generator | `tools/content-brief-gen.py` | EEAT-aligned content brief generation from keyword + country |

**Usage:**
```bash
# Keyword discovery
python3 tools/keyword-finder.py --product "heavy duty tarp" --countries "us,ca,uk"

# SERP analysis (reads keywords from file or stdin)
python3 tools/serp-analyzer.py --keywords "pvc tarpaulin manufacturer usa" --country us

# Content brief
python3 tools/content-brief-gen.py --keyword "heavy duty tarp manufacturer canada"
```

## Templates & References

| File | Content |
|------|---------|
| `references/seo-glossary.md` | Common SEO terms, Google ranking factors, EEAT framework |
| `references/content-brief-template.md` | Full content brief template with examples |

## Common Pitfalls

1. **Search engines blocking VPS IPs.** DuckDuckGo (403), Bing (captcha), and Startpage (~2 queries then captcha) all have anti-bot protection from VPS IPs. Use Jina Reader (`r.jina.ai`) to read known competitor pages when search backends fail. When all automated search fails, fall back to manual website analysis of known competitors.
2. **Trusting single-source search data.** DuckDuckGo, Bing, and Startpage all give incomplete results from VPS IPs. Cross-check manually or use Jina Reader for competitor content extraction.
3. **Mixing B2B and B2C keywords.** "Buy tarp" (B2C) vs "tarp manufacturer" (B2B) = completely different search intent. Don't lump them together.
3. **Estimating search volume without paid tools.** Without Ahrefs/SEMrush, treat all volume estimates as ±50%. Focus on difficulty signal over volume precision.
4. **Over-localizing too early.** Start with English for English-friendly markets, add local languages only after proving product-market fit.
5. **Ignoring Alibaba dominance.** If Alibaba holds 4+ of top 10, the keyword is hard to crack with a new site. Target longer-tail variations.
6. **Writing for SEO, not for humans.** AI-detection penalty is real. Follow the "tarp-content-writing" skill's humanization rules.
7. **Not checking hreflang on multi-language sites.** Missing hreflang = Google treats localized pages as duplicates.

## Verification Checklist

- [ ] Product and target countries scoped
- [ ] 15-30 keywords discovered per market
- [ ] Search intent labeled for each keyword
- [ ] Top-3 keywords analyzed via SERP analyzer
- [ ] Competition type classification complete
- [ ] Chinese supplier share assessed
- [ ] Content brief generated for priority keyword
- [ ] AI detection check on generated content
- [ ] Output saved as structured markdown

## One-Shot Recipes

### Quick Keyword Scan (3 min)
```bash
python3 tools/keyword-finder.py \
  --product "heavy duty tarp" \
  --countries "us,ca,au,uk" \
  --output /tmp/kw-scan.md
```

### Full Market Deep Dive (15 min)
```bash
# Phase 1: keywords
python3 tools/keyword-finder.py \
  --product "pvc tarpaulin" \
  --countries "us,ca,uk" \
  --output /tmp/kw-list.md

# Phase 2: analyze top keywords
python3 tools/serp-analyzer.py \
  --input /tmp/kw-list.md \
  --output /tmp/serp-analysis.md

# Phase 3: write content brief for best keyword
python3 tools/content-brief-gen.py \
  --keyword "pvc tarpaulin manufacturer usa" \
  --country us \
  --output /tmp/content-brief-usa.md
```
