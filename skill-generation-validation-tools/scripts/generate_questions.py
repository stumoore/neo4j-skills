#!/usr/bin/env python3
"""
generate_questions.py — Question generation CLI for neo4j-skills test harness.

Generates new test case questions for a given domain, validates them as
business-user language, auto-rewrites technical questions, generates candidate
Cypher via Claude, executes against live DB to capture baselines, and appends
cases to the domain YAML file.

Usage:
    uv run --project skill-generation-validation-tools python3 \\
        skill-generation-validation-tools/scripts/generate_questions.py \\
        --domain companies \\
        --count 25 \\
        --model sonnet \\
        --difficulties basic,intermediate,advanced,complex,expert \\
        --cases-dir skill-generation-validation-tools/tests/cases/ \\
        --skill neo4j-cypher-authoring-skill

Environment variables:
    NEO4J_URI       — default from database: block in domain YAML
    NEO4J_USERNAME  — default from database: block in domain YAML
    NEO4J_PASSWORD  — default from database: block in domain YAML
    ANTHROPIC_API_KEY — required for Claude API calls

Makefile target:
    make generate-questions DOMAIN=companies COUNT=25 MODEL=haiku
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent
_HARNESS_DIR = _HERE.parent / "tests" / "harness"
sys.path.insert(0, str(_HARNESS_DIR))

# ---------------------------------------------------------------------------
# Driver-level timeout constant (matches validator.py)
# ---------------------------------------------------------------------------

_QUERY_TIMEOUT_S: int = 30
"""Timeout in seconds passed to every driver.execute_query() / tx call."""

try:
    from neo4j import Query as _Neo4jQuery  # type: ignore
except ImportError:
    _Neo4jQuery = None  # type: ignore


def _query_with_timeout(cypher: str) -> Any:
    """Wrap cypher in neo4j.Query with timeout set. Falls back to raw string."""
    if _Neo4jQuery is not None:
        return _Neo4jQuery(cypher, timeout=_QUERY_TIMEOUT_S)
    return cypher


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

try:
    import yaml  # type: ignore

    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


def _require_yaml() -> None:
    if not _YAML_AVAILABLE:
        print("ERROR: pyyaml is required. Install with: uv add pyyaml", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Model ID mapping (mirrors runner.py / generator.py)
# ---------------------------------------------------------------------------

_MODEL_MAP: dict[str, str] = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-5",
    "haiku": "claude-haiku-4-5",
}
_DEFAULT_MODEL_ID = "claude-sonnet-4-6"


def resolve_model_id(model_short: Optional[str]) -> str:
    """Resolve short model name to full model ID; pass-through full IDs unchanged."""
    if model_short is None:
        return _DEFAULT_MODEL_ID
    return _MODEL_MAP.get(model_short, model_short)


# ---------------------------------------------------------------------------
# YAML domain file loading / saving
# ---------------------------------------------------------------------------

_VALID_DIFFICULTIES = ["basic", "intermediate", "advanced", "complex", "expert"]


def _load_domain_yaml(domain_path: Path) -> dict[str, Any]:
    """Load a domain YAML file and return its contents."""
    if not _YAML_AVAILABLE:
        _require_yaml()
    with open(domain_path) as f:
        return yaml.safe_load(f) or {}


def _save_domain_yaml(domain_path: Path, data: dict[str, Any]) -> None:
    """Save domain YAML data back to file, preserving human-friendly formatting."""
    if not _YAML_AVAILABLE:
        _require_yaml()
    with open(domain_path, "w") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=120)


def _next_case_id(cases: list[dict[str, Any]], domain: str, difficulty: str) -> str:
    """
    Compute the next sequential case ID for a domain+difficulty pair.

    Scans existing IDs of the form '{domain}-{difficulty}-NNN' and returns
    the next integer (zero-padded to 3 digits).
    """
    prefix = f"{domain}-{difficulty}-"
    max_n = 0
    for case in cases:
        cid = str(case.get("id", ""))
        if cid.startswith(prefix):
            try:
                n = int(cid[len(prefix) :])
                max_n = max(max_n, n)
            except ValueError:
                pass
    return f"{prefix}{max_n + 1:03d}"


# ---------------------------------------------------------------------------
# Neo4j driver
# ---------------------------------------------------------------------------


def _get_driver(uri: str, username: str, password: str) -> Any:
    """Create and return a neo4j driver; exits on ImportError."""
    try:
        import neo4j  # type: ignore
    except ImportError:
        print("ERROR: neo4j package not installed. Install with: uv add neo4j", file=sys.stderr)
        sys.exit(1)
    return neo4j.GraphDatabase.driver(uri, auth=(username, password))


# ---------------------------------------------------------------------------
# Schema formatting for prompt injection
# ---------------------------------------------------------------------------


def _format_dataset_schema_for_prompt(dataset: dict[str, Any], db_block: dict[str, Any]) -> str:
    """
    Format the dataset schema into a concise string for injection into Claude prompts.
    Delegates to runner._format_dataset_schema if available, otherwise builds inline.
    """
    try:
        from runner import _format_dataset_schema  # type: ignore

        return _format_dataset_schema(dataset, db_block)
    except ImportError:
        pass

    # Fallback: minimal inline formatter
    lines: list[str] = []
    name = dataset.get("name", "unknown")
    database = db_block.get("database", name)
    description = str(dataset.get("description", "")).strip()
    schema = dataset.get("schema", {})
    notes = dataset.get("notes", [])

    lines.append(f"=== DATASET SCHEMA: {name} (database: {database}) ===")
    if description:
        lines.append(description)
    neo4j_version = db_block.get("neo4j_version", "")
    cypher_version = db_block.get("cypher_version", "")
    if neo4j_version or cypher_version:
        parts = []
        if neo4j_version:
            parts.append(f"Neo4j {neo4j_version}")
        if cypher_version:
            parts.append(f"Cypher {cypher_version}")
        lines.append(f"Database version: {' / '.join(parts)}")

    nodes = schema.get("nodes", {})
    if nodes:
        lines.append("\nNODES:")
        for label, info in nodes.items():
            if isinstance(info, dict):
                desc = info.get("description", "")
                lines.append(f"  :{label}{' — ' + desc if desc else ''}")
                for prop, pinfo in (info.get("properties") or {}).items():
                    if isinstance(pinfo, dict):
                        ptype = pinfo.get("type", "")
                        samples = pinfo.get("sample") or pinfo.get("values")
                        sample_str = ""
                        if samples and isinstance(samples, list):
                            flat = [s for s in samples[:3] if not isinstance(s, list)]
                            if flat:
                                sample_str = f" e.g. {flat}"
                        lines.append(f"    .{prop}: {ptype}{sample_str}")

    rels = schema.get("relationships", [])
    if rels:
        lines.append("\nRELATIONSHIPS:")
        for rel in rels:
            if isinstance(rel, dict):
                rtype = rel.get("type", "?")
                rfrom = rel.get("from", "?")
                rto = rel.get("to", "?")
                lines.append(f"  (:{rfrom})-[:{rtype}]->(:{rto})")

    indexes = schema.get("indexes", [])
    if indexes:
        lines.append("\nINDEXES:")
        for idx in indexes:
            if isinstance(idx, dict):
                lines.append(f"  {idx.get('name','?')} — {idx.get('type','?')} on {idx.get('on','?')}")
                if idx.get("call"):
                    lines.append(f"    Usage: {idx['call']}")

    if notes:
        lines.append("\nIMPORTANT NOTES:")
        for note in notes:
            lines.append(f"  - {note}")

    lines.append("=========================")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Existing question de-duplication helper
# ---------------------------------------------------------------------------


def _extract_existing_questions(cases: list[dict[str, Any]]) -> list[str]:
    """Return a list of existing question strings from the cases list."""
    return [str(c.get("question", "")) for c in cases if c.get("question")]


# ---------------------------------------------------------------------------
# Claude invocation — question generation
# ---------------------------------------------------------------------------

_GENERATION_SYSTEM = """\
You are an expert at creating test questions for Neo4j graph database queries.
Your task is to generate BUSINESS-USER questions — questions a non-technical analyst,
product manager, or domain expert would ask. Questions must be in plain English with
no technical graph database terminology.

