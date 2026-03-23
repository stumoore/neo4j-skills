#!/usr/bin/env python3
"""
register_dataset.py — Dataset registration CLI for neo4j-skills.

Connects to a Neo4j database, discovers schema, capabilities, indexes and
constraints, calls Claude to generate a business-language description, and
writes a dataset: YAML block to tests/cases/<domain>.yml.

If the domain YAML file already exists, the dataset: block is updated and
existing cases are preserved. If the file is new, only the dataset: block
is written (no cases yet).

Usage:
    uv run --project skill-generation-validation-tools python3 \\
        skill-generation-validation-tools/scripts/register_dataset.py \\
        --uri neo4j+s://demo.neo4jlabs.com:7687 \\
        --username companies \\
        --password companies \\
        --database companies \\
        --domain companies \\
        --model sonnet \\
        --output-dir skill-generation-validation-tools/tests/cases/

Environment variables:
    NEO4J_URI       — default: bolt://localhost:7687
    NEO4J_USERNAME  — default: neo4j
    NEO4J_PASSWORD  — default: neo4j

Makefile target:
    make register-dataset DB_URI=... DB_USER=... DB_PASS=... DB_NAME=companies
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_HERE.parent / "tests" / "harness"))

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
# Neo4j connection
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
# Discovery steps
# ---------------------------------------------------------------------------


def _run_query(driver: Any, database: str, cypher: str, **params: Any) -> list[Any]:
    """Run a query and return records; returns [] on error."""
    try:
        records, _, _ = driver.execute_query(cypher, **params, database_=database)
        return list(records)
    except Exception as exc:
        print(f"  WARNING: query failed: {exc!r}", file=sys.stderr)
        return []


def discover_version(driver: Any, database: str) -> dict[str, str]:
    """
    Detect Neo4j version via dbms.components().

    Returns {"neo4j_version": "YYYY.MM.PATCH", "cypher_version": "25"}
    Falls back to "unknown" on failure.
    """
    records = _run_query(
        driver,
        "system",
        "CALL dbms.components() YIELD name, versions RETURN name, versions",
    )
    neo4j_ver = "unknown"
    for r in records:
        if str(r["name"]).lower() == "neo4j kernel":
            versions = r["versions"]
            neo4j_ver = versions[0] if versions else "unknown"
            break

    # Also try with database parameter as fallback
    if neo4j_ver == "unknown":
        records = _run_query(
            driver,
            database,
            "CALL dbms.components() YIELD name, versions RETURN name, versions",
        )
        for r in records:
            if str(r["name"]).lower() == "neo4j kernel":
                versions = r["versions"]
                neo4j_ver = versions[0] if versions else "unknown"
                break

    return {"neo4j_version": neo4j_ver, "cypher_version": "25"}


def discover_capabilities(driver: Any, database: str) -> list[str]:
    """
    Detect optional plugins by counting procedures with known prefixes.

    Returns a list like ['gds', 'apoc', 'apoc-extended', 'genai'].
    """
    _CHECKS = [
        ("gds", "gds."),
        ("apoc", "apoc."),
        ("genai", "ai."),
    ]
    capabilities: list[str] = []
    for key, prefix in _CHECKS:
        records = _run_query(
            driver,
            database,
            "SHOW PROCEDURES YIELD name WHERE name STARTS WITH $prefix RETURN count(*) AS cnt",
            prefix=prefix,
        )
        cnt = int(records[0]["cnt"]) if records else 0
        if cnt > 0:
            capabilities.append(key)
            # apoc-extended typically adds > 400 procedures on top of core
            if key == "apoc" and cnt > 400:
                capabilities.append("apoc-extended")
    return capabilities


def discover_schema(driver: Any, database: str) -> dict[str, Any]:
    """
    Full schema discovery: labels, rel-types, properties, indexes, constraints.

    Returns a structured dict ready for YAML serialization.
    """
    schema: dict[str, Any] = {
        "labels": [],
        "relationship_types": [],
        "node_properties": {},
        "rel_properties": {},
        "indexes": [],
        "constraints": [],
    }

    # Labels
    records = _run_query(
        driver,
        database,
        "CALL db.labels() YIELD label RETURN label ORDER BY label",
    )
    schema["labels"] = [r["label"] for r in records]

    # Relationship types
    records = _run_query(
        driver,
        database,
        "CALL db.relationshipTypes() YIELD relationshipType "
        "RETURN relationshipType ORDER BY relationshipType",
    )
    schema["relationship_types"] = [r["relationshipType"] for r in records]

    # Indexes (ONLINE only)
    records = _run_query(
        driver,
        database,
        "SHOW INDEXES YIELD name, type, state, labelsOrTypes, properties "
        "WHERE state = 'ONLINE' "
        "RETURN name, type, state, labelsOrTypes, properties ORDER BY name",
    )
    schema["indexes"] = [
        {
            "name": r["name"],
            "type": r["type"],
            "labelsOrTypes": list(r["labelsOrTypes"] or []),
            "properties": list(r["properties"] or []),
        }
        for r in records
    ]

    # Constraints
    records = _run_query(
        driver,
        database,
        "SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties "
        "RETURN name, type, labelsOrTypes, properties ORDER BY name",
    )
    schema["constraints"] = [
        {
            "name": r["name"],
            "type": r["type"],
            "labelsOrTypes": list(r["labelsOrTypes"] or []),
            "properties": list(r["properties"] or []),
        }
        for r in records
    ]

    # Node properties per label (via property key inspection)
    for label in schema["labels"]:
        records = _run_query(
            driver,
            database,
            f"MATCH (n:`{label}`) "
            "WITH keys(n) AS props UNWIND props AS prop "
            "RETURN DISTINCT prop ORDER BY prop LIMIT 50",
        )
        schema["node_properties"][label] = [r["prop"] for r in records]

    # Relationship properties per type
    for rel_type in schema["relationship_types"]:
        records = _run_query(
            driver,
            database,
            f"MATCH ()-[r:`{rel_type}`]->() "
            "WITH keys(r) AS props UNWIND props AS prop "
            "RETURN DISTINCT prop ORDER BY prop LIMIT 20",
        )
        schema["rel_properties"][rel_type] = [r["prop"] for r in records]

    return schema


def sample_property_values(
    driver: Any,
    database: str,
    label: str,
    prop: str,
    limit: int = 20,
) -> list[Any]:
    """
    Sample up to `limit` distinct values for `prop` on nodes with `label`.

    Uses COLLECT { MATCH ... RETURN DISTINCT ... LIMIT N } subquery form.
    """
    cypher = (
        f"CYPHER 25 "
        f"MATCH (n:`{label}`) WHERE n.`{prop}` IS NOT NULL "
        f"WITH COLLECT {{ MATCH (m:`{label}`) WHERE m.`{prop}` IS NOT NULL "
        f"RETURN DISTINCT m.`{prop}` LIMIT {limit} }} AS samples "
        f"RETURN samples LIMIT 1"
    )
    records = _run_query(driver, database, cypher)
    if records:
        return list(records[0]["samples"])
    return []


def discover_property_samples(
    driver: Any,
    database: str,
    schema: dict[str, Any],
    max_props_per_label: int = 10,
) -> dict[str, dict[str, Any]]:
    """
    Sample property values for each label×property pair.

    Returns {label: {prop: {type, sample/values}}} structure.
    Limits to `max_props_per_label` properties per label to avoid long runtime.
    """
    samples: dict[str, dict[str, Any]] = {}

    for label in schema["labels"]:
        props = schema["node_properties"].get(label, [])[:max_props_per_label]
        label_samples: dict[str, Any] = {}

        for prop in props:
            values = sample_property_values(driver, database, label, prop, limit=20)
            if not values:
                label_samples[prop] = {"type": "STRING"}
                continue

            # Infer type from values
            sample_type = _infer_type(prop, values)
            entry: dict[str, Any] = {"type": sample_type}

            # Store values (for enum) or sample (for others)
            str_values = [str(v) for v in values]
            if sample_type in ("STRING", "BOOLEAN") and len(set(str_values)) <= 15:
                entry["values"] = sorted(set(str_values))
            elif len(values) <= 5:
                entry["sample"] = values
            else:
                # For large value sets, store first 5 as sample
                entry["sample"] = values[:5]

            label_samples[prop] = entry

        if label_samples:
            samples[label] = label_samples

    return samples


def _infer_type(prop: str, values: list[Any]) -> str:
    """Infer a Neo4j type string from sample values."""
    if not values:
        return "STRING"
    first = values[0]
    if isinstance(first, bool):
        return "BOOLEAN"
    if isinstance(first, int):
        return "INTEGER"
    if isinstance(first, float):
        return "FLOAT"
    # Check for date-like string by name heuristic
    prop_lower = prop.lower()
    if any(kw in prop_lower for kw in ("date", "time", "at", "created", "updated")):
        return "DATE"
    return "STRING"


# ---------------------------------------------------------------------------
# Schema → YAML dataset block builder
# ---------------------------------------------------------------------------


def build_dataset_yaml(
    domain: str,
    database: str,
    uri: str,
    username: str,
    neo4j_version: str,
    cypher_version: str,
    capabilities: list[str],
    schema: dict[str, Any],
    property_samples: dict[str, dict[str, Any]],
    description: str,
    notes: list[str],
    read_only: bool = False,
) -> dict[str, Any]:
    """
    Build the top-level database: and dataset: dicts for YAML output.

    Returns a dict with 'database' and 'dataset' keys.
    """
    # Build database: block
    db_block: dict[str, Any] = {
        "uri": uri,
        "username": username,
        "database": database,
        "neo4j_version": neo4j_version,
        "cypher_version": cypher_version,
    }
    if capabilities:
        db_block["capabilities"] = capabilities
    if read_only:
        db_block["read_only"] = True

    # Build schema nodes section
    nodes_dict: dict[str, Any] = {}
    for label in schema["labels"]:
        label_info: dict[str, Any] = {"description": f"A {label} entity"}
        props_raw = schema["node_properties"].get(label, [])
        label_samples = property_samples.get(label, {})

        props_section: dict[str, Any] = {}
        for prop in props_raw:
            if prop in label_samples:
                props_section[prop] = label_samples[prop]
            else:
                props_section[prop] = {"type": "STRING"}

        if props_section:
            label_info["properties"] = props_section

        nodes_dict[label] = label_info

    # Build schema relationships section
    rels_list: list[dict[str, Any]] = []
    for rel_type in schema["relationship_types"]:
        rel_entry: dict[str, Any] = {"type": rel_type, "from": "?", "to": "?"}
        props = schema["rel_properties"].get(rel_type, [])
        if props:
            rel_entry["properties"] = props
        rels_list.append(rel_entry)

    # Build indexes section
    indexes_list: list[dict[str, Any]] = []
    for idx in schema["indexes"]:
        idx_entry: dict[str, Any] = {
            "name": idx["name"],
            "type": idx["type"],
            "on": _format_index_on(idx),
        }
        # Add example call for FULLTEXT and VECTOR
        if idx["type"] == "FULLTEXT":
            idx_entry["call"] = (
                f"CALL db.index.fulltext.queryNodes('{idx['name']}', $q) YIELD node, score"
            )
        elif idx["type"] == "VECTOR":
            idx_entry["call"] = (
                f"CALL db.index.vector.queryNodes('{idx['name']}', N, $vec) YIELD node, score"
            )
        indexes_list.append(idx_entry)

    dataset_block: dict[str, Any] = {
        "name": domain,
        "description": description,
        "schema": {
            "nodes": nodes_dict,
            "relationships": rels_list,
            "indexes": indexes_list,
        },
    }
    if notes:
        dataset_block["notes"] = notes

    return {"database": db_block, "dataset": dataset_block}


def _format_index_on(idx: dict[str, Any]) -> str:
    """Format index on-clause as 'Label(prop1, prop2)'."""
    labels = idx.get("labelsOrTypes", [])
    props = idx.get("properties", [])
    label_str = ", ".join(labels)
    props_str = ", ".join(props)
    if label_str and props_str:
        return f"{label_str}({props_str})"
    return label_str or props_str or "?"


# ---------------------------------------------------------------------------
# Claude API — description generation
# ---------------------------------------------------------------------------


def _call_claude(prompt: str, model_id: str) -> str:
    """
    Call Claude via `claude --print` subprocess.

    Returns the text response or empty string on failure.
    """
    cmd = ["claude", "--print", "--model", model_id]
    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(
                f"  WARNING: claude subprocess failed (rc={result.returncode}): "
                f"{result.stderr[:200]}",
                file=sys.stderr,
            )
            return ""
        return result.stdout.strip()
    except FileNotFoundError:
        print(
            "  WARNING: 'claude' CLI not found — skipping description generation. "
            "Install with: pip install claude-code",
            file=sys.stderr,
        )
        return ""
    except subprocess.TimeoutExpired:
        print("  WARNING: claude subprocess timed out — skipping description generation", file=sys.stderr)
        return ""


def generate_description(
    database: str,
    schema: dict[str, Any],
    property_samples: dict[str, dict[str, Any]],
    model_id: str,
) -> tuple[str, list[str]]:
    """
    Ask Claude to generate a business-language description and usage notes.

    Returns (description: str, notes: list[str]).
    Falls back to a generic description on failure.
    """
    labels = schema.get("labels", [])
    rel_types = schema.get("relationship_types", [])
    indexes = schema.get("indexes", [])

    # Compact schema summary for the prompt
    schema_summary = f"Labels: {', '.join(labels)}\n"
    schema_summary += f"Relationships: {', '.join(rel_types)}\n"
    if indexes:
        schema_summary += "Indexes: " + ", ".join(
            f"{i['name']} ({i['type']})" for i in indexes
        ) + "\n"

    # Add sample values
    sample_lines: list[str] = []
    for label in labels[:5]:  # limit to first 5 labels
        lsamples = property_samples.get(label, {})
        for prop, info in list(lsamples.items())[:3]:  # first 3 props
            vals = info.get("values") or info.get("sample") or []
            if vals:
                sample_lines.append(f"  {label}.{prop}: {vals[:3]}")
    if sample_lines:
        schema_summary += "Sample values:\n" + "\n".join(sample_lines)

    prompt = f"""You are a Neo4j database expert. Given the following schema for a Neo4j database named '{database}', provide:

