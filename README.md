# SEO Content Research — Hermes Agent Skill Pack

Multi-source SEO content research for B2B/B2C international markets.

**Keywords:** `seo` `keyword-research` `content-strategy` `b2b` `international` `export` `hermes-agent`

## What's Inside

| Component | File | Description |
|-----------|------|-------------|
| Skill Definition | `SKILL.md` | Full SEO content research workflow for Hermes Agent |
| Keyword Finder | `tools/keyword-finder.py` | Multi-source keyword discovery via DuckDuckGo + Bing (zero API cost) |
| SERP Analyzer | `tools/serp-analyzer.py` | Competition analysis by country, competitor type classification |
| Content Brief Generator | `tools/content-brief-gen.py` | EEAT-aligned content briefs with H2 structure + title suggestions |
| SEO Glossary | `references/seo-glossary.md` | Key SEO terms reference |
| Content Brief Template | `references/content-brief-template.md` | Reusable content brief template with examples |

## Quick Start

```bash
# 1. Install as Hermes skill
cp -r seo-content-research ~/.hermes/skills/seo-content/

# 2. Discover keywords
python3 tools/keyword-finder.py \
  --product "heavy duty tarp" \
  --countries "us,ca,au,uk" \
  --output /tmp/kw-results.md

# 3. Analyze SERP competition
python3 tools/serp-analyzer.py \
  --input /tmp/kw-results.md \
  --country us \
  --output /tmp/serp-analysis.md

# 4. Generate content brief
python3 tools/content-brief-gen.py \
  --keyword "heavy duty tarp manufacturer canada" \
  --country ca \
  --output /tmp/brief.md
```

### One-Shot: Full Pipeline

```bash
python3 tools/keyword-finder.py \
  --product "pvc tarpaulin" \
  --countries "us,ca,uk" \
  --output /tmp/kws.md && \
python3 tools/serp-analyzer.py \
  --input /tmp/kws.md \
  --country us \
  --output /tmp/serp.md && \
python3 tools/content-brief-gen.py \
  --keyword "$(head -20 /tmp/kws.md | grep -E '^\|' | tail -1 | cut -d'|' -f3 | xargs)" \
  --country us \
  --output /tmp/brief.md
```

## Requirements

- **Python 3.8+** (stdlib only — no pip dependencies)
- **Internet access** (DuckDuckGo + Bing fetch SERP data)

## How It Works

1. **Keyword Discovery** — Searches DuckDuckGo and Bing with 12+ search patterns per country (manufacturer, supplier, wholesale, import, application, comparison)
2. **SERP Competition Analysis** — Fetches Bing SERP, classifies each result by type (Factory, B2B Platform, Retailer, Guide, etc.), assesses difficulty
3. **Content Brief Generation** — Infers search intent from keyword, generates title suggestions, H2 structure, EEAT signals, and AI detection avoidance rules

## Use Cases

- Chinese factories/exporters targeting overseas markets
- Cross-border sellers doing content marketing
- Independent station operators needing data-driven SEO
- SEO agencies doing quick competitive research

## License

MIT
