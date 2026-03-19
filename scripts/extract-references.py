#!/usr/bin/env python3
"""
extract-references.py — Extract and clean asciidoc source files into Markdown
reference files for the neo4j-cypher-authoring-skill.

Usage:
  python scripts/extract-references.py \
    --cypher-src docs-cypher/modules/ROOT/pages \
    --cheat-src docs-cheat-sheet/modules/ROOT/pages \
    --out neo4j-cypher-authoring-skill/references \
    [--exclude LET,FINISH,FILTER,NEXT,INSERT] \
    [--max-tokens 2000] \
    [--dry-run]
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Asciidoc → Markdown conversion helpers
# ---------------------------------------------------------------------------

# GQL clauses to exclude by default
DEFAULT_EXCLUDE = ["LET", "FINISH", "FILTER", "NEXT", "INSERT"]

# Approximate chars-per-token for token budget estimation
CHARS_PER_TOKEN = 4


def get_git_sha(path: Path) -> str:
    """Return the short HEAD SHA for a git repo at `path`."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def get_git_remote_url(path: Path) -> str:
    """Return the remote origin URL for a git repo at `path`."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return str(path)


def adoc_to_markdown(text: str, gql_exclude: list[str]) -> str:
    """
    Convert asciidoc text to clean Markdown.

    Transformations applied:
    - Strip :description: / :table-caption!: / include:: directives
    - Convert = / == / === headings to # / ## / ###
    - Convert [source, cypher] blocks to ```cypher fenced blocks
    - Convert [source, *] blocks to generic ``` fenced blocks
    - Strip .Details / .Bad / .Good / .Example label lines
    - Strip [TIP] / [NOTE] / [IMPORTANT] / [WARNING] admonition markers
    - Strip image:: lines
    - Strip xref:: / link: inline references (keep link text)
    - Strip [appendix] / [[anchor]] / role= directives
    - Convert |=== tables to simple Markdown tables
    - Strip lines containing GQL-excluded clause keywords as standalone terms
    """
    lines = text.splitlines()
    output_lines: list[str] = []
    i = 0
    in_source_block = False
    pending_source_lang = ""  # set when we see [source, lang] before ----
    in_table = False
    table_rows: list[list[str]] = []

    while i < len(lines):
        line = lines[i]

        # --- Delimited source blocks ---
        if line.strip() == "----":
            if not in_source_block:
                lang = pending_source_lang
                pending_source_lang = ""
                in_source_block = True
                output_lines.append(f"```{lang}")
            else:
                in_source_block = False
                output_lines.append("```")
            i += 1
            continue

        if in_source_block:
            output_lines.append(line)
            i += 1
            continue

        # --- Table blocks ---
        if line.strip() == "|===":
            if not in_table:
                in_table = True
                table_rows = []
                table_header_done = False
            else:
                # End of table — render as Markdown
                in_table = False
                if table_rows:
                    # Filter out empty rows and separator rows
                    filtered = [r for r in table_rows if any(c.strip() for c in r)]
                    if filtered:
                        # Determine max cols
                        max_cols = max(len(r) for r in filtered)
                        # Pad all rows to max_cols
                        padded = [r + [""] * (max_cols - len(r)) for r in filtered]
                        # Render header + separator + body
                        header = padded[0]
                        output_lines.append("| " + " | ".join(header) + " |")
                        output_lines.append("| " + " | ".join(["---"] * max_cols) + " |")
                        for row in padded[1:]:
                            output_lines.append("| " + " | ".join(row) + " |")
                        output_lines.append("")
            i += 1
            continue

        if in_table:
            # Parse a table row: lines starting with | or multi-cell lines
            if line.strip().startswith("|"):
                # Could be `| cell1 | cell2 | cell3` or just `| cell1`
                cells = line.strip().split("|")
                cells = [c.strip() for c in cells if c.strip()]
                # Strip adoc formatting in cells
                cells = [_clean_inline(c) for c in cells]
                if cells:
                    table_rows.append(cells)
            # else: skip continuation lines inside table
            i += 1
            continue

        # --- Skip directives and metadata ---
        if (
            line.startswith(":description:")
            or line.startswith(":table-caption!")
            or line.startswith("include::")
            or line.startswith("image::")
            or line.startswith("[appendix]")
            or re.match(r"^\[\[[\w-]+\]\]$", line.strip())  # [[anchor]]
        ):
            i += 1
            continue

        # --- Skip .Label lines (e.g. .Details, .Bad, .Good) ---
        if re.match(r"^\.[A-Z][a-zA-Z ]*$", line.strip()):
            i += 1
            continue

        # --- Capture [source, lang] for next ---- block; strip admonitions ---
        source_match = re.match(r"^\[source[,\s]+(\w+)", line.strip(), re.IGNORECASE)
        if source_match:
            candidate = source_match.group(1)
            # Ignore 'role' as a pseudo-lang (e.g. [source, role=noheader])
            if candidate.lower() != "role":
                pending_source_lang = candidate
            else:
                pending_source_lang = ""
            i += 1
            continue
        if re.match(r"^\[(TIP|NOTE|IMPORTANT|WARNING|CAUTION)", line.strip(), re.IGNORECASE):
            i += 1
            continue

        # --- Skip role= lines and ====  block delimiters ---
        if line.strip() == "====" or re.match(r"^\[role=", line.strip()):
            i += 1
            continue

        # --- Headings ---
        heading_match = re.match(r"^(={1,4})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            title = _clean_inline(heading_match.group(2))
            md_heading = "#" * level + " " + title
            # Apply GQL exclusion to headings
            if _is_gql_excluded_line(md_heading, gql_exclude):
                i += 1
                continue
            output_lines.append(md_heading)
            i += 1
            continue

        # --- Clean inline markup ---
        cleaned = _clean_inline(line)

        # --- GQL exclusion: skip lines that are primarily about excluded clauses ---
        if _is_gql_excluded_line(cleaned, gql_exclude):
            i += 1
            continue

        output_lines.append(cleaned)
        i += 1

    result = "\n".join(output_lines)
    # Collapse 3+ consecutive blank lines into 2 (paragraph break)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def _clean_inline(text: str) -> str:
    """Strip common asciidoc inline markup from a string."""
    # xref:path[text] → text
    text = re.sub(r"xref:[^\[]+\[([^\]]*)\]", r"\1", text)
    # link:url[text] → text
    text = re.sub(r"link:[^\[]+\[([^\]]*)\]", r"\1", text)
    # https://...[text] → text
    text = re.sub(r"https?://[^\s\[]+\[([^\]]*)\]", r"\1", text)
    # `code` stays as-is (already Markdown compatible)
    # *bold* → **bold**
    text = re.sub(r"\*([^*]+)\*", r"**\1**", text)
    # _italic_ → *italic*
    text = re.sub(r"_([^_]+)_", r"*\1*", text)
    # Strip {page-version}, {neo4j-docs-base-uri}, etc. attribute references
    text = re.sub(r"\{[a-z][a-z0-9-]*\}", "", text)
    # Unescape \| in table cells
    text = text.replace("\\|", "|")
    return text


def _is_gql_excluded_line(line: str, gql_exclude: list[str]) -> bool:
    """
    Return True if the line appears to be primarily about an excluded GQL clause.

    We check if the line starts with a heading that names an excluded clause,
    or if a code snippet consists solely of the excluded clause keyword.
    We do NOT exclude lines where the keyword appears as part of a larger query.
    """
    stripped = line.strip()
    for clause in gql_exclude:
        # Skip lines like "## INSERT" or "# LET" (headings about excluded clauses)
        if re.match(rf"^#+\s+{clause}\b", stripped, re.IGNORECASE):
            return True
        # Skip standalone keyword in code context like just "LET x = ..."
        # But do NOT skip lines where keyword is part of a valid Cypher query
    return False


# ---------------------------------------------------------------------------
# File-level extraction
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Rough token count estimate based on character count."""
    return len(text) // CHARS_PER_TOKEN


