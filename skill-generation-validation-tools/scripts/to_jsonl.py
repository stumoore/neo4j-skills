#!/usr/bin/env python3
"""
to_jsonl.py — Convert YAML training dataset(s) to JSONL for fine-tuning.

Reads one or more YAML training dataset files produced by exporter.py and writes
one JSONL line per record. Each line is a JSON object with a `messages` array
containing three entries:

  system    — concise Cypher 25 authoring instruction summary
  user      — database name + schema context summary + original question
  assistant — the validated Cypher query (only)

Output is compatible with Anthropic and OpenAI fine-tuning APIs.

Usage:
    # Single file
    uv run python3 scripts/to_jsonl.py \\
        --input tests/dataset/companies.yml \\
        --output tests/dataset/companies.jsonl

    # All files in a directory
    uv run python3 scripts/to_jsonl.py \\
        --input tests/dataset/ \\
        --output all.jsonl

    # Filter by difficulty
    uv run python3 scripts/to_jsonl.py \\
        --input tests/dataset/companies.yml \\
        --output basic.jsonl \\
        --difficulty basic

    # Filter by tags (comma-separated)
    uv run python3 scripts/to_jsonl.py \\
        --input tests/dataset/companies.yml \\
        --output search.jsonl \\
        --tags search,vector
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# YAML import
# ---------------------------------------------------------------------------

try:
    import yaml  # type: ignore

    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


def _require_yaml() -> None:
    if not _YAML_AVAILABLE:
        print(
            "ERROR: pyyaml is required. Install with: uv add pyyaml",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# System message — fixed Cypher 25 authoring instruction summary
# ---------------------------------------------------------------------------

_SYSTEM_MESSAGE = """\
You are a Neo4j Cypher 25 query author. Follow these rules for every query:

1. Always begin with `CYPHER 25`.
2. Use `$param` for all predicates and MERGE keys; never inline literals (exception: LIMIT N).
3. Every MERGE must have ON CREATE SET and ON MATCH SET.
4. Use CALL { } scope syntax (Cypher 25); importing WITH inside CALL is deprecated.
5. Prefer SHORTEST k over deprecated shortestPath() / allShortestPaths().
6. Never emit GQL-only clauses: LET, FINISH, FILTER, NEXT, INSERT.
7. Use elementId() not id() (id() is deprecated).
8. Use toFloatOrNull() / toIntegerOrNull() variants to avoid runtime errors on bad data.
9. For vector search use the SEARCH clause (Neo4j 2026.01+, Preview) or db.index.vector.queryNodes().
10. For fulltext search use db.index.fulltext.queryNodes() (SEARCH clause is vector-only in 2026.01).
11. Naming: labels PascalCase, relationship types SCREAMING_SNAKE_CASE, properties camelCase.
12. EXPLAIN every query before execution; PROFILE when performance matters.

