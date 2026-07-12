#!/usr/bin/env python3
"""
SEO Optimizer — Google SEO recommendations for content.
Zero external dependencies (stdlib only).

Takes a keyword + country + optional competitor data, outputs:
  - Content quality assessment (Google 32 questions)
  - EEAT signal checklist (2026 framework, Trust-first)
  - Freshness & core update strategy
  - Hub-and-Spoke internal linking
  - NavBoost engagement tactics
  - AI content compliance

Based on 50+ cross-referenced sources (Google official, Moz, Backlinko, etc.)

Usage:
  python3 tools/seo-optimizer.py --keyword "china tarp manufacturer" --country us
  python3 tools/seo-optimizer.py --keyword "heavy duty tarp supplier canada" --country ca --output /tmp/optimizer.md
"""

import os
import json
import sys
from argparse import ArgumentParser
from typing import Optional

# ─── Google 2026 Ranking Factor Weights (cross-validated) ───────────────────

RANKING_FACTORS = {
    "content_quality": {"weight": 23, "label": "持续发布满意内容", "trend": "↑"},
    "meta_title_keyword": {"weight": 14, "label": "Meta Title关键词", "trend": "↓"},
    "backlinks": {"weight": 13, "label": "外链(高质量)", "trend": "↓"},
    "niche_expertise": {"weight": 13, "label": "利基专业度", "trend": "→"},
    "searcher_engagement": {"weight": 12, "label": "搜索者参与度(NavBoost)", "trend": "↑↑"},
    "freshness": {"weight": 6, "label": "内容新鲜度", "trend": "↑↑"},
    "mobile_friendly": {"weight": 5, "label": "移动端友好", "trend": "→"},
    "trustworthiness": {"weight": 4, "label": "可信度(EEAT-Trust)", "trend": "↑"},
    "link_diversity": {"weight": 3, "label": "链接分布多样性", "trend": "↑"},
    "page_speed": {"weight": 3, "label": "页面速度(CWV)", "trend": "→"},
    "ssl_https": {"weight": 2, "label": "SSL/HTTPS", "trend": "→"},
    "onpage_seo": {"weight": 1, "label": "内链/Schema/Header等", "trend": "↓"},
}

# ─── Google 32 self-assessment questions (key ones for AI content) ──────────

AI_RED_FLAGS = [
    {
        "id": "Q4-1",
        "question": "是否在使用大量自动化来生产内容？",
        "explanation": "AI批量生产风险。Google SpamBrain会检测规模化内容模式",
        "severity": "🔴 高风险",
        "fix": "每篇文章人工审核+编辑，标注AI辅助，添加原始研究和数据。单站日产出不超过1-2篇优质内容。"
    },
    {
        "id": "Q4-2",
        "question": "是否主要总结别人的话而不增加价值？",
        "explanation": "AI缝合内容。Google Passage Ranking会检测段落级原创性",
        "severity": "🔴 高风险",
        "fix": "每段至少包含一个原始观点/数据/案例。不要纯改写竞争对手内容。添加工厂实地信息、客户案例、产品规格实测。"
    },
    {
        "id": "Q4-3",
        "question": "是否在没有专业知识的情况下进入利基？",
        "explanation": "AI填充站。EEAT评估会检查作者/网站的专业度",
        "severity": "🟡 中风险",
        "fix": "展示工厂实拍、15年出口经验、ISO证书。About页写明团队背景。每篇文章署名人+简介。"
    },
]

EEAT_CHECKLIST = [
    {
        "signal": "Trust (最优先)",
        "items": [
            "✅ About页面：工厂历史、团队照片、联系方式",
            "✅ Contact页面：电话、邮箱、WhatsApp、地址",
            "✅ 客户评价/案例：至少3个来自目标国家的真实案例",
            "✅ 透明度：明确标注价格模式(FOB/CIF)、MOQ、交货时间",
            "✅ 退换货政策 / 质量保证条款",
        ]
    },
    {
        "signal": "Experience (经验)",
        "items": [
            "✅ 工厂生产线实拍照片/视频",
            "✅ 产品规格实测数据（克重、拉力、UV测试）",
            "✅ 出口国家清单 + 合作年限",
            "✅ 行业展会参与记录",
        ]
    },
    {
        "signal": "Expertise (专业)",
        "items": [
            "✅ ISO 9001 / SGS 等认证展示",
            "✅ 产品技术参数详细说明",
            "✅ 行业术语使用准确",
            "✅ 博客文章展示专业知识深度",
        ]
    },
    {
        "signal": "Authoritativeness (权威)",
        "items": [
            "✅ 被其他网站引用/转载",
            "✅ Google Business Profile（目标国家）",
            "✅ B2B平台（Alibaba/MIC）上正面评价",
            "✅ 行业目录收录",
        ]
    },
]

