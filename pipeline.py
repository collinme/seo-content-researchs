#!/usr/bin/env python3
"""
SEO Content Research Pipeline — one command, full report.

Chains keyword-finder → serp-analyzer → content-brief-gen into a single report.
Uses DDG via Jina Reader (stable data source, unlimited queries).

Usage:
  python3 pipeline.py --product "heavy duty tarp" --countries "us,ca,uk,au"
  python3 pipeline.py --product "aluminum profile" --countries "us,uk,ae" --output /tmp/report.md
  python3 pipeline.py --product "pvc tarpaulin" --countries "us,ca" --google  # try Google source
"""

import os
import re
import subprocess
import sys
import tempfile
from argparse import ArgumentParser
from datetime import datetime


TOOLS_DIR = os.path.join(os.path.dirname(__file__), "tools")


def run_step(script: str, args: list, step_name: str) -> str:
    """Run a tool script and return its stdout output path."""
    cmd = [sys.executable, os.path.join(TOOLS_DIR, script)] + args
    print(f"\n{'='*50}", file=sys.stderr)
    print(f"  Step: {step_name}", file=sys.stderr)
    print(f"  Cmd: {' '.join(cmd)}", file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    # Print stderr (progress), return stdout if it's a file path
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")

    if result.returncode != 0:
        print(f"  ❌ {step_name} failed (exit {result.returncode})", file=sys.stderr)
        if result.stderr:
            print(f"  Error: {result.stderr[-500:]}", file=sys.stderr)
        return None

    # Find output file from args
    for i, arg in enumerate(args):
        if arg == "--output" and i + 1 < len(args):
            out_path = args[i + 1]
            if os.path.exists(out_path):
                return out_path

    # No --output flag — check for output in stderr
    match = re.search(r'Written to (.+)', result.stderr)
    if match:
        path = match.group(1).strip()
        if os.path.exists(path):
            return path

    print(f"  ⚠️ No output file found for {step_name}", file=sys.stderr)
    return None


def extract_top_keywords(kw_path: str, max_n: int = 5) -> list:
    """Extract top N keywords from keyword-finder output for SERP analysis."""
    keywords = []
    with open(kw_path) as f:
        for line in f:
            # Match table rows: | N | `keyword` | intent | competition | ...
            match = re.match(r'\|\s*\d+\s*\|\s*`([^`]+)`', line)
            if match:
                kw = match.group(1).strip()
                if kw and kw not in keywords:
                    keywords.append(kw)

    # Return unique keywords, limit to max_n
    seen = []
    for kw in keywords:
        if kw not in seen:
            seen.append(kw)
    return seen[:max_n]


def build_report(product: str, countries: str, kw_path: str, serp_path: str = None,
                 brief_path: str = None, optimize_path: str = None) -> str:
    """Consolidate all outputs into one markdown report."""
    lines = []
    lines.append(f"# SEO Content Research Report: {product}\n")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ")
    lines.append(f"**Target markets:** {countries}  ")
    lines.append(f"**Data source:** DuckDuckGo via Jina Reader  \n")
    lines.append("---\n")

    # Section 1: Keywords
    lines.append("## 一、Keywords Discovered\n")
    if kw_path and os.path.exists(kw_path):
        with open(kw_path) as f:
            content = f.read()
        # Extract keyword table + summary (skip header metadata)
        in_table = False
        for line in content.split('\n'):
            if line.startswith('| '):
                in_table = True
                lines.append(line + '\n')
            elif in_table and line.strip() == '':
                in_table = False
                lines.append('\n')
            elif in_table:
                lines.append(line + '\n')
    else:
        lines.append("_No keyword data._\n")

    lines.append("---\n")

    # Section 2: SERP Analysis
    lines.append("## 二、SERP Competition Analysis\n")
    if serp_path and os.path.exists(serp_path):
        with open(serp_path) as f:
            lines.append(f.read())
    else:
        lines.append("_Run serp-analyzer for detailed competition data._\n")

    lines.append("---\n")

    # Section 3: Content Brief
    lines.append("## 三、Content Brief (Top Keyword)\n")
    if brief_path and os.path.exists(brief_path):
        with open(brief_path) as f:
            lines.append(f.read())
    else:
        lines.append("_No content brief generated._\n")

    lines.append("---\n")

    # Section 4: Google SEO Optimization (optional)
    if optimize_path and os.path.exists(optimize_path):
        lines.append("## 四、Google SEO Optimization\n")
        with open(optimize_path) as f:
            content = f.read()
        # Skip the title (already have it in the heading)
        content_lines = content.split('\n')
        for line in content_lines[2:]:  # skip first two lines (title + blank)
            lines.append(line + '\n')
        lines.append("\n---\n")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = ArgumentParser(description="SEO Content Research Pipeline")
    parser.add_argument("--product", required=True, help="Product name")
    parser.add_argument("--countries", default="us", help="Comma-separated country codes")
    parser.add_argument("--output", default="", help="Output report path (default: stdout)")
    parser.add_argument("--google", action="store_true",
                        help="Try Google-quality results via Startpage (may hit captcha)")
    parser.add_argument("--brief-keyword", help="Override the keyword for content brief (optional)")
    parser.add_argument("--optimize", action="store_true",
                        help="Add Google SEO optimization section to report")
    parser.add_argument("--write", action="store_true",
                        help="Generate article writing prompt from research data")
    args = parser.parse_args()

    tmpdir = tempfile.mkdtemp(prefix="seo-pipeline-")
    kw_path = os.path.join(tmpdir, "keywords.md")
    serp_path = os.path.join(tmpdir, "serp.md")
    brief_path = os.path.join(tmpdir, "brief.md")

    print(f"\n🚀 SEO Pipeline: {args.product} → {args.countries}", file=sys.stderr)
    print(f"   Temp dir: {tmpdir}", file=sys.stderr)

    # ─── Step 1: Keyword Discovery ───
    kw_args = ["--product", args.product, "--countries", args.countries,
               "--output", kw_path]
    if args.google:
        kw_args.append("--google")

    kw_result = run_step("keyword-finder.py", kw_args, "Keyword Discovery")
    if not kw_result:
        print("\n❌ Pipeline failed at keyword discovery", file=sys.stderr)
        sys.exit(1)

    # ─── Step 2: SERP Analysis ───
    top_kws = extract_top_keywords(kw_path, max_n=5)
    if top_kws:
        print(f"\n   Top keywords for SERP analysis: {top_kws}", file=sys.stderr)
        serp_args = ["--country", args.countries.split(",")[0],
                     "--output", serp_path,
                     "--keyword", top_kws[0]]
        # Pass additional keywords
        for kw in top_kws[1:]:
            serp_args.extend(["--keyword", kw])

        serp_result = run_step("serp-analyzer.py", serp_args, "SERP Analysis")

    # ─── Step 3: Content Brief ───
    brief_kw = args.brief_keyword or (top_kws[0] if top_kws else args.product)
    print(f"\n   Generating brief for: {brief_kw}", file=sys.stderr)
    brief_args = ["--keyword", brief_kw,
                  "--country", args.countries.split(",")[0],
                  "--output", brief_path]
    brief_result = run_step("content-brief-gen.py", brief_args, "Content Brief")

    # ─── Step 4: Google SEO Optimization (optional) ───
    optimize_path = ""
    if args.optimize:
        optimize_path = os.path.join(tmpdir, "optimize.md")
        opt_args = ["--keyword", brief_kw,
                     "--country", args.countries.split(",")[0],
                     "--output", optimize_path]
        opt_result = run_step("seo-optimizer.py", opt_args, "Google SEO Optimization")

    # ─── Step 5: Competitor Research (only with --write) ───
    gap_path = ""
    if args.write and serp_result:
        gap_path = os.path.join(tmpdir, "gaps.md")
        gap_args = ["--keyword", brief_kw,
                    "--serp", serp_path,
                    "--output", gap_path]
        gap_result = run_step("competitor-research.py", gap_args, "Competitor Research")

    # ─── Step 6: Article Writing Prompt (only with --write) ───
    write_prompt_path = ""
    if args.write:
        write_prompt_path = os.path.join(tmpdir, "write-prompt.md")
        write_args = ["--keyword", brief_kw,
                      "--country", args.countries.split(",")[0],
                      "--brief", brief_path,
                      "--seo", optimize_path if optimize_path else "",
                      "--serp", serp_path if serp_result else "",
                      "--gaps", gap_path if gap_path else "",
                      "--output", write_prompt_path]
        write_result = run_step("article-writer.py", write_args, "Article Writing Prompt")

    # ─── Step 6: Build Report ───
    report = build_report(
        args.product, args.countries,
        kw_path,
        serp_path if serp_result else None,
        brief_path if brief_result else None,
        optimize_path if args.optimize and os.path.exists(optimize_path) else None,
    )

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\n✅ Report written to {args.output}", file=sys.stderr)
        # Also print stdout for piping
        print(report)
    else:
        print(report)

    # Cleanup: remove temp dir
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"\n✅ Pipeline complete", file=sys.stderr)