Output only the Cypher query. No explanation, no markdown, no prose.\
"""

# ---------------------------------------------------------------------------
# Schema context formatter
# ---------------------------------------------------------------------------


def _format_schema_context(
    schema_context: Optional[dict[str, Any]],
    property_samples: Optional[dict[str, Any]],
    database: str,
) -> str:
    """
    Build a compact schema context string for the user message.

    Includes labels, relationship types, index names/types, and property
    semantics (inferred_semantic values only — no raw sample data).
    """
    lines: list[str] = [f"Database: {database}"]

    if schema_context:
        labels = schema_context.get("labels") or []
        rel_types = schema_context.get("relationship_types") or []
        indexes = schema_context.get("indexes") or []

        if labels:
            lines.append(f"Node labels: {', '.join(sorted(labels))}")
        if rel_types:
            lines.append(f"Relationship types: {', '.join(sorted(rel_types))}")
        if indexes:
            idx_summaries = []
            for idx in indexes:
                name = idx.get("name", "?")
                idx_type = idx.get("type", "?")
                state = idx.get("state", "")
                props_list = idx.get("properties") or []
                props_str = ", ".join(str(p) for p in props_list)
                summary = f"{name} ({idx_type}"
                if props_str:
                    summary += f" on {props_str}"
                if state and state != "ONLINE":
                    summary += f", state={state}"
                summary += ")"
                idx_summaries.append(summary)
            lines.append(f"Indexes: {'; '.join(idx_summaries)}")

    if property_samples:
        prop_lines: list[str] = []
        for label, props in sorted(property_samples.items()):
            if not isinstance(props, dict):
                continue
            for prop, info in sorted(props.items()):
                if not isinstance(info, dict):
                    continue
                semantic = info.get("inferred_semantic", "")
                non_null = info.get("non_null_count")
                entry = f"{label}.{prop}"
                if semantic:
                    entry += f" [{semantic}]"
                if non_null is not None:
                    entry += f" ({non_null} non-null)"
                prop_lines.append(entry)
        if prop_lines:
            lines.append("Properties: " + ", ".join(prop_lines))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Record → messages conversion
# ---------------------------------------------------------------------------


def _record_to_messages(record: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a single training record to a fine-tuning messages object.

    Returns:
        {"messages": [system, user, assistant]}
    """
    database = record.get("database", "unknown")
    question = record.get("question", "")
    cypher = record.get("cypher", "")
    schema_context = record.get("schema_context")
    property_samples = record.get("property_samples")

    schema_str = _format_schema_context(schema_context, property_samples, database)

    user_content = f"{schema_str}\n\nQuestion: {question}"

    return {
        "messages": [
            {"role": "system", "content": _SYSTEM_MESSAGE},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": cypher},
        ]
    }


# ---------------------------------------------------------------------------
# Dataset file loader
# ---------------------------------------------------------------------------


def _load_dataset_file(path: Path) -> list[dict[str, Any]]:
    """
    Load records from a YAML dataset file.

    Expects a top-level `records:` key (format produced by exporter.py).
    Returns an empty list if the file is missing, empty, or malformed.
    """
    _require_yaml()
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        print(f"WARNING: could not read {path}: {exc} — skipping", file=sys.stderr)
        return []

    if not isinstance(data, dict):
        print(
            f"WARNING: {path} has unexpected format (expected mapping) — skipping",
            file=sys.stderr,
        )
        return []

    records = data.get("records", [])
    if not isinstance(records, list):
        print(
            f"WARNING: {path} 'records' key is not a list — skipping",
            file=sys.stderr,
        )
        return []

    return records


def _collect_input_files(input_path: Path) -> list[Path]:
    """
    Collect all YAML dataset files from a file path or directory.

    If input_path is a directory, collects all *.yml files (not *-generated.yml
    files, which are pending human review).
    """
    if input_path.is_file():
        return [input_path]

    if input_path.is_dir():
        # Skip *-generated.yml — those require human review before export
        files = sorted(
            p
            for p in input_path.glob("*.yml")
            if not p.name.endswith("-generated.yml")
        )
        return files

    print(f"ERROR: input path not found: {input_path}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def _matches_filters(
    record: dict[str, Any],
    difficulty_filter: Optional[str],
    tags_filter: Optional[set[str]],
) -> bool:
    """Return True if the record passes all active filters."""
    if difficulty_filter is not None:
        meta = record.get("metadata") or {}
        if meta.get("difficulty", "") != difficulty_filter:
            return False

    if tags_filter:
        meta = record.get("metadata") or {}
        record_tags = set(meta.get("tags") or [])
        # Must have at least one matching tag
        if not (tags_filter & record_tags):
            return False

    return True


# ---------------------------------------------------------------------------
# Main convert function
# ---------------------------------------------------------------------------


