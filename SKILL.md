---
name: seo-content-research
description: >-
  SEO content research for B2B/B2C international markets. Discovers keywords
  via DuckDuckGo proxied through Jina Reader (bypasses VPS IP bans, zero API
  cost), analyzes SERP with real competitor identification, generates EEAT
  content briefs. For factory owners and exporters needing international SEO
  research without paid tools.
version: 1.2.0
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

**Five core capabilities this skill provides:**

1. **Keyword Discovery** — Multi-source keyword hunting via DuckDuckGo through Jina Reader proxy (bypasses IP-based anti-bot), intent classification, competition estimation
2. **SERP Competition Analysis** — Market-by-market competitive landscape, Chinese supplier share, ranking difficulty scoring via Jina-proxied search
3. **Content Brief Generation** — EEAT-aligned outlines, H2/H3 structure, internal linking suggestions, AI detection avoidance
4. **Google SEO Optimization** — Content quality checks (Google 32 questions), EEAT signal checklists, NavBoost engagement strategy, Core Update response plan, Hub-and-Spoke internal linking, AI content compliance
5. **Article Writing** — Combines brief + SEO + SERP into a structured writing prompt for LLM or human writer

## Data Source Architecture

**Default: DDG via Jina Reader (stable, unlimited).** Search queries route through `r.jina.ai` which proxies DuckDuckGo Lite on their servers, bypassing VPS IP bans entirely:

```python
# Jina handles rendering on their infrastructure
# Returns clean markdown — no API key needed
r.jina.ai/https://lite.duckduckgo.com/lite/?q=search+query
```

**Optional Google-quality data:** Pass `--google` to try Startpage (Google Search Alliance) with IP rotation between direct and v2raya SOCKS5 proxy (`localhost:20170`). This extends captcha-free queries to 3-4 before being blocked. When Startpage fails, falls back to DDG via Jina.

```
Default:  DDG via Jina Reader      → Unlimited, no captcha, stable
--google: Startpage (direct/proxy)  → Google quality, ~3 queries, then Jina fallback
```

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

Search engines block VPS/server IPs aggressively. From data-center IPs:

- DuckDuckGo Lite → 403 Forbidden
- Bing → Captcha challenge
- Startpage → Captcha after 1-2 queries

**Solution: Route through Jina Reader proxy.** `r.jina.ai` fetches pages on Jina's servers, bypasses IP bans, returns clean markdown. No API key needed.

Priority when searching:
1. **Startpage (direct IP)** — Google-quality, ~2 queries before captcha
2. **Startpage (v2raya SOCKS5 proxy)** — different exit IP, +2 more queries
3. **DDG via Jina proxy** — most reliable from VPS, no query limit
4. **Jina Reader** (`r.jina.ai/URL`) — read competitor pages directly
5. **Bing** — only when `setmkt` country-specific results are essential

### Phase 2: Multi-Source Keyword Discovery

Run `tools/keyword-finder.py` with `--clean` flag. In clean mode, the search queries themselves become the output keywords (not raw page titles), making the result directly usable as a keyword strategy table.

```bash
# Clean mode (recommended) — outputs search queries as keywords
python3 tools/keyword-finder.py \
  --product "heavy duty tarp" \
  --countries "us,ca,uk,au" \
  --clean \
  --output /tmp/kw-results.md
```

Without `--clean`, the tool outputs raw SERP page titles — useful for competitor discovery but noisy for keyword strategy. Always prefer `--clean` for deliverable reports.

The tool searches across DuckDuckGo proxied through Jina Reader with 12 search patterns per country:

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

Each keyword in clean mode comes with a competition estimate derived from actual SERP composition:

| SERP Signal | Competition Label |
|-------------|:-----------------:|
| 3+ manufacturers/factories in top 10 | 🔴 High |
| 2+ B2B platforms (Alibaba/MIC) in top 5 | 🔴 High |
| Only BigBox/B2C retailers (Amazon/Home Depot) | 🟢 Low (not B2B comp) |
| Zero direct competitors | 🟢 Low |
| Mixed (some niche sites, some comp) | 🟡 Medium |

The tool also lists the top 2-3 actual competitor domains per keyword with type labels (Manufacturer / Tarp retailer / B2B platform / Wholesaler), so you can see who you'd be competing against for each term.

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

### Phase 5: Google SEO Optimization

Run `tools/seo-optimizer.py` to get 10-section Google SEO recommendations for any keyword:

```bash
python3 tools/seo-optimizer.py \
  --keyword "china tarp manufacturer" \
  --country us \
  --output /tmp/seo-optimize.md
```

The optimizer is built from 50+ cross-referenced sources (Google official, Moz, Backlinko, First Page Sage, etc.) covering the 2026 ranking landscape. Outputs:

| Section | Content |
|---------|---------|
| Keyword & Intent Analysis | Search intent inference, market targeting |
| Ranking Factor Weights | 12 factors with % weight, trend direction, priority |
| AI Content Risk Check | Google's 32 self-assessment questions (bucket 4: search-engine-first red flags) |
| EEAT Signal Checklist | Trust-first framework (Trust → Experience → Expertise → Authority) |
| Content Freshness Plan | Per-page-type update frequency, technical implementation |
| NavBoost Strategy | goodClicks/badClicks/lastLongestClicks tactics |
| Hub-and-Spoke Internal Linking | Content cluster architecture for the target keyword |
| Core Update Response Plan | 6-week update cycle, March/May 2026 signals |
| AI Compliance Checklist | What Google allows vs penalizes in 2026 |
| Intent-Specific Recommendations | Tailored to B2B procurement vs wholesale vs informational intent |