CRITICAL RULES for questions:
1. NO Cypher keywords: MATCH, WHERE, RETURN, WITH, CALL, MERGE, CREATE, DELETE, SET,
   UNION, EXISTS, COUNT, COLLECT, LIMIT, SKIP, DISTINCT, UNWIND, YIELD, USE, SHOW, etc.
2. NO graph label syntax: :Person, :Movie, :Organization, etc.
3. NO relationship type names: HAS_SUBSIDIARY, ACTED_IN, etc.
4. NO dot-access property syntax: .name, .title, movie.released, etc.
5. NO procedure names: gds.*, apoc.*, db.index.*, ai.*, etc.
6. Questions should sound like natural business questions, not database queries.

GOOD examples:
- "Which companies have more than 5 direct subsidiaries?"
- "What are the top 10 highest-rated movies from the 1990s?"
- "Show me accounts that shared a device with a flagged account"

BAD examples (these contain technical terms — do NOT generate these):
- "Find (:Organization)-[:HAS_SUBSIDIARY]->() with depth > 2"
- "MATCH (m:Movie) WHERE m.released > 2000 RETURN m.title"
- "Use gds.pageRank.stream to rank companies"

IMPORTANT: Your response MUST be ONLY a valid JSON object. Do NOT include any text before or after the JSON. Do NOT add explanations, summaries, or section headers. Start your response with { and end with }.

Output ONLY a valid JSON object with this structure:
{
  "questions": [
    {
      "difficulty": "basic",
      "question": "Which companies have no subsidiaries at all?",
      "notes": "Tests NOT EXISTS subquery pattern for absence of relationships",
      "expected_pattern": "not-exists"
    }
  ]
}