def convert(
    input_path: Path,
    output_path: Path,
    *,
    difficulty: Optional[str] = None,
    tags: Optional[set[str]] = None,
    verbose: bool = False,
) -> int:
    """
    Convert YAML dataset file(s) to JSONL.

    Args:
        input_path: Path to a YAML file or directory containing YAML files.
        output_path: Path to write the JSONL output.
        difficulty: Optional difficulty filter ('basic', 'intermediate', 'advanced', 'complex').
        tags: Optional set of tag strings (record must match at least one).
        verbose: Print per-record details.

    Returns:
        Number of records written.
    """
    input_files = _collect_input_files(input_path)

    if not input_files:
        print(
            f"WARNING: no YAML dataset files found in {input_path}",
            file=sys.stderr,
        )
        return 0

    if verbose:
        print(f"[to_jsonl] Input files: {[str(f) for f in input_files]}", flush=True)

    # Collect and filter records
    all_records: list[dict[str, Any]] = []
    for file_path in input_files:
        records = _load_dataset_file(file_path)
        if verbose:
            print(f"[to_jsonl]   {file_path.name}: {len(records)} record(s)", flush=True)
        all_records.extend(records)

    filtered: list[dict[str, Any]] = [
        r for r in all_records if _matches_filters(r, difficulty, tags)
    ]

    filter_desc = []
    if difficulty:
        filter_desc.append(f"difficulty={difficulty}")
    if tags:
        filter_desc.append(f"tags={sorted(tags)}")
    filter_str = f" (filters: {', '.join(filter_desc)})" if filter_desc else ""

    print(
        f"[to_jsonl] {len(filtered)}/{len(all_records)} record(s) after filtering{filter_str}",
        flush=True,
    )

    if not filtered:
        print("[to_jsonl] No records to write.", flush=True)
        return 0

    # Write JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(output_path, "w", encoding="utf-8") as out_f:
        for record in filtered:
            try:
                obj = _record_to_messages(record)
                line = json.dumps(obj, ensure_ascii=False)
                out_f.write(line + "\n")
                written += 1
                if verbose:
                    record_id = record.get("id", "?")
                    diff = (record.get("metadata") or {}).get("difficulty", "?")
                    print(f"  WRITE {record_id} ({diff})", flush=True)
            except Exception as exc:
                record_id = record.get("id", "?")
                print(
                    f"WARNING: could not serialize record {record_id}: {exc} — skipping",
                    file=sys.stderr,
                )

    print(f"[to_jsonl] Wrote {written} line(s) to {output_path}", flush=True)
    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert YAML training dataset(s) to JSONL for fine-tuning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a YAML dataset file or directory containing YAML files",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the JSONL output file",
    )
    parser.add_argument(
        "--difficulty",
        default=None,
        choices=["basic", "intermediate", "advanced", "complex"],
        help="Filter records by difficulty (default: no filter — all difficulties)",
    )
    parser.add_argument(
        "--tags",
        default=None,
        help=(
            "Comma-separated list of tags to filter by. "
            "A record is included if it has ANY of the specified tags."
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print per-record details",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    _require_yaml()

    input_path = Path(args.input)
    output_path = Path(args.output)
    tags: Optional[set[str]] = (
        {t.strip() for t in args.tags.split(",") if t.strip()} if args.tags else None
    )

    convert(
        input_path=input_path,
        output_path=output_path,
        difficulty=args.difficulty,
        tags=tags,
        verbose=args.verbose,
    )
    return 0


# ---------------------------------------------------------------------------
# Smoke tests (run when invoked directly with no args)
# ---------------------------------------------------------------------------


def _run_smoke_tests() -> None:
    """
    Offline smoke tests — no Neo4j connection required.
    Tests: schema formatting, message structure, filtering, JSONL round-trip.
    """
    import tempfile

    _require_yaml()
    import yaml as _yaml  # type: ignore

    print("Running to_jsonl smoke tests...", flush=True)
    errors: list[str] = []

    # --- Test 1: _format_schema_context with full schema ---
    schema_context = {
        "labels": ["Organization", "Article"],
        "relationship_types": ["MENTIONS", "HAS_CHUNK"],
        "indexes": [
            {
                "name": "entity",
                "type": "FULLTEXT",
                "state": "ONLINE",
                "labelsOrTypes": ["Organization"],
                "properties": ["name"],
            },
            {
                "name": "news",
                "type": "VECTOR",
                "state": "ONLINE",
                "labelsOrTypes": ["Chunk"],
                "properties": ["embedding"],
            },
        ],
    }
    property_samples = {
        "Organization": {
            "name": {"inferred_semantic": "freetext", "non_null_count": 1500},
            "ticker": {"inferred_semantic": "uuid", "non_null_count": 800},
        },
        "Article": {
            "sentiment": {"inferred_semantic": "score", "non_null_count": 2000},
        },
    }
    schema_str = _format_schema_context(schema_context, property_samples, "companies")
    assert "Database: companies" in schema_str, "Missing database name"
    assert "Organization" in schema_str, "Missing label"
    assert "MENTIONS" in schema_str, "Missing relationship type"
    assert "entity (FULLTEXT" in schema_str, "Missing index"
    assert "Organization.name [freetext]" in schema_str, "Missing property semantic"
    assert "Article.sentiment [score]" in schema_str, "Missing sentiment property"
    print("  PASS: schema context formatting", flush=True)

    # --- Test 2: _record_to_messages structure ---
    sample_record = {
        "id": "tc-001",
        "question": "Find the top 5 organizations by article count",
        "database": "companies",
        "neo4j_version": "2026.01",
        "schema_context": schema_context,
        "property_samples": property_samples,
        "cypher": "CYPHER 25\nMATCH (o:Organization)<-[:MENTIONS]-(a:Article)\nRETURN o.name, count(a) AS articles\nORDER BY articles DESC\nLIMIT 5",
        "metadata": {
            "difficulty": "basic",
            "tags": ["match", "aggregation"],
            "db_hits": 1200,
            "allocated_memory_bytes": 204800,
            "runtime_ms": 12.0,
            "passed_gates": [1, 2, 3, 4],
            "generated_at": "2026-03-20T12:00:00Z",
        },
    }

    obj = _record_to_messages(sample_record)
    assert "messages" in obj, "Missing messages key"
    msgs = obj["messages"]
    assert len(msgs) == 3, f"Expected 3 messages, got {len(msgs)}"
    roles = [m["role"] for m in msgs]
    assert roles == ["system", "user", "assistant"], f"Wrong roles: {roles}"

    # system: concise authoring instructions
    system_msg = msgs[0]["content"]
    assert "CYPHER 25" in system_msg, "System message missing CYPHER 25 instruction"
    assert "$param" in system_msg, "System message missing parameter discipline"
    assert len(system_msg) < 3000, "System message too long for a concise summary"

    # user: contains database name and question
    user_msg = msgs[1]["content"]
    assert "companies" in user_msg, "User message missing database name"
    assert "Find the top 5 organizations" in user_msg, "User message missing question"
    assert "Organization" in user_msg, "User message missing schema labels"

    # assistant: only the Cypher query
    assistant_msg = msgs[2]["content"]
    assert assistant_msg.startswith("CYPHER 25"), "Assistant message should start with CYPHER 25"
    assert "MATCH" in assistant_msg, "Assistant message missing MATCH"

    print("  PASS: messages structure", flush=True)

    # --- Test 3: filtering by difficulty ---
    records_basic = [
        {**sample_record, "id": "tc-basic-1", "metadata": {**sample_record["metadata"], "difficulty": "basic"}},
        {**sample_record, "id": "tc-basic-2", "metadata": {**sample_record["metadata"], "difficulty": "basic"}},
    ]
    records_advanced = [
        {**sample_record, "id": "tc-adv-1", "metadata": {**sample_record["metadata"], "difficulty": "advanced"}},
    ]
    all_recs = records_basic + records_advanced

    basic_filtered = [r for r in all_recs if _matches_filters(r, "basic", None)]
    assert len(basic_filtered) == 2, f"Expected 2 basic records, got {len(basic_filtered)}"

    adv_filtered = [r for r in all_recs if _matches_filters(r, "advanced", None)]
    assert len(adv_filtered) == 1, f"Expected 1 advanced record, got {len(adv_filtered)}"

    no_filter = [r for r in all_recs if _matches_filters(r, None, None)]
    assert len(no_filter) == 3, f"Expected 3 records without filter, got {len(no_filter)}"

    print("  PASS: difficulty filtering", flush=True)

    # --- Test 4: filtering by tags ---
    rec_with_search_tag = {
        **sample_record,
        "id": "tc-search-1",
        "metadata": {**sample_record["metadata"], "tags": ["search", "vector"]},
    }
    rec_no_search = {
        **sample_record,
        "id": "tc-match-1",
        "metadata": {**sample_record["metadata"], "tags": ["match", "aggregation"]},
    }
    mixed = [rec_with_search_tag, rec_no_search]

    search_filtered = [r for r in mixed if _matches_filters(r, None, {"search"})]
    assert len(search_filtered) == 1, f"Expected 1 search-tagged record, got {len(search_filtered)}"
    assert search_filtered[0]["id"] == "tc-search-1", "Wrong record selected by tag"

    vector_filtered = [r for r in mixed if _matches_filters(r, None, {"vector", "aggregation"})]
    assert len(vector_filtered) == 2, f"Expected 2 records (either tag), got {len(vector_filtered)}"

    print("  PASS: tag filtering", flush=True)

    # --- Test 5: JSONL round-trip via convert() ---
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Write a small YAML dataset
        dataset = {"records": [sample_record]}
        yaml_path = tmppath / "companies.yml"
        with open(yaml_path, "w") as f:
            _yaml.dump(dataset, f, default_flow_style=False, allow_unicode=True)

        jsonl_path = tmppath / "out.jsonl"
        count = convert(
            input_path=yaml_path,
            output_path=jsonl_path,
            difficulty=None,
            tags=None,
        )
        assert count == 1, f"Expected 1 record written, got {count}"
        assert jsonl_path.exists(), "JSONL file not created"

        # Parse and validate each line
        with open(jsonl_path) as f:
            lines = f.readlines()
        assert len(lines) == 1, f"Expected 1 JSONL line, got {len(lines)}"
        parsed = json.loads(lines[0])
        assert "messages" in parsed, "JSONL line missing messages key"
        assert len(parsed["messages"]) == 3, "JSONL messages count != 3"
        assert parsed["messages"][0]["role"] == "system", "First message should be system"
        assert parsed["messages"][1]["role"] == "user", "Second message should be user"
        assert parsed["messages"][2]["role"] == "assistant", "Third message should be assistant"

    print("  PASS: JSONL round-trip", flush=True)

    # --- Test 6: difficulty filter produces only basic records ---
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        mixed_dataset = {
            "records": [
                {**sample_record, "id": "tc-b1",
                 "metadata": {**sample_record["metadata"], "difficulty": "basic"}},
                {**sample_record, "id": "tc-i1",
                 "metadata": {**sample_record["metadata"], "difficulty": "intermediate"}},
                {**sample_record, "id": "tc-b2",
                 "metadata": {**sample_record["metadata"], "difficulty": "basic"}},
            ]
        }
        yaml_path = tmppath / "companies.yml"
        with open(yaml_path, "w") as f:
            _yaml.dump(mixed_dataset, f, default_flow_style=False, allow_unicode=True)

        jsonl_path = tmppath / "basic_only.jsonl"
        count = convert(
            input_path=yaml_path,
            output_path=jsonl_path,
            difficulty="basic",
        )
        assert count == 2, f"Expected 2 basic records, got {count}"
        with open(jsonl_path) as f:
            lines = f.readlines()
        for line in lines:
            parsed = json.loads(line)
            # Verify the user message doesn't contain intermediate content (just structure check)
            assert len(parsed["messages"]) == 3

    print("  PASS: difficulty filter produces only basic records", flush=True)

    # --- Summary ---
    if errors:
        print("\nFAIL — errors:", flush=True)
        for e in errors:
            print(f"  {e}", flush=True)
        sys.exit(1)
    else:
        print("\nAll smoke tests passed.", flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _run_smoke_tests()
    else:
        sys.exit(main())