Includes actionable references to Google's March 2026 Core Update (80% TOP3 displacement, flow from aggregators to original sources) and May 2026 update (freshness weight 6%↑↑).

### Phase 6: Article Writing (optional)

After keyword discovery, SERP analysis, brief generation, and Google SEO optimization, generate a structured **writing prompt** for LLM or human writer:

```bash
python3 tools/article-writer.py \
  --keyword "china tarp manufacturer" \
  --country us \
  --brief /tmp/brief.md \
  --seo /tmp/seo-optimize.md \
  --serp /tmp/serp.md \
  --output /tmp/write-prompt.md
```

The writing prompt includes:
- Role definition (expert SEO content writer / B2B export perspective)
- Title suggestions from the content brief
- H2 structure with writing guidance per section
- EEAT signals to embed (from SEO optimizer)
- Competitors to outrank (from SERP analysis)
- AI detection avoidance rules (short paragraphs, first-person plural "we", natural rhythm)
- Final pre-publish checklist

The output is a self-contained markdown file that can be fed directly to any LLM for first-draft generation.

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
| Keyword Finder | `tools/keyword-finder.py` | Multi-source keyword discovery, dedup, intent classification, competition estimation |
| SERP Analyzer | `tools/serp-analyzer.py` | Top-10 SERP analysis, competitor type classification, matrix output |
| Content Brief Generator | `tools/content-brief-gen.py` | EEAT-aligned content brief generation from keyword + country |
| SEO Optimizer | `tools/seo-optimizer.py` | 10-section Google SEO recommendations (EEAT, NavBoost, Core Updates, AI compliance) |
| Article Writer | `tools/article-writer.py` | Combines brief + SEO + SERP into structured LLM writing prompt |
| Pipeline | `pipeline.py` | One-command chains all 5 tools into a single report |

**Usage:**

### One-command pipeline (recommended)
```bash
# Full report: keywords + SERP + brief
python3 pipeline.py \
  --product "heavy duty tarp" \
  --countries "us,ca,uk,au" \
  --output /tmp/full-report.md

# With Google SEO optimization
python3 pipeline.py --product "heavy duty tarp" --countries "us" --optimize --output report.md

# Full pipeline: keywords + SERP + brief + SEO + article writing prompt
python3 pipeline.py --product "china tarp" --countries "us" --optimize --write --output report.md
```

### Step-by-step
```bash
# Discover keywords (clean mode)
python3 tools/keyword-finder.py \
  --product "heavy duty tarp" \
  --countries "us,ca,uk,au" \
  --output /tmp/kw-scan.md

# SERP analysis for a key term
python3 tools/serp-analyzer.py \
  --keyword "china tarp manufacturer" \
  --country us \
  --output /tmp/serp-china.md

# Content brief for top keyword
python3 tools/content-brief-gen.py \
  --keyword "heavy duty tarp manufacturer canada" \
  --country ca \
  --output /tmp/brief.md
```

## Templates & References

| File | Content |
|------|---------|
| `references/seo-glossary.md` | Common SEO terms, Google ranking factors, EEAT framework |
| `references/content-brief-template.md` | Full content brief template with examples |

## Common Pitfalls

1. **Startpage HTML is NOT `<a>text</a>`.** Startpage wraps result titles in `<a class="result-title result-link">` with `<h2 class="wgl-title">TITLE</h2>` inside. Parsing with a simple `href="..."` → `>text<` regex will get zero matches. Use the correct regex: `r'class="result-title result-link[^"]*"\s*href="(https?://[^"]+)".*?<h2[^>]*class="wgl-title[^"]*"[^>]*>(.*?)</h2>'`
2. **Search engines blocking VPS IPs.** DuckDuckGo (403), Bing (captcha), and Startpage (~2 queries then captcha) all have anti-bot protection from VPS IPs. Use Jina Reader (`r.jina.ai`) fallback when Startpage fails. When all automated search fails, fall back to manual website analysis of known competitors.
3. **Trusting single-source search data.** DuckDuckGo, Bing, and Startpage all give incomplete results from VPS IPs. Cross-check manually or use Jina Reader for competitor content extraction.
4. **Mixing B2B and B2C keywords.** "Buy tarp" (B2C) vs "tarp manufacturer" (B2B) = completely different search intent. Don't lump them together.
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

### One-Command Full Report (recommended)
```bash
python3 pipeline.py \
  --product "heavy duty tarp" \
  --countries "us,ca,uk,au" \
  --output /home/report.md
```

### Quick Keyword Scan (3 min)
```bash
python3 tools/keyword-finder.py \
  --product "heavy duty tarp" \
  --countries "us,ca,au,uk" \
  --output /tmp/kw-scan.md
```

### Full Market Deep Dive (15 min)
```bash
# Phase 1: keywords (clean mode)
python3 tools/keyword-finder.py \
  --product "pvc tarpaulin" \
  --countries "us,ca,uk" \
  --output /tmp/kw-list.md

# Phase 2: SERP analysis for top keyword
python3 tools/serp-analyzer.py \
  --keyword "china tarp manufacturer" \
  --country us \
  --output /tmp/serp-analysis.md

# Phase 3: write content brief for best keyword
python3 tools/content-brief-gen.py \
  --keyword "pvc tarpaulin manufacturer usa" \
  --country us \
  --output /tmp/content-brief-usa.md
```