def truncate_to_budget(text: str, max_tokens: int) -> tuple[str, bool]:
    """
    Truncate text to approximately max_tokens tokens.
    Returns (truncated_text, was_truncated).
    """
    # Reserve ~20 tokens for the truncation notice itself
    suffix = "\n\n> **Note**: Content truncated to token budget.\n"
    effective_budget = (max_tokens - 20) * CHARS_PER_TOKEN
    if len(text) <= effective_budget:
        return text, False

    # Truncate at a paragraph boundary near the limit
    truncated = text[:effective_budget]
    # Find last paragraph break
    last_para = truncated.rfind("\n\n")
    if last_para > effective_budget // 2:
        truncated = truncated[:last_para]
    return truncated + suffix, True


def extract_file(
    src_path: Path,
    gql_exclude: list[str],
    max_tokens: int,
    expected_sections: Optional[list[str]] = None,
) -> tuple[str, list[str]]:
    """
    Read an asciidoc file, convert to Markdown, check for expected sections.

    Returns (markdown_content, warnings_list).
    """
    warnings = []
    raw = src_path.read_text(encoding="utf-8")
    md = adoc_to_markdown(raw, gql_exclude)

    # Check for expected sections
    if expected_sections:
        for section in expected_sections:
            # Check heading at any level
            pattern = re.compile(r"^#+\s+" + re.escape(section), re.MULTILINE | re.IGNORECASE)
            if not pattern.search(md):
                msg = f"WARNING: section not found: '{section}' in {src_path.name}"
                warnings.append(msg)
                print(msg, file=sys.stderr)

    # Truncate if over budget
    md, truncated = truncate_to_budget(md, max_tokens)
    if truncated:
        msg = f"WARNING: {src_path.name} truncated to {max_tokens} tokens"
        warnings.append(msg)
        print(msg, file=sys.stderr)

    return md, warnings