1. A 2-3 sentence business-language description of what this database represents and what use cases it supports. Write for a business analyst, not a developer.
2. 3-5 practical usage notes for someone querying this database with Cypher. Include important quirks, common patterns, or pitfalls.

Schema:
{schema_summary}

Respond in this exact JSON format (no other text):
{{
  "description": "...",
  "notes": ["note1", "note2", "note3"]
}}"""

    response = _call_claude(prompt, model_id)

    if not response:
        fallback_desc = (
            f"A Neo4j graph database containing {', '.join(labels[:3])} "
            f"{'and more' if len(labels) > 3 else ''} nodes "
            f"connected by {', '.join(rel_types[:3])} relationships."
        )
        return fallback_desc, []

    # Parse JSON response
    try:
        # Extract JSON from response (Claude may add markdown fencing)
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            description = data.get("description", "")
            notes = data.get("notes", [])
            return description, notes
    except (json.JSONDecodeError, AttributeError) as exc:
        print(f"  WARNING: failed to parse Claude response as JSON: {exc}", file=sys.stderr)

    # Fallback: use response as description
    return response[:500], []


# ---------------------------------------------------------------------------
# YAML file read/write with case preservation
# ---------------------------------------------------------------------------


def load_existing_domain_yaml(path: Path) -> Optional[dict[str, Any]]:
    """Load an existing domain YAML file. Returns None if file doesn't exist."""
    if not path.exists():
        return None
    _require_yaml()
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_domain_yaml(path: Path, data: dict[str, Any]) -> None:
    """
    Write a domain YAML file, preserving the expected key order:
      # header comment
      database:
      dataset:
      cases:  (if present)
    """
    _require_yaml()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Build ordered output
    ordered: dict[str, Any] = {}

    # database: block first
    if "database" in data:
        ordered["database"] = data["database"]

    # dataset: block second
    if "dataset" in data:
        ordered["dataset"] = data["dataset"]

    # cases: block last (preserve existing cases)
    if "cases" in data:
        ordered["cases"] = data["cases"]

    with path.open("w", encoding="utf-8") as f:
        f.write(f"# {path.name} — Neo4j domain dataset for neo4j-cypher-authoring-skill\n")
        f.write(f"# Generated by register_dataset.py on {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
        f.write("# Edit manually to add business context, then run generate-questions to create test cases.\n\n")
        yaml.dump(
            ordered,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register a Neo4j database as a dataset: block in a domain YAML file."
    )
    parser.add_argument(
        "--uri",
        default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j connection URI (default: NEO4J_URI env var or bolt://localhost:7687)",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("NEO4J_USERNAME", "neo4j"),
        help="Neo4j username (default: NEO4J_USERNAME env var or neo4j)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("NEO4J_PASSWORD", "neo4j"),
        help="Neo4j password (default: NEO4J_PASSWORD env var or neo4j)",
    )
    parser.add_argument(
        "--database",
        default=None,
        help="Neo4j database name (default: same as --domain)",
    )
    parser.add_argument(
        "--domain",
        default=None,
        help="Domain name for output file (default: same as --database)",
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        help="Model for description generation: sonnet|haiku|opus (default: sonnet)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_REPO_ROOT / "skill-generation-validation-tools" / "tests" / "cases"),
        help="Output directory for domain YAML files",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        default=False,
        help="Mark database as read-only (write queries will SKIP in harness)",
    )
    parser.add_argument(
        "--no-claude",
        action="store_true",
        default=False,
        help="Skip Claude description generation (use generic fallback)",
    )

    args = parser.parse_args()

    # Resolve domain/database defaults
    if args.database is None and args.domain is None:
        parser.error("At least one of --database or --domain is required")
    database = args.database or args.domain
    domain = args.domain or args.database

    model_id = resolve_model_id(args.model)
    output_dir = Path(args.output_dir)
    output_path = output_dir / f"{domain}.yml"

    print(f"Registering dataset: {domain} (database: {database})")
    print(f"  URI: {args.uri}")
    print(f"  Output: {output_path}")

    _require_yaml()

    # Connect to Neo4j
    print("\nStep 1: Connecting to Neo4j...")
    driver = _get_driver(args.uri, args.username, args.password)

    try:
        # Step 1: Version detection
        print("Step 2: Detecting Neo4j version...")
        version_info = discover_version(driver, database)
        neo4j_ver = version_info["neo4j_version"]
        cypher_ver = version_info["cypher_version"]
        print(f"  Neo4j: {neo4j_ver}, Cypher: {cypher_ver}")

        # Step 2: Capabilities
        print("Step 3: Detecting capabilities (GDS, APOC, GenAI)...")
        capabilities = discover_capabilities(driver, database)
        print(f"  Capabilities: {capabilities or ['none detected']}")

        # Step 3: Schema
        print("Step 4: Discovering schema...")
        schema = discover_schema(driver, database)
        print(f"  Labels: {len(schema['labels'])}, Rel types: {len(schema['relationship_types'])}")
        print(f"  Indexes (ONLINE): {len(schema['indexes'])}, Constraints: {len(schema['constraints'])}")

        # Step 4: Property value sampling
        print("Step 5: Sampling property values (COLLECT DISTINCT LIMIT 20)...")
        property_samples = discover_property_samples(driver, database, schema)
        total_sampled = sum(len(v) for v in property_samples.values())
        print(f"  Sampled {total_sampled} properties across {len(property_samples)} labels")

    finally:
        driver.close()

    # Step 5: Claude description generation
    if args.no_claude:
        print("Step 6: Skipping Claude description (--no-claude specified)")
        description = (
            f"A Neo4j graph database containing "
            f"{', '.join(schema['labels'][:3])} nodes "
            f"connected by {', '.join(schema['relationship_types'][:3])} relationships."
        )
        notes: list[str] = []
    else:
        print(f"Step 6: Generating description with Claude ({model_id})...")
        description, notes = generate_description(database, schema, property_samples, model_id)
        print(f"  Description: {description[:80]}...")
        print(f"  Notes: {len(notes)} items")

    # Build YAML blocks
    print("\nStep 7: Building YAML output...")
    yaml_data = build_dataset_yaml(
        domain=domain,
        database=database,
        uri=args.uri,
        username=args.username,
        neo4j_version=neo4j_ver,
        cypher_version=cypher_ver,
        capabilities=capabilities,
        schema=schema,
        property_samples=property_samples,
        description=description,
        notes=notes,
        read_only=args.read_only,
    )

    # Load existing file to preserve cases
    existing = load_existing_domain_yaml(output_path)
    if existing is not None:
        print(f"  Existing file found — preserving {len(existing.get('cases', []))} cases")
        yaml_data["cases"] = existing.get("cases", [])
    else:
        print("  New domain file — no cases to preserve")

    # Write output
    save_domain_yaml(output_path, yaml_data)
    print(f"\nDataset registered: {output_path}")

    # Summary
    labels = schema["labels"]
    rels = schema["relationship_types"]
    print(f"\nSummary:")
    print(f"  Labels ({len(labels)}): {', '.join(labels[:10])}{'...' if len(labels) > 10 else ''}")
    print(f"  Relationships ({len(rels)}): {', '.join(rels[:10])}{'...' if len(rels) > 10 else ''}")
    print(f"  Capabilities: {', '.join(capabilities) if capabilities else 'none'}")
    print(f"  ONLINE indexes: {len(schema['indexes'])}")
    print(f"\nNext step: make generate-questions DOMAIN={domain}")


if __name__ == "__main__":
    main()