# ─── Core Update Strategy ───────────────────────────────────────────────────

CORE_UPDATE_STRATEGY = """
## Google Core Update 策略 (2026)

### 更新频率
- 核心更新约 **每6周一次**（从每年3-4次加速）
- March 2026: 80% TOP3位移, 24% TOP10跌出前100
- **审计→修复→等待恢复模型不再适用**, 需要更快迭代

### March 2026 关键信号
1. **原始来源 > 内容整合站** — 政府/非营利信任信号超过资历信号
2. **聚合器/比价站持续失血** — 流量向官方来源移动
3. **Entity Health概念深化** — 缺少可验证实体的站被分类为"无帮助"

### 应对策略
- **每季度至少更新一次** 所有核心页面（新鲜度权重6%↑↑）
- 每次核心更新后48小时内检查流量变化
- 建立「核心更新响应SOP」：检查→诊断→修复→监控
"""

NAVBOOST_STRATEGY = """
## NavBoost 参与度策略 (权重12%↑↑)

Google使用NavBoost追踪: goodClicks / badClicks / lastLongestClicks

### 提升方法
1. **首屏即价值** — 前100字直接回答用户问题（减少bounce）
2. **结构化停留** — 编号列表/对比表/交互式FAQ（延长dwell time）
3. **内部导航** — 相关文章推荐 + 产品页链接（增加页面浏览数）
4. **CTA优化** — "获取报价"而非"了解更多"（区分goodClick vs badClick）
5. **跳出率目标** < 40%, **停留时间目标** > 2分钟
"""

CONTENT_FRESHNESS = """
## 内容新鲜度策略 (权重6%↑↑)

| 页面类型 | 更新频率 | 更新内容 |
|---------|:-------:|---------|
| 首页 | 每季度 | 新产品/认证/合作信息 |
| 产品页 | 每半年 | 规格更新、价格调整 |
| 博客文章 | 每季度 | 添加新数据、更新年份、补充案例 |
| 国家落地页 | 每季度 | 更新关税/物流/市场信息 |

**技术实施：**
- 每篇文章标注 "Last updated: YYYY-MM-DD"
- 更新后通过 Search Console 请求索引
- 重大更新修改 publish date（非重大更新改 last modified）
"""

AI_CONTENT_COMPLIANCE = """
## AI 内容合规 (Google 2026政策)

### 允许 (不违规)
- AI辅助生产内容，经过**人工审核和编辑**
- AI用于研究/提纲/初稿，人类进行事实核查和润色

### 违规 (会被处罚)
- 规模化自动生产内容 (Scaled Content Abuse)
- AI生成后不经过人工审核直接发布
- 使用AI伪造专业知识/经验

### 合规必要条件
1. ✅ 披露AI使用方式
2. ✅ 人工审核后发布
3. ✅ 添加原始价值和数据
4. ✅ 作者信息真实可查
5. ✅ 每篇不超过1-2篇（非批量生产）
"""


def infer_intent(keyword: str) -> str:
    """Infer search intent from keyword."""
    kw = keyword.lower()
    if any(w in kw for w in ["manufacturer", "supplier", "factory", "oem"]):
        return "B2B procurement (采购决策)"
    if any(w in kw for w in ["wholesale", "bulk", "price"]):
        return "Wholesale buying (批发采购)"
    if any(w in kw for w in ["import", "export", "from china", "shipping"]):
        return "Import research (进口调研)"
    if any(w in kw for w in ["guide", "buying", "best", "vs", "review"]):
        return "Informational (信息查询)"
    return "Commercial investigation (商业调研)"