Do NOT include candidate Cypher in this output — only questions.
Do NOT include any markdown headers, bullet points, or prose.
"""


def _build_generation_prompt(
    schema_text: str,
    database: str,
    difficulties: list[str],
    count: int,
    existing_questions: list[str],
) -> str:
    """Build the prompt for generating questions."""
    # Distribute count across requested difficulties
    n_per_diff = max(1, count // len(difficulties))
    remainder = count - n_per_diff * len(difficulties)
    distribution = {d: n_per_diff for d in difficulties}
    for d in difficulties[:remainder]:
        distribution[d] += 1

    dist_str = ", ".join(f"{n} {d}" for d, n in distribution.items())

    lines = [
        f"Database: {database}",
        "",
        schema_text,
        "",
        f"Generate exactly {count} questions distributed as: {dist_str}.",
        "",
        "Difficulty descriptions:",
        "  basic:        Simple single-label lookup or count. No traversal, no aggregation.",
        "  intermediate: 1-2 hop relationship traversal or basic aggregation (count, avg, sum).",
        "  advanced:     Multi-hop traversal, path queries, COLLECT subquery, or filtered aggregation.",
        "  complex:      Bounded QPE traversal, multi-pattern matching, conditional logic.",
        "  expert:       Deep QPE, SHORTEST path variants, hybrid search, multi-database.",
        "",
    ]

    if existing_questions:
        # Show ALL existing questions to avoid duplicates
        lines.append("EXISTING questions (do NOT duplicate these):")
        for q in existing_questions:
            lines.append(f"  - {q}")
        lines.append("")

    lines.append(f"Return exactly {count} questions as a JSON object with a 'questions' array.")

    return "\n".join(lines)


def _call_claude_for_questions(
    prompt: str,
    *,
    model_id: str = _DEFAULT_MODEL_ID,
    timeout_s: int = 300,
) -> tuple[list[dict[str, Any]], Optional[str]]:
    """
    Invoke Claude to generate questions.

    Returns (list_of_question_dicts, error_or_None).
    """
    full_prompt = _GENERATION_SYSTEM + "\n\n---\n\n" + prompt
    cmd = ["claude", "--model", model_id, "--print", "--output-format", "text"]

    try:
        result = subprocess.run(
            cmd,
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env={**os.environ},
        )
        if result.returncode != 0:
            err = result.stderr.strip() or f"claude exited {result.returncode}"
            return [], err
        response = result.stdout
    except subprocess.TimeoutExpired:
        return [], f"Claude invocation timed out after {timeout_s}s"
    except FileNotFoundError:
        return [], "claude CLI not found — ensure 'claude' is on PATH"
    except Exception as exc:
        return [], f"Unexpected error: {exc}"

    # Parse JSON from response — try multiple strategies
    stripped = response.strip()

    # Strategy 1: JSON inside a code block (```json ... ```)
    json_match = re.search(r"```(?:json)?\s*\n(.*?)```", stripped, re.DOTALL)
    if json_match:
        candidate = json_match.group(1).strip()
        try:
            data = json.loads(candidate)
            questions = data.get("questions", [])
            if questions:
                return questions, None
        except json.JSONDecodeError:
            pass

    # Strategy 2: Find the outermost JSON object with a "questions" key
    # Search for {"questions": [...]} pattern
    for match in re.finditer(r'\{[^{}]*"questions"\s*:\s*\[', stripped):
        start = match.start()
        # Walk forward to find the matching closing brace
        depth = 0
        for i, ch in enumerate(stripped[start:]):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    candidate = stripped[start:start + i + 1]
                    try:
                        data = json.loads(candidate)
                        questions = data.get("questions", [])
                        if questions:
                            return questions, None
                    except json.JSONDecodeError:
                        break

    # Strategy 3: Any JSON object in the response
    json_obj_match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if json_obj_match:
        candidate = json_obj_match.group(0)
        try:
            data = json.loads(candidate)
            questions = data.get("questions", [])
            if isinstance(questions, list):
                return questions, None
        except json.JSONDecodeError:
            pass

    # Strategy 4: Retry with sonnet if model_id is haiku and all strategies failed
    if model_id != _DEFAULT_MODEL_ID:
        print(f"  WARNING: {model_id} returned non-JSON response, retrying with {_DEFAULT_MODEL_ID}...", flush=True)
        cmd_retry = ["claude", "--model", _DEFAULT_MODEL_ID, "--print", "--output-format", "text"]
        try:
            result_retry = subprocess.run(
                cmd_retry,
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env={**os.environ},
            )
            if result_retry.returncode == 0:
                response2 = result_retry.stdout
                stripped2 = response2.strip()
                json_match2 = re.search(r"```(?:json)?\s*\n(.*?)```", stripped2, re.DOTALL)
                if json_match2:
                    try:
                        data2 = json.loads(json_match2.group(1).strip())
                        qs2 = data2.get("questions", [])
                        if qs2:
                            return qs2, None
                    except json.JSONDecodeError:
                        pass
                json_obj2 = re.search(r"\{.*\}", stripped2, re.DOTALL)
                if json_obj2:
                    try:
                        data2 = json.loads(json_obj2.group(0))
                        qs2 = data2.get("questions", [])
                        if isinstance(qs2, list) and qs2:
                            return qs2, None
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

    return [], f"Failed to parse JSON from Claude response: no valid JSON found\n\nResponse (first 500 chars): {response[:500]}"


# ---------------------------------------------------------------------------
# Rewrite prompt for technical questions
# ---------------------------------------------------------------------------

_REWRITE_SYSTEM = """\
Rewrite the following technical graph database question as a casual business-user question.
The rewritten question must contain NO Cypher keywords, NO label syntax (:Label),
NO relationship type names (ALL_CAPS_UNDERSCORE), NO dot-access (.property),
NO procedure names (gds., apoc., etc.).

The question should sound like something a non-technical manager or analyst would ask.
Keep the same underlying intent.

Return ONLY the rewritten question text — no explanation, no JSON, no quotes.
"""


def _rewrite_question(
    question: str,
    *,
    model_id: str = _DEFAULT_MODEL_ID,
    timeout_s: int = 60,
) -> Optional[str]:
    """
    Ask Claude to rewrite a technical question as business language.

    Returns the rewritten question or None on failure.
    """
    full_prompt = _REWRITE_SYSTEM + f"\n\nOriginal: {question}\n\nRewritten:"
    cmd = ["claude", "--model", model_id, "--print", "--output-format", "text"]

    try:
        result = subprocess.run(
            cmd,
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env={**os.environ},
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Claude invocation — Cypher generation
# ---------------------------------------------------------------------------

_CYPHER_SYSTEM = """\
You are an expert Neo4j Cypher 25 query author. Given a database schema and a business question,
generate a valid, executable Cypher query that answers the question.

RULES:
- Every query MUST begin with CYPHER 25 on the first line.
- Use QPE syntax (-[:REL]{m,n}->) not deprecated [:REL*] patterns.
- Use SHORTEST N instead of shortestPath() / allShortestPaths().
- Use elementId() instead of deprecated id().
- Use CALL (x) { ... } scope syntax — never importing WITH inside CALL.
- Never use label-free MATCH (n) — always include a label.
- Do NOT use GQL-only clauses: LET, FINISH, FILTER, NEXT, INSERT.
- Use toFloatOrNull(), toIntegerOrNull() for type-unsafe conversions.

SUBQUERIES — prefer these Cypher 25 forms:
- Existence check: WHERE EXISTS { (n)-[:R]->(m) WHERE m.prop = x }  (not pattern predicates)
- Counting degree: COUNT { (n)-[:R]->(:Label) }  (not MATCH + count(x) which triggers deprecated NodeCountFromCountStore)
- Collecting: COLLECT { MATCH (n)-[:R]->(m) RETURN m.name ORDER BY m.name LIMIT 10 }  (LIMIT inside COLLECT {} minimizes data retrieved)
- COUNT {} and EXISTS {} accept a bare pattern or full MATCH...RETURN statement.
- COLLECT {} requires a full MATCH...RETURN statement — bare pattern is a syntax error.

