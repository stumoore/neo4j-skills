#!/usr/bin/env python3
"""
Tests for extract-references.py
Run from the repo root: python3 scripts/test-extract-references.py
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

# Load module under test
spec = importlib.util.spec_from_file_location("extract", "scripts/extract-references.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

REPO_ROOT = Path(".")
CYPHER_SRC = REPO_ROOT / "docs-cypher/modules/ROOT/pages"
CHEAT_SRC = REPO_ROOT / "docs-cheat-sheet/modules/ROOT/pages"
GQL_EXCLUDE = ["LET", "FINISH", "FILTER", "NEXT", "INSERT"]

failures = []


def check(name: str, condition: bool, msg: str = ""):
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f": {msg}" if msg else ""))
        failures.append(name)


# ---------------------------------------------------------------------------
# Test 1: dry-run prints planned files without writing
# ---------------------------------------------------------------------------
print("\n--- Test 1: dry-run mode ---")
with tempfile.TemporaryDirectory() as tmpdir:
    out_dir = Path(tmpdir) / "refs"
    rc = os.system(
        f"python3 scripts/extract-references.py --dry-run --out {out_dir} > /dev/null 2>&1"
    )
    check("dry-run exits 0", rc == 0)
    check("dry-run does not create output dir", not out_dir.exists())


# ---------------------------------------------------------------------------
# Test 2: Source header format
# ---------------------------------------------------------------------------
print("\n--- Test 2: Source header ---")
with tempfile.TemporaryDirectory() as tmpdir:
    out_dir = Path(tmpdir) / "refs"
    os.system(
        f"python3 scripts/extract-references.py --only cypher25-patterns.md --out {out_dir} > /dev/null 2>&1"
    )
    out_file = out_dir / "cypher25-patterns.md"
    check("output file created", out_file.exists())
    if out_file.exists():
        content = out_file.read_text()
        check("header contains '> Source:'", "> Source:" in content)
        check("header contains '> Generated:'", "> Generated:" in content)
        check("header contains SHA", "238ab12a" in content or "e11fe2f2" in content)


# ---------------------------------------------------------------------------
# Test 3: GQL exclusion — headings
# ---------------------------------------------------------------------------
print("\n--- Test 3: GQL exclusion (headings) ---")
sample_adoc = """\
= Test doc

== LET

Some text about LET.

== Normal section

Normal content here.

== FINISH

Some FINISH content.
"""
result = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE)
check("LET heading excluded", "# LET" not in result and "## LET" not in result)
check("FINISH heading excluded", "# FINISH" not in result and "## FINISH" not in result)
check("Normal section preserved", "Normal section" in result)
check("Normal content preserved", "Normal content here" in result)


# ---------------------------------------------------------------------------
# Test 4: Section-not-found WARNING
# ---------------------------------------------------------------------------
print("\n--- Test 4: Missing section WARNING ---")
import io
import contextlib

styleguide = CYPHER_SRC / "styleguide.adoc"
if styleguide.exists():
    stderr_capture = io.StringIO()
    with contextlib.redirect_stderr(stderr_capture):
        _, warnings = mod.extract_file(
            styleguide,
            gql_exclude=GQL_EXCLUDE,
            max_tokens=4000,
            expected_sections=["NONEXISTENT SECTION XYZ"],
        )
    stderr_out = stderr_capture.getvalue()
    check("WARNING in warnings list", any("WARNING: section not found" in w for w in warnings))
    check("WARNING written to stderr", "WARNING: section not found" in stderr_out)
else:
    print("  SKIP  styleguide.adoc not found")


# ---------------------------------------------------------------------------
# Test 5: Token budget enforcement
# ---------------------------------------------------------------------------
print("\n--- Test 5: Token budget ---")
with tempfile.TemporaryDirectory() as tmpdir:
    out_dir = Path(tmpdir) / "refs"
    os.system(
        f"python3 scripts/extract-references.py --max-tokens 2000 --out {out_dir} > /dev/null 2>&1"
    )
    over_budget = []
    for md_file in out_dir.glob("*.md"):
        size = md_file.stat().st_size
        approx_tokens = size // 4
        if approx_tokens > 2000:
            over_budget.append(f"{md_file.name}: ~{approx_tokens} tokens")
    check(
        "all output files ≤ 2000 tokens",
        len(over_budget) == 0,
        "; ".join(over_budget),
    )


# ---------------------------------------------------------------------------
# Test 6: Code fence language tags
# ---------------------------------------------------------------------------
print("\n--- Test 6: Code fence language tags ---")
sample_adoc = """\
= Test

[source, cypher]
----
MATCH (n) RETURN n
----

[source, role=noheader]
----
something
----
"""
result = mod.adoc_to_markdown(sample_adoc, GQL_EXCLUDE)
check("cypher fence has language tag", "```cypher" in result)
check("noheader fence has no 'role' tag", "```role" not in result)


# ---------------------------------------------------------------------------
# Test 7: flags accepted (CLI help)
# ---------------------------------------------------------------------------
print("\n--- Test 7: CLI flags accepted ---")
rc = os.system("python3 scripts/extract-references.py --help > /dev/null 2>&1")
check("--help exits 0", rc == 0)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if failures:
    print(f"FAILED: {len(failures)} test(s): {', '.join(failures)}")
    sys.exit(1)
else:
    print(f"ALL TESTS PASSED")
    sys.exit(0)