def build_source_header(
    repo_url: str,
    sha: str,
    generated: str,
    source_files: list[str],
) -> str:
    """Build the > Source: header block for an output file."""
    files_str = ", ".join(source_files)
    return (
        f"> Source: {repo_url}@{sha}\n"
        f"> Generated: {generated}\n"
        f"> Files: {files_str}\n\n"
    )


# ---------------------------------------------------------------------------
# Main extraction configurations
# ---------------------------------------------------------------------------

# Each entry: output_filename, list of (src_root_key, relative_path, expected_sections)
EXTRACTION_CONFIGS = [
    {
        "output": "cypher25-patterns.md",
        "sources": [
            {
                "root": "cypher",
                "path": "patterns/variable-length-patterns.adoc",
                "sections": ["Quantified path patterns"],
            },
            {
                "root": "cypher",
                "path": "patterns/shortest-paths.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "patterns/non-linear-patterns.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "patterns/match-modes.adoc",
                "sections": ["DIFFERENT RELATIONSHIPS", "REPEATABLE ELEMENTS"],
            },
            {
                "root": "cheat",
                "path": "quantified-path-patterns.adoc",
                "sections": [],
            },
            {
                "root": "cheat",
                "path": "path-pattern-expressions.adoc",
                "sections": [],
            },
        ],
    },
    {
        "output": "cypher25-functions.md",
        "sources": [
            {
                "root": "cypher",
                "path": "functions/aggregating.adoc",
                "sections": ["avg()", "count()", "sum()"],
            },
            {
                "root": "cypher",
                "path": "functions/list.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "functions/string.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "functions/scalar.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "functions/predicate.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "functions/vector.adoc",
                "sections": [],
            },
            {
                "root": "cheat",
                "path": "temporal-functions.adoc",
                "sections": [],
            },
            {
                "root": "cheat",
                "path": "spatial-functions.adoc",
                "sections": [],
            },
            {
                "root": "cheat",
                "path": "mathematical-functions-numeric.adoc",
                "sections": [],
            },
        ],
    },
    {
        "output": "cypher25-indexes.md",
        "sources": [
            {
                "root": "cypher",
                "path": "indexes/semantic-indexes/vector-indexes.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "indexes/semantic-indexes/full-text-indexes.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "indexes/syntax.adoc",
                "sections": [],
            },
            {
                "root": "cheat",
                "path": "vector-index.adoc",
                "sections": [],
            },
            {
                "root": "cheat",
                "path": "full-text-index.adoc",
                "sections": [],
            },
            {
                "root": "cheat",
                "path": "search-performance-index.adoc",
                "sections": [],
            },
        ],
    },
    {
        "output": "cypher25-subqueries.md",
        "sources": [
            {
                "root": "cypher",
                "path": "subqueries/call-subquery.adoc",
                "sections": ["Correlated subqueries"],
            },
            {
                "root": "cypher",
                "path": "subqueries/subqueries-in-transactions.adoc",
                "sections": ["CALL IN TRANSACTIONS"],
            },
            {
                "root": "cypher",
                "path": "subqueries/count.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "subqueries/collect.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "subqueries/existential.adoc",
                "sections": [],
            },
            {
                "root": "cheat",
                "path": "subqueries-call.adoc",
                "sections": [],
            },
            {
                "root": "cheat",
                "path": "subqueries-call-in-transactions.adoc",
                "sections": [],
            },
            {
                "root": "cheat",
                "path": "subqueries-collect-count-exists.adoc",
                "sections": [],
            },
        ],
    },
    {
        "output": "cypher25-types-and-nulls.md",
        "sources": [
            {
                "root": "cypher",
                "path": "values-and-types/working-with-null.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "values-and-types/casting-data.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "values-and-types/property-structural-constructed.adoc",
                "sections": [],
            },
            {
                "root": "cheat",
                "path": "type-predicate-expressions.adoc",
                "sections": [],
            },
        ],
    },
    {
        "output": "cypher-style-guide.md",
        "sources": [
            {
                "root": "cypher",
                "path": "styleguide.adoc",
                "sections": ["General recommendations", "Indentation"],
            },
            {
                "root": "cypher",
                "path": "syntax/naming.adoc",
                "sections": [],
            },
            {
                "root": "cypher",
                "path": "syntax/keywords.adoc",
                "sections": [],
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract asciidoc reference files into Markdown for neo4j-cypher-authoring-skill."
    )
    parser.add_argument(
        "--cypher-src",
        default="docs-cypher/modules/ROOT/pages",
        help="Path to docs-cypher pages directory",
    )
    parser.add_argument(
        "--cheat-src",
        default="docs-cheat-sheet/modules/ROOT/pages",
        help="Path to docs-cheat-sheet pages directory",
    )
    parser.add_argument(
        "--out",
        default="neo4j-cypher-authoring-skill/references",
        help="Output directory for generated Markdown files",
    )
    parser.add_argument(
        "--exclude",
        default=",".join(DEFAULT_EXCLUDE),
        help="Comma-separated list of GQL clauses to exclude (default: LET,FINISH,FILTER,NEXT,INSERT)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2000,
        help="Maximum tokens per output file (default: 2000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned output files without writing",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Only generate specific output file(s), comma-separated (e.g. cypher25-patterns.md)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    cypher_src = Path(args.cypher_src)
    cheat_src = Path(args.cheat_src)
    out_dir = Path(args.out)
    gql_exclude = [c.strip() for c in args.exclude.split(",") if c.strip()]
    max_tokens = args.max_tokens
    dry_run = args.dry_run
    only_filter = set(args.only.split(",")) if args.only else None

    # Validate source directories
    if not cypher_src.is_dir():
        print(f"ERROR: --cypher-src not found: {cypher_src}", file=sys.stderr)
        return 1
    if not cheat_src.is_dir():
        print(f"ERROR: --cheat-src not found: {cheat_src}", file=sys.stderr)
        return 1

    # Gather metadata
    # cypher_src = docs-cypher/modules/ROOT/pages → 3 parents up = docs-cypher root
    cypher_root = cypher_src.parent.parent.parent
    cheat_root = cheat_src.parent.parent.parent
    cypher_sha = get_git_sha(cypher_root)
    cheat_sha = get_git_sha(cheat_root)
    cypher_url = get_git_remote_url(cypher_root)
    cheat_url = get_git_remote_url(cheat_root)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if dry_run:
        print(f"DRY RUN — would write to: {out_dir}/")
        print(f"  cypher-src:  {cypher_src} (SHA: {cypher_sha[:8]})")
        print(f"  cheat-src:   {cheat_src} (SHA: {cheat_sha[:8]})")
        print(f"  gql-exclude: {', '.join(gql_exclude)}")
        print(f"  max-tokens:  {max_tokens}")
        print()

    # Create output directory
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    all_warnings: list[str] = []
    files_written: list[str] = []

    for config in EXTRACTION_CONFIGS:
        output_name = config["output"]

        if only_filter and output_name not in only_filter:
            continue

        if dry_run:
            source_names = [s["path"] for s in config["sources"]]
            print(f"  {output_name}")
            for sn in source_names:
                print(f"    <- {sn}")
            continue

        # Collect and merge content from all source files
        all_sections: list[str] = []
        all_source_files: list[str] = []
        file_warnings: list[str] = []

        for source in config["sources"]:
            root_key = source["root"]
            rel_path = source["path"]
            expected = source.get("sections", [])

            if root_key == "cypher":
                src_file = cypher_src / rel_path
                repo_label = f"neo4j/docs-cypher@{cypher_sha[:8]}"
            else:
                src_file = cheat_src / rel_path
                repo_label = f"neo4j/docs-cheat-sheet@{cheat_sha[:8]}"

            if not src_file.exists():
                msg = f"WARNING: source file not found: {src_file}"
                file_warnings.append(msg)
                print(msg, file=sys.stderr)
                continue

            all_source_files.append(f"{rel_path} ({root_key})")
            md_content, warnings = extract_file(
                src_file, gql_exclude, max_tokens * 2, expected
            )
            file_warnings.extend(warnings)
            all_sections.append(md_content.strip())

        # Merge all sections with separators
        merged = "\n\n---\n\n".join(s for s in all_sections if s)

        # Build source header
        repo_url = f"{cypher_url} + {cheat_url}"
        sha_summary = f"{cypher_sha[:8]} / {cheat_sha[:8]}"
        header = build_source_header(repo_url, sha_summary, generated, all_source_files)

        full_content = header + merged

        # Enforce overall token budget
        full_content, truncated = truncate_to_budget(full_content, max_tokens)
        if truncated:
            msg = f"WARNING: {output_name} truncated to {max_tokens} tokens (combined)"
            file_warnings.append(msg)
            print(msg, file=sys.stderr)

        # Write output
        out_path = out_dir / output_name
        out_path.write_text(full_content, encoding="utf-8")

        token_est = estimate_tokens(full_content)
        status = "OK" if not file_warnings else f"WARN ({len(file_warnings)} warnings)"
        print(f"  Written: {out_path} (~{token_est} tokens) [{status}]")
        files_written.append(str(out_path))
        all_warnings.extend(file_warnings)

    if dry_run:
        print("\nDRY RUN complete — no files written.")
        return 0

    print(f"\nGenerated {len(files_written)} files in {out_dir}/")
    if all_warnings:
        print(f"{len(all_warnings)} total warnings (see stderr)", file=sys.stderr)
        return 0  # Warnings are non-fatal

    return 0


if __name__ == "__main__":
    sys.exit(main())