PARALLEL RUNTIME — if the schema notes recommend runtime=parallel for global analytics
on a large database, use: CYPHER 25 runtime=parallel  as the first line for aggregate
queries that scan a large fraction of nodes (e.g. avg/count over all nodes of a label).

Return ONLY a JSON object:
{
  "cypher": "CYPHER 25\\nMATCH ...",
  "is_write_query": false
}
"""


BATCH_SYSTEM_PROMPT = """For each question listed, write exactly one JSON line to the output file.
Format: {"id": "<id>", "cypher": "CYPHER 25\\n<query>", "is_write_query": <bool>}
Write each line as soon as it is ready. Do not output anything else."""


def _resolve_test_plugin_dir(skill: str) -> Optional[Path]:
    """
    Locate the test-plugin directory that wraps the local dev skill via symlink.

    The test-plugin structure mirrors a real plugin: skills/<skill-name> -> skill dir.
    This allows --plugin-dir to load the skill properly including WebFetch for L2/L3.
    """
    candidates = [
        Path(__file__).parent.parent / "test-plugin",
        Path(__file__).parent.parent.parent / "skill-generation-validation-tools" / "test-plugin",
    ]
    for p in candidates:
        skill_link = p / "skills" / skill
        if (p / "package.json").exists() and (skill_link.exists() or skill_link.is_symlink()):
            return p
    return None


def _generate_batch_cypher(
    questions: list[dict[str, Any]],
    schema_text: str,
    domain: str,
    db_config: dict[str, Any],
    plugin_dir: Optional[Path],
    *,
    model_id: str = _DEFAULT_MODEL_ID,
    skill: str = "neo4j-cypher-authoring-skill",
    timeout_s: int = 600,
) -> list[dict[str, Any]]:
    """
    Generate Cypher for all questions in a single Claude invocation (batch mode).

    Builds one prompt containing the skill slash command, full schema, and all
    question specs. Claude writes one JSONL line per question to a temp file via
    the Write tool. After claude exits, the temp file is read back and parsed.

    Returns a list of dicts with keys: id, cypher, is_write_query.
    Missing or unparseable lines are omitted — callers should fall back to
    _generate_cypher() for any question ID that is absent from the result.
    """
    plugin_name = "neo4j-skills-test-plugin"
    skill_invocation = f"/{plugin_name}:{skill}" if plugin_dir else ""

    # Create a temp file for JSONL output; claude will write to this path
    tmp_path = tempfile.mktemp(suffix=".jsonl")

    # Build the batch prompt
    database = db_config.get("database", domain)
    lines: list[str] = []
    if skill_invocation:
        lines.append(skill_invocation)
        lines.append("")
    lines.append("## Schema")
    lines.append(schema_text)
    lines.append("")
    lines.append("## Task")
    lines.append(
        f"Generate a valid Cypher 25 query for each question listed below. "
        f"For each question, write exactly one JSON line to the file at: {tmp_path}"
    )
    lines.append(
        'Format per line: {"id": "<id>", "cypher": "CYPHER 25\\n<query>", "is_write_query": <bool>}'
    )
    lines.append(f"Database: {database}")
    lines.append("")
    lines.append("## Questions")
    for i, q in enumerate(questions, 1):
        qid = q.get("_batch_id", "")
        difficulty = q.get("difficulty", "basic")
        question_text = q.get("question", "")
        lines.append(f"{i}. [{qid}] ({difficulty}) {question_text}")
    lines.append("")

    user_prompt = "\n".join(lines)

    cmd = [
        "claude", "--model", model_id,
        "--print", "--output-format", "text",
        "--allowedTools", "Write",
    ]
    if plugin_dir:
        cmd += ["--plugin-dir", str(plugin_dir)]
    cmd += ["--append-system-prompt", BATCH_SYSTEM_PROMPT]

    n = len(questions)
    logger.info(f"batch mode: {n} questions → 1 claude invocation")
    print(f"[batch-cypher] {n} questions → 1 claude invocation (model={model_id})", flush=True)

    try:
        result = subprocess.run(
            cmd,
            input=user_prompt,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env={**os.environ},
        )
        if result.returncode != 0:
            err = result.stderr.strip() or f"claude exited {result.returncode}"
            print(f"[batch-cypher] ERROR: claude returned non-zero: {err[:200]}", file=sys.stderr, flush=True)
            return []
    except subprocess.TimeoutExpired:
        print(f"[batch-cypher] ERROR: timed out after {timeout_s}s", file=sys.stderr, flush=True)
        return []
    except FileNotFoundError:
        print("[batch-cypher] ERROR: claude CLI not found", file=sys.stderr, flush=True)
        return []
    except Exception as exc:
        print(f"[batch-cypher] ERROR: {exc}", file=sys.stderr, flush=True)
        return []

    # Read back the JSONL file
    results: list[dict[str, Any]] = []
    try:
        with open(tmp_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and obj.get("id") and obj.get("cypher"):
                        results.append(obj)
                except json.JSONDecodeError:
                    print(f"[batch-cypher] WARNING: skipping unparseable JSONL line: {line[:100]}", file=sys.stderr)
    except FileNotFoundError:
        print(f"[batch-cypher] WARNING: JSONL output file not found: {tmp_path}", file=sys.stderr, flush=True)
        return []
    except Exception as exc:
        print(f"[batch-cypher] ERROR reading JSONL: {exc}", file=sys.stderr, flush=True)
        return []
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    print(f"[batch-cypher] parsed {len(results)}/{n} lines from JSONL", flush=True)
    return results


def _generate_cypher(
    question: str,
    schema_text: str,
    database: str,
    difficulty: str,
    *,
    model_id: str = _DEFAULT_MODEL_ID,
    skill: str = "neo4j-cypher-authoring-skill",
    timeout_s: int = 120,
) -> tuple[Optional[str], bool, Optional[str]]:
    """
    Generate Cypher using Claude with the skill loaded via --plugin-dir (local dev).

    Uses skill-generation-validation-tools/test-plugin which symlinks the local skill
    directory, allowing --plugin-dir to load it with full WebFetch access for L2/L3
    reference files. _CYPHER_SYSTEM rules are appended to reinforce JSON output format.

    Returns (cypher_string_or_None, is_write_query, error_or_None).
    """
    plugin_dir = _resolve_test_plugin_dir(skill)
    plugin_name = "neo4j-skills-test-plugin"

    if plugin_dir:
        skill_invocation = f"/{plugin_name}:{skill}"
    else:
        print(
            f"[WARN] test-plugin not found for '{skill}' — generating without skill context. "
            "Run: mkdir -p skill-generation-validation-tools/test-plugin/skills && "
            f"ln -s ../../../../{skill} skill-generation-validation-tools/test-plugin/skills/{skill}",
            file=sys.stderr,
            flush=True,
        )
        skill_invocation = ""

    user_prompt = (
        f"{skill_invocation}\n\n" if skill_invocation else ""
    ) + (
        f"{schema_text}\n\n"
        f"Database: {database}\n"
        f"Difficulty: {difficulty}\n\n"
        f"Question: {question}\n\n"
        "Return a JSON object with 'cypher' and 'is_write_query' fields."
    )

    cmd = [
        "claude", "--model", model_id, "--print", "--output-format", "text",
        "--append-system-prompt", _CYPHER_SYSTEM,
    ]
    if plugin_dir:
        cmd += ["--plugin-dir", str(plugin_dir)]

    try:
        result = subprocess.run(
            cmd,
            input=user_prompt,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env={**os.environ},
        )
        if result.returncode != 0:
            err = result.stderr.strip() or f"claude exited {result.returncode}"
            return None, False, err
        response = result.stdout
    except subprocess.TimeoutExpired:
        return None, False, f"Claude invocation timed out after {timeout_s}s"
    except FileNotFoundError:
        return None, False, "claude CLI not found"
    except Exception as exc:
        return None, False, str(exc)

        # Parse response
        stripped = response.strip()
        json_match = re.search(r"```(?:json)?\s*\n(.*?)```", stripped, re.DOTALL)
        if json_match:
            stripped = json_match.group(1).strip()

        json_obj_match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if json_obj_match:
            stripped = json_obj_match.group(0)

        try:
            data = json.loads(stripped)
            cypher = data.get("cypher", "").strip()
            is_write = bool(data.get("is_write_query", False))
            if cypher:
                return cypher, is_write, None
        except json.JSONDecodeError:
            # Try to extract from cypher code block
            m = re.search(r"```(?:cypher|CYPHER)?\s*\n(.*?)```", stripped, re.DOTALL)
            if m:
                return m.group(1).strip(), False, None

    return None, False, "Failed to parse Cypher from response"


# ---------------------------------------------------------------------------
# Execute query and capture basic metrics
# ---------------------------------------------------------------------------

# Difficulty-based performance defaults for Gate 4 thresholds.
# Base values suit small graphs (Northwind, recommendations — ~10K total nodes+rels).
# Call compute_difficulty_defaults(node_count, rel_count) to get graph-scaled values.
_BASE_DIFFICULTY_DEFAULTS: dict[str, dict[str, int]] = {
    "basic":        {"max_db_hits": 10_000,     "max_runtime_ms": 5_000},
    "intermediate": {"max_db_hits": 50_000,     "max_runtime_ms": 10_000},
    "advanced":     {"max_db_hits": 200_000,    "max_runtime_ms": 20_000},
    "complex":      {"max_db_hits": 500_000,    "max_runtime_ms": 30_000},
    "expert":       {"max_db_hits": 2_000_000,  "max_runtime_ms": 60_000},
}

# Max fraction of (nodeCount + relCount) that each difficulty tier may touch.
_GRAPH_FRACTION: dict[str, float] = {
    "basic":        0.5,
    "intermediate": 1.0,
    "advanced":     2.0,
    "complex":      5.0,
    "expert":       10.0,
}

# Hard caps — no tier should exceed these regardless of graph size.
# Large graphs like stackoverflow (~100M nodes+rels) produce 260M+ db-hits for
# reasonable queries that complete in <10s; 500M is the right cap for such graphs.
_DB_HITS_CAP: dict[str, int] = {
    "basic":        500_000_000,
    "intermediate": 500_000_000,
    "advanced":     500_000_000,
    "complex":      1_000_000_000,
    "expert":       2_000_000_000,
}

_DEFAULT_MAX_MEMORY_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB for all tiers


def compute_difficulty_defaults(node_count: int, rel_count: int) -> dict[str, dict[str, int]]:
    """
    Return Gate 4 db_hits and runtime thresholds scaled to the graph size.

    Small graphs (Northwind, recommendations) get the base values.
    Large graphs (stackoverflow, patientjourney) scale proportionally up to the caps.
    """
    graph_size = node_count + rel_count
    result: dict[str, dict[str, int]] = {}
    for diff, base in _BASE_DIFFICULTY_DEFAULTS.items():
        scaled_hits = int(graph_size * _GRAPH_FRACTION[diff])
        max_db_hits = min(_DB_HITS_CAP[diff], max(base["max_db_hits"], scaled_hits))
        # Runtime scales with graph size but capped at 10x the base
        rt_scale = min(10.0, max(1.0, graph_size / 10_000))
        max_runtime_ms = int(base["max_runtime_ms"] * rt_scale)
        result[diff] = {"max_db_hits": max_db_hits, "max_runtime_ms": max_runtime_ms}
    return result


def _query_graph_size(driver: Any, database: str) -> tuple[int, int]:
    """
    Return (node_count, rel_count) for the database using count-store queries (O(1)).
    Falls back to (0, 0) on any error so callers use base defaults.
    """
    try:
        n_rec, _, _ = driver.execute_query(
            "MATCH (n) RETURN count(n) AS c", database_=database
        )
        r_rec, _, _ = driver.execute_query(
            "MATCH ()-[r]->() RETURN count(r) AS c", database_=database
        )
        return int(n_rec[0]["c"]), int(r_rec[0]["c"])
    except Exception:
        return 0, 0


def _execute_query(
    driver: Any,
    database: str,
    cypher: str,
    is_write_query: bool,
) -> dict[str, Any]:
    """
    Execute a query against the DB and return basic metrics.

    For write queries: executes in a rolled-back transaction.
    Returns dict with: actual_rows, execution_ms, db_hits, error.
    db_hits is populated via a PROFILE run for read queries.
    """
    result: dict[str, Any] = {
        "actual_rows": None,
        "execution_ms": None,
        "db_hits": None,
        "error": None,
    }

    try:
        t0 = time.monotonic()
        if is_write_query:
            with driver.session(database=database) as session:
                with session.begin_transaction(timeout=_QUERY_TIMEOUT_S) as tx:
                    try:
                        r = tx.run(cypher)
                        rows = r.data()
                        result["actual_rows"] = len(rows)
                    finally:
                        tx.rollback()
        else:
            records, summary, _ = driver.execute_query(_query_with_timeout(cypher), database_=database)
            result["actual_rows"] = len(records)
            # Attempt PROFILE to capture db_hits for read queries
            try:
                profile_cypher = _prepend_profile(cypher)
                _, profile_summary, _ = driver.execute_query(_query_with_timeout(profile_cypher), database_=database)
                if profile_summary and profile_summary.profile:
                    result["db_hits"] = _sum_plan_db_hits(profile_summary.profile)
            except Exception:
                pass  # PROFILE not critical — continue without db_hits
        result["execution_ms"] = round((time.monotonic() - t0) * 1000, 1)
    except Exception as exc:
        result["error"] = str(exc)

    return result


def _prepend_profile(cypher: str) -> str:
    """Prepend PROFILE to a Cypher query, handling CYPHER 25 pragma."""
    stripped = cypher.strip()
    pragma_match = re.match(r"^(CYPHER\s+\S+)\s*\n", stripped, re.IGNORECASE)
    if pragma_match:
        pragma = pragma_match.group(1)
        rest = stripped[pragma_match.end():]
        return f"{pragma}\nPROFILE\n{rest}"
    return f"PROFILE\n{stripped}"


def _sum_plan_db_hits(plan: Any) -> int:
    """Recursively sum dbHits from a ProfiledPlan object or dict."""
    if hasattr(plan, "db_hits"):
        # Neo4j driver ProfiledPlan
        total = plan.db_hits or 0
        for child in (plan.children or []):
            total += _sum_plan_db_hits(child)
        return total
    if isinstance(plan, dict):
        total = plan.get("dbHits", 0) or 0
        for child in (plan.get("children") or []):
            total += _sum_plan_db_hits(child)
        return total
    return 0


# ---------------------------------------------------------------------------
# YAML case builder
# ---------------------------------------------------------------------------


def _build_case(
    case_id: str,
    question: str,
    difficulty: str,
    notes: str,
    tags: list[str],
    database: str,
    domain: str,
    cypher: Optional[str],
    is_write_query: bool,
    execution: dict[str, Any],
    *,
    needs_review: bool = False,
    validation_failure: Optional[str] = None,
    difficulty_defaults: Optional[dict[str, dict[str, int]]] = None,
) -> dict[str, Any]:
    """Build a case dict for appending to domain YAML."""
    case: dict[str, Any] = {
        "id": case_id,
        "question": question,
        "database": database,
        "domain": domain,
        "difficulty": difficulty,
        "tags": tags or [],
        "is_write_query": is_write_query,
    }

    if notes:
        case["notes"] = notes

    if needs_review or validation_failure:
        case["status"] = "needs_review"
    if validation_failure:
        case["validation_failure"] = validation_failure

    # min_results
    actual_rows = execution.get("actual_rows")
    if actual_rows is not None and actual_rows > 0:
        case["min_results"] = actual_rows
    else:
        case["min_results"] = 0

    # execution timing
    exec_ms = execution.get("execution_ms")
    if exec_ms is not None:
        case["execution_ms"] = exec_ms

    if execution.get("error"):
        case["execution_error"] = execution["error"]

    # ---- Gate 4 performance thresholds ----
    # Prefer observed metrics (multiplied by tolerance factor) when available;
    # fall back to difficulty-based conservative defaults.
    _defs = difficulty_defaults if difficulty_defaults is not None else _BASE_DIFFICULTY_DEFAULTS
    defaults = _defs.get(difficulty, _defs["expert"])

    observed_db_hits = execution.get("db_hits")
    if observed_db_hits is not None and observed_db_hits > 0:
        case["max_db_hits"] = observed_db_hits * 3
    else:
        case["max_db_hits"] = defaults["max_db_hits"]

    if exec_ms is not None and exec_ms > 0 and not execution.get("error"):
        case["max_runtime_ms"] = int(exec_ms * 5)
    else:
        case["max_runtime_ms"] = defaults["max_runtime_ms"]

    case["max_allocated_memory_bytes"] = _DEFAULT_MAX_MEMORY_BYTES

    if cypher:
        case["candidate_cypher"] = cypher

    return case


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run(
    domain: str,
    cases_dir: Path,
    count: int,
    difficulties: list[str],
    model_id: str,
    skill: str,
    neo4j_uri: Optional[str],
    neo4j_username: Optional[str],
    neo4j_password: Optional[str],
    *,
    verbose: bool = False,
    no_cypher: bool = False,
) -> None:
    """Main generation pipeline."""
    _require_yaml()

    # Load domain YAML
    domain_path = cases_dir / f"{domain}.yml"
    if not domain_path.exists():
        print(f"ERROR: Domain YAML not found: {domain_path}", file=sys.stderr)
        print(f"  Run 'make register-dataset DB_NAME={domain}' first.", file=sys.stderr)
        sys.exit(1)

    data = _load_domain_yaml(domain_path)
    dataset = data.get("dataset")
    if not dataset or not isinstance(dataset, dict):
        print(
            f"ERROR: No 'dataset:' block found in {domain_path}",
            file=sys.stderr,
        )
        print("  Run 'make register-dataset' to add the dataset: block first.", file=sys.stderr)
        sys.exit(1)

    db_block = data.get("database") or {}
    existing_cases: list[dict[str, Any]] = data.get("cases") or []

    # Resolve Neo4j connection from args > env > YAML database: block
    uri = neo4j_uri or os.environ.get("NEO4J_URI") or db_block.get("uri", "bolt://localhost:7687")
    username = neo4j_username or os.environ.get("NEO4J_USERNAME") or db_block.get("username", "neo4j")
    password = neo4j_password or os.environ.get("NEO4J_PASSWORD") or db_block.get("password", "neo4j")
    database = db_block.get("database", domain)

    print(f"[generate-questions] Domain: {domain}")
    print(f"  URI: {uri}  DB: {database}")
    print(f"  Model: {model_id}")
    print(f"  Count: {count}  Difficulties: {difficulties}")
    print(f"  Existing cases: {len(existing_cases)}")
    if no_cypher:
        print(f"  --no-cypher: skipping Cypher generation and DB execution")

    # Connect to Neo4j (skip when --no-cypher)
    driver = None
    _difficulty_defaults: dict[str, dict[str, int]] = _BASE_DIFFICULTY_DEFAULTS.copy()
    if not no_cypher:
        driver = _get_driver(uri, username, password)
        try:
            driver.verify_connectivity()
        except Exception as exc:
            print(f"ERROR: Cannot connect to Neo4j at {uri}: {exc}", file=sys.stderr)
            sys.exit(1)
        node_count, rel_count = _query_graph_size(driver, database)
        if node_count + rel_count > 0:
            _difficulty_defaults = compute_difficulty_defaults(node_count, rel_count)
            print(
                f"[graph-size] {node_count:,} nodes + {rel_count:,} rels → "
                f"db_hits caps: "
                + ", ".join(
                    f"{d}={_difficulty_defaults[d]['max_db_hits']:,}"
                    for d in ("basic", "intermediate", "advanced", "complex", "expert")
                ),
                flush=True,
            )

    # Import question validator
    try:
        from question_validator import QuestionValidator  # type: ignore
    except ImportError:
        print("ERROR: question_validator.py not found in harness dir", file=sys.stderr)
        sys.exit(1)

    schema = dataset.get("schema", {})
    validator = QuestionValidator(schema=schema)

    # Format schema for Claude
    schema_text = _format_dataset_schema_for_prompt(dataset, db_block)

    # Get existing questions for de-duplication
    existing_questions = _extract_existing_questions(existing_cases)

    # Build generation prompt
    prompt = _build_generation_prompt(
        schema_text=schema_text,
        database=database,
        difficulties=difficulties,
        count=count,
        existing_questions=existing_questions,
    )

    # --- Step 1: Generate questions ---
    print(f"\n[generate-questions] Calling Claude to generate {count} questions...", flush=True)
    questions, err = _call_claude_for_questions(prompt, model_id=model_id)
    if err:
        print(f"ERROR: Question generation failed: {err}", file=sys.stderr)
        sys.exit(1)
    print(f"  Got {len(questions)} questions from Claude")

    # Trim or pad to requested count
    if len(questions) > count:
        questions = questions[:count]

    # --- Step 2: Validate, rewrite, generate Cypher, execute ---
    stats = {"total": len(questions), "auto_rewritten": 0, "flagged_needs_review": 0}
    new_cases: list[dict[str, Any]] = []

    # --- Step 2a: Assign batch IDs and pre-generate Cypher in bulk (unless --no-cypher) ---
    # Each question gets a temporary _batch_id so we can match JSONL results back to it.
    plugin_dir = _resolve_test_plugin_dir(skill)
    batch_cypher_by_id: dict[str, dict[str, Any]] = {}
    if not no_cypher:
        for i, qdict in enumerate(questions):
            difficulty_tmp = str(qdict.get("difficulty", difficulties[i % len(difficulties)])).strip()
            if difficulty_tmp not in _VALID_DIFFICULTIES:
                difficulty_tmp = difficulties[i % len(difficulties)]
            batch_id = f"{domain}-{difficulty_tmp}-batch{i+1:03d}"
            qdict["_batch_id"] = batch_id

        batch_results = _generate_batch_cypher(
            questions=questions,
            schema_text=schema_text,
            domain=domain,
            db_config=db_block,
            plugin_dir=plugin_dir,
            model_id=model_id,
            skill=skill,
        )
        for item in batch_results:
            batch_cypher_by_id[item["id"]] = item

    for i, qdict in enumerate(questions):
        question = str(qdict.get("question", "")).strip()
        difficulty = str(qdict.get("difficulty", difficulties[i % len(difficulties)])).strip()
        notes = str(qdict.get("notes", "")).strip()
        tags = list(qdict.get("tags", []) or [])

        if not question:
            print(f"  [{i+1}/{len(questions)}] Skipping empty question", file=sys.stderr)
            continue

        if difficulty not in _VALID_DIFFICULTIES:
            difficulty = difficulties[i % len(difficulties)]

        # Validate question language
        ok, reason = validator.validate(question)
        validation_failure: Optional[str] = None
        needs_review = False

        if not ok:
            print(f"  [{i+1}] INVALID question: {reason}")
            print(f"       Q: {question[:80]}")
            # Auto-rewrite once
            rewritten = _rewrite_question(question, model_id=model_id)
            if rewritten:
                ok2, reason2 = validator.validate(rewritten)
                if ok2:
                    print(f"       → Rewritten: {rewritten[:80]}")
                    question = rewritten
                    stats["auto_rewritten"] += 1
                else:
                    print(f"       → Rewrite still invalid ({reason2}): {rewritten[:80]}")
                    validation_failure = f"Original: {reason}; Rewrite: {reason2}"
                    needs_review = True
                    stats["flagged_needs_review"] += 1
            else:
                validation_failure = reason
                needs_review = True
                stats["flagged_needs_review"] += 1

        # Generate candidate Cypher (skip when --no-cypher)
        cypher: Optional[str] = None
        is_write = False
        execution: dict[str, Any] = {"actual_rows": None, "execution_ms": None, "error": None}

        if no_cypher:
            print(f"  [{i+1}/{len(questions)}] {difficulty}: {question[:70]} [no-cypher]", flush=True)
            needs_review = True
        else:
            if verbose:
                print(f"  [{i+1}/{len(questions)}] {difficulty}: {question[:70]}")
            else:
                print(f"  [{i+1}/{len(questions)}] Validating Cypher for: {question[:60]}...", flush=True)

            # Try to use batch result first; fall back to per-question generation
            batch_id = qdict.get("_batch_id", "")
            batch_item = batch_cypher_by_id.get(batch_id)
            if batch_item:
                cypher = batch_item.get("cypher", "").strip() or None
                is_write = bool(batch_item.get("is_write_query", False))
                cypher_err: Optional[str] = None
                if cypher:
                    print(f"    [batch] got Cypher from batch result", flush=True)
                else:
                    print(f"    [batch] empty cypher in batch result — falling back to per-question", flush=True)
                    batch_item = None

            if not batch_item:
                # Fallback: individual _generate_cypher() call
                print(f"    [fallback] calling _generate_cypher() for: {question[:60]}...", flush=True)
                cypher, is_write, cypher_err = _generate_cypher(
                    question=question,
                    schema_text=schema_text,
                    database=database,
                    difficulty=difficulty,
                    model_id=model_id,
                    skill=skill,
                )
                if cypher_err:
                    print(f"    WARNING: Cypher generation failed: {cypher_err}", file=sys.stderr)

            # Execute against DB to capture baseline
            if cypher:
                execution = _execute_query(driver, database, cypher, is_write)
                actual_rows = execution.get("actual_rows")
                if execution.get("error"):
                    print(f"    WARNING: Execution error: {execution['error'][:100]}", file=sys.stderr)
                    needs_review = True
                elif actual_rows == 0 and not is_write:
                    print(f"    WARNING: Query returned 0 rows — marking needs_review", file=sys.stderr)
                    needs_review = True
                elif actual_rows is not None:
                    print(f"    OK: {actual_rows} rows in {execution.get('execution_ms', '?')}ms")

        # Compute next case ID
        case_id = _next_case_id(existing_cases + new_cases, domain, difficulty)

        case = _build_case(
            case_id=case_id,
            question=question,
            difficulty=difficulty,
            notes=notes,
            tags=tags,
            database=database,
            domain=domain,
            cypher=cypher,
            is_write_query=is_write,
            execution=execution,
            needs_review=needs_review,
            validation_failure=validation_failure,
            difficulty_defaults=_difficulty_defaults,
        )
        new_cases.append(case)

    # --- Step 3: Append to domain YAML ---
    data["cases"] = existing_cases + new_cases
    _save_domain_yaml(domain_path, data)

    print(f"\n[generate-questions] Done!")
    print(f"  Total generated:  {stats['total']}")
    print(f"  Auto-rewritten:   {stats['auto_rewritten']}")
    print(f"  Needs review:     {stats['flagged_needs_review']}")
    print(f"  Appended {len(new_cases)} new cases to {domain_path}")

    if driver is not None:
        driver.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate test questions for a neo4j-skills domain YAML."
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Domain name (must match a YAML file in --cases-dir, e.g. 'companies')",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=25,
        help="Number of questions to generate (default: 25)",
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        help="Model short name: sonnet (default), haiku, opus — or full model ID",
    )
    parser.add_argument(
        "--difficulties",
        default="basic,intermediate,advanced,complex,expert",
        help="Comma-separated list of difficulty tiers to target (default: all five)",
    )
    parser.add_argument(
        "--cases-dir",
        default=str(_HERE.parent / "tests" / "cases"),
        help="Path to tests/cases/ directory",
    )
    parser.add_argument(
        "--skill",
        default="neo4j-cypher-authoring-skill",
        help="Skill name to load for Cypher generation (default: neo4j-cypher-authoring-skill)",
    )
    parser.add_argument(
        "--neo4j-uri",
        default=None,
        help="Neo4j URI (overrides database: block in YAML and NEO4J_URI env var)",
    )
    parser.add_argument(
        "--neo4j-username",
        default=None,
        help="Neo4j username (overrides YAML and NEO4J_USERNAME env var)",
    )
    parser.add_argument(
        "--neo4j-password",
        default=None,
        help="Neo4j password (overrides YAML and NEO4J_PASSWORD env var)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--no-cypher",
        action="store_true",
        help=(
            "Skip Cypher generation and DB execution. "
            "Cases are written with status: needs_review. "
            "Useful for fast bulk question generation before harness validation."
        ),
    )

    args = parser.parse_args()

    model_id = resolve_model_id(args.model)
    difficulties = [d.strip() for d in args.difficulties.split(",") if d.strip()]
    invalid_diffs = [d for d in difficulties if d not in _VALID_DIFFICULTIES]
    if invalid_diffs:
        print(
            f"ERROR: Invalid difficulty values: {invalid_diffs}. "
            f"Valid: {_VALID_DIFFICULTIES}",
            file=sys.stderr,
        )
        sys.exit(1)

    cases_dir = Path(args.cases_dir)
    if not cases_dir.exists():
        print(f"ERROR: cases-dir does not exist: {cases_dir}", file=sys.stderr)
        sys.exit(1)

    run(
        domain=args.domain,
        cases_dir=cases_dir,
        count=args.count,
        difficulties=difficulties,
        model_id=model_id,
        skill=args.skill,
        neo4j_uri=args.neo4j_uri,
        neo4j_username=args.neo4j_username,
        neo4j_password=args.neo4j_password,
        verbose=args.verbose,
        no_cypher=args.no_cypher,
    )


if __name__ == "__main__":
    main()