def generate_report(keyword: str, country: str, output_file: Optional[str] = None) -> str:
    """Generate full SEO optimization report."""
    intent = infer_intent(keyword)
    country_name = {"us": "USA", "ca": "Canada", "uk": "UK", "au": "Australia",
                    "nz": "New Zealand", "ae": "UAE"}.get(country, country.upper())

    lines = []
    lines.append(f"# Google SEO Optimization: `{keyword}` — {country_name}\n")

    # Section 1: Keyword & Intent
    lines.append("## 1. 关键词分析\n")
    lines.append(f"**Keyword:** `{keyword}`  ")
    lines.append(f"**Target country:** {country_name} ({country.upper()})  ")
    lines.append(f"**Search intent:** {intent}\n")

    # Section 2: Ranking Factors
    lines.append("## 2. 2026 Google排名因素权重\n")
    lines.append("| 因素 | 权重 | 趋势 | 当前优先级 |")
    lines.append("|------|:----:|:----:|:----------:|")
    for key, factor in sorted(RANKING_FACTORS.items(), key=lambda x: -x[1]["weight"]):
        # Determine priority based on intent
        if factor["weight"] >= 12:
            priority = "🔴 必须优化"
        elif factor["weight"] >= 6:
            priority = "🟡 重要"
        else:
            priority = "🟢 基础要求"
        lines.append(f"| {factor['label']} | {factor['weight']}% | {factor['trend']} | {priority} |")
    lines.append("")

    # Section 3: AI Content Red Flags
    lines.append("## 3. AI内容风险检查\n")
    lines.append(f"针对 `{keyword}` 的内容，检查以下高风险信号：\n")
    lines.append("| 风险 | 问题 | 修复建议 |")
    lines.append("|:----:|------|---------|")
    for flag in AI_RED_FLAGS:
        lines.append(f"| {flag['severity']} | {flag['question']} | {flag['fix']} |")
    lines.append("")
    lines.append('> Google 32道自审题共8桶，以上3条为桶四（搜索引擎优先警示）。答"是"越多问题越大。\n')

    # Section 4: EEAT Checklist
    lines.append("## 4. EEAT信号清单 (Trust-first)\n")
    lines.append("Google原文：\"Of these aspects, **trust is most important**\"\n")
    for category in EEAT_CHECKLIST:
        lines.append(f"### {category['signal']}")
        for item in category["items"]:
            lines.append(item)
        lines.append("")

    # Section 5: Content Freshness
    lines.append("## 5. 内容新鲜度计划\n")
    lines.append(CONTENT_FRESHNESS)
    lines.append("")

    # Section 6: NavBoost
    lines.append("## 6. NavBoost参与度策略 (12%↑↑)\n")
    lines.append("Google内部使用 `goodClicks/badClicks/lastLongestClicks` 追踪用户参与度\n")
    lines.append(NAVBOOST_STRATEGY)
    lines.append("")

    # Section 7: Internal Linking
    lines.append("## 7. Hub-and-Spoke内链结构\n")
    lines.append(f"针对 `{keyword}` 推荐的内容集群：\n")
    lines.append("```")
    lines.append(f"/                     ← Hub: {keyword} (核心页)")
    lines.append("├── products/          ← 产品分类页")
    lines.append("├── about/             ← 工厂介绍+EEAT")
    lines.append("├── contact/           ← 询盘转化")
    lines.append("├── blog/              ← 内容博客")
    lines.append("│   ├── buying-guide/  ← 购买指南 (Spoke)")
    lines.append("│   ├── vs-comparison/ ← 对比文章 (Spoke)")
    lines.append("│   └── industry-app/  ← 应用场景 (Spoke)")
    lines.append("└── country/           ← 国家落地页")
    lines.append(f"    └── {country}/       ← {country_name}市场页")
    lines.append("```")
    lines.append("")

    # Section 8: Core Update
    lines.append("## 8. Core Update 策略\n")
    lines.append(CORE_UPDATE_STRATEGY)
    lines.append("")

    # Section 9: AI Compliance
    lines.append("## 9. AI内容合规清单\n")
    lines.append(AI_CONTENT_COMPLIANCE)
    lines.append("")

    # Section 10: Intent-specific recommendations
    lines.append("## 10. 基于搜索意图的优化建议\n")
    if "B2B procurement" in intent:
        lines.append(f"""
针对 `{keyword}` 的 B2B 采购意图，重点优化：

1. **首屏内容**：直接展示工厂实力 — "15年XXX制造经验，出口XX国"
2. **信任信号**：ISO证书 + 客户Logo + 工厂航拍图
3. **转化路径**：每个页面都有"获取报价"按钮
4. **FAQ区块**：回答MOQ、交期、付款方式、样品政策
5. **技术参数表**：产品规格详细对比（胜出信息型搜索的Featured Snippet）
""")
    elif "Wholesale" in intent:
        lines.append(f"""
针对 `{keyword}` 的批发意图，重点优化：

1. **定价透明**：标注FOB/CIF价格区间
2. **批量阶梯**：不同数量级的价格对比表
3. **物流信息**：到{country_name}的运费估算和交期
4. **最小起订量**：明确标注MOQ
""")
    else:
        lines.append(f"""
针对 `{keyword}` 的信息/调研意图，重点优化：

1. **深度指南**：写1500-2500字的完整指南
2. **对比表格**：不同材质/规格的优劣势对比
3. **内链闭环**：引导到产品页和询盘页
""")

    output = "\n".join(lines)
    if output_file:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w") as f:
            f.write(output)
        print(f"✅ SEO optimization report written to {output_file}", file=sys.stderr)
    else:
        print(output)

    return output


if __name__ == "__main__":
    parser = ArgumentParser(description="Google SEO optimizer")
    parser.add_argument("--keyword", required=True, help="Target keyword")
    parser.add_argument("--country", default="us", help="Target country code")
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    generate_report(args.keyword, args.country, args.output)
