#!/usr/bin/env python3
"""
question_validator.py — Business-language question validator.

Checks that test case questions are phrased as casual, business-user questions
(the kind a non-technical analyst or product manager would ask) and do NOT
contain:
  - Explicit Cypher syntax patterns (node patterns, relationship patterns)
  - Property dot-access syntax in code context (.name, .rating on variable names)
  - GDS/APOC/db.index procedure prefixes
  - Known schema label/rel-type names from the passed schema dict
  - ALL_CAPS_WITH_UNDERSCORES relationship type patterns (when schema-matched)

Common English words like "return", "distinct", "match", "create", "delete",
"shortest", "profile", "collect" are NOT flagged — they appear naturally in
business questions. Only explicit Cypher syntax patterns are rejected.

Usage:
    from question_validator import QuestionValidator
    validator = QuestionValidator(schema=schema_dict)
    ok, reason = validator.validate("Which companies have no subsidiaries?")
    if not ok:
        print(f"INVALID: {reason}")

    # Or using the module-level helper (no schema-awareness):
    from question_validator import validate
    ok, reason = validate("MATCH (n:Org) RETURN n")
"""

from __future__ import annotations

import re
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Cypher syntax patterns — always flag these regardless of context
# ---------------------------------------------------------------------------

# Node pattern syntax: ( optionally followed by words/spaces, then :UppercaseWord
# Requires an opening paren so ": The" in titles does NOT match.
_NODE_PATTERN = re.compile(r"\([\w\s]*:[A-Z][a-zA-Z]+")

# Relationship type in brackets: [:REL_TYPE] or [r:REL_TYPE]
_REL_BRACKET_PATTERN = re.compile(r"\[[\w\s]*:[A-Z_]+\]")

# MATCH followed by opening paren — explicit Cypher MATCH clause
_MATCH_PAREN = re.compile(r"\bMATCH\s*\(", re.IGNORECASE)

# RETURN followed by property dot-access: RETURN n.property
_RETURN_DOT = re.compile(r"\bRETURN\s+\w+\.", re.IGNORECASE)

# WHERE followed by property dot-access: WHERE n.age > 30
# Requires the dot to be followed by a letter (not end-of-word/sentence)
# so "where available." and "where specified." do NOT match.
_WHERE_DOT = re.compile(r"\bWHERE\s+\w+\.[a-zA-Z]", re.IGNORECASE)

# WITH ... AS aliasing pattern: WITH x AS y
_WITH_AS = re.compile(r"\bWITH\s+\w+\s+AS\s+\w+\b", re.IGNORECASE)

# Property comparison: variable.property = value (e.g. n.name = 'Alice')
_PROP_COMPARISON = re.compile(r"\b\w+\.\w+\s*[=<>!]")

# Backtick identifiers (Cypher escaping)
_BACKTICK = re.compile(r"`[^`]+`")

# ---------------------------------------------------------------------------
# Dot-access in code context — lower.lower or camelCase.camelCase variable access
# (excludes domain names, URLs, sentence-ending periods)
# ---------------------------------------------------------------------------

# Matches patterns like n.name, movie.title, node.property — where both sides
# are lowercase or camelCase identifiers (not starting with uppercase/digit)
_DOT_ACCESS_CODE = re.compile(r"\b[a-z][a-zA-Z0-9_]{0,}\.[a-z][a-zA-Z0-9_]{1,}\b")

# Domain names / URLs to exclude from dot-access detection
_URL_LIKE = re.compile(
    r"https?://|www\.|"
    r"\b\w+\.(com|org|net|io|co|uk|de|fr|eu|gov|edu|info|biz)\b"
)

# ---------------------------------------------------------------------------
# Procedure/function prefixes — always flag
# ---------------------------------------------------------------------------

_PROCEDURE_PREFIXES = [
    "gds.",
    "apoc.",
    "db.index.",
    "db.schema.",
    "dbms.",
    "ai.embedding",
    "vector.",
    "algo.",
]

# ---------------------------------------------------------------------------
# ALL_CAPS pattern for relationship type detection (schema-aware)
# Matches: SENT, NEXT, FIRST, SIMILAR_TO, RESPONDING_FOR, HAS_SUBSIDIARY, etc.
# Pattern: starts uppercase, ends uppercase, middle is uppercase or underscore
# ---------------------------------------------------------------------------
_ALL_CAPS_PATTERN = re.compile(r"\b([A-Z][A-Z_]+[A-Z])\b")


class QuestionValidator:
    """
    Validates that a question string is phrased in casual business language.

    Uses pattern-based detection rather than keyword lists. Common English words
    like "return", "distinct", "match", "create", "delete", "shortest", "profile",
    "collect" are intentionally NOT flagged — only explicit Cypher syntax patterns
    are rejected.

    Args:
        schema: Optional dict (from dataset.schema) used for schema-aware
                rejection of known label names and relationship type names.
    """

    def __init__(self, schema: Optional[dict[str, Any]] = None) -> None:
        self._schema_labels: frozenset[str] = frozenset()
        self._schema_rel_types: frozenset[str] = frozenset()

        if schema and isinstance(schema, dict):
            # Collect known label names from schema.nodes
            nodes = schema.get("nodes", {})
            if isinstance(nodes, dict):
                self._schema_labels = frozenset(nodes.keys())

            # Collect known relationship type names from schema.relationships
            rels = schema.get("relationships", [])
            if isinstance(rels, list):
                types: list[str] = []
                for r in rels:
                    if isinstance(r, dict) and r.get("type"):
                        types.append(str(r["type"]))
                self._schema_rel_types = frozenset(types)

    def validate(self, question: str) -> tuple[bool, str]:
        """
        Check whether the question is valid business language.

        Returns:
            (True, "")             — valid question
            (False, reason_str)    — invalid, with a description of why
        """
        if not question or not question.strip():
            return False, "Empty question"

        q = question.strip()

        # ── Explicit Cypher node pattern syntax: (n:Label) or (:Label) ───────
        m = _NODE_PATTERN.search(q)
        if m:
            return False, f"Contains Cypher node pattern syntax: '{m.group(0)}'"

        # ── Relationship bracket syntax: [:REL_TYPE] ──────────────────────────
        m = _REL_BRACKET_PATTERN.search(q)
        if m:
            return False, f"Contains Cypher relationship bracket syntax: '{m.group(0)}'"

        # ── MATCH ( — explicit Cypher MATCH clause ────────────────────────────
        m = _MATCH_PAREN.search(q)
        if m:
            return False, f"Contains Cypher MATCH clause: '{m.group(0).strip()}'"

        # ── RETURN n. — RETURN followed by property access ────────────────────
        m = _RETURN_DOT.search(q)
        if m:
            return False, f"Contains Cypher RETURN with property access: '{m.group(0).strip()}'"

        # ── WHERE n. — WHERE followed by property access ──────────────────────
        m = _WHERE_DOT.search(q)
        if m:
            return False, f"Contains Cypher WHERE with property access: '{m.group(0).strip()}'"

        # ── WITH x AS y — Cypher aliasing syntax ─────────────────────────────
        m = _WITH_AS.search(q)
        if m:
            return False, f"Contains Cypher WITH...AS aliasing: '{m.group(0)}'"

        # ── n.property = — property comparison ───────────────────────────────
        m = _PROP_COMPARISON.search(q)
        if m:
            return False, f"Contains Cypher property comparison: '{m.group(0)}'"

        # ── Backtick identifiers ──────────────────────────────────────────────
        m = _BACKTICK.search(q)
        if m:
            return False, f"Contains backtick identifier: '{m.group(0)}'"

        # ── Procedure/function prefixes ───────────────────────────────────────
        q_lower = q.lower()
        for prefix in _PROCEDURE_PREFIXES:
            if prefix in q_lower:
                return False, f"Contains procedure prefix: '{prefix}'"

        # ── Dot-access property syntax (code context only) ───────────────────
        # Only flag if the question doesn't look like it contains a URL
        if not _URL_LIKE.search(q):
            m = _DOT_ACCESS_CODE.search(q)
            if m:
                return False, f"Contains dot-access property syntax: '{m.group(0)}'"

        # ── Schema-aware: known label names ───────────────────────────────────
        for label in self._schema_labels:
            if re.search(r"\b" + re.escape(label) + r"\b", q):
                return False, f"Contains schema label name: '{label}'"

        # ── Schema-aware: relationship type names (ALL_CAPS pattern + schema match)
        # Only flag if the token matches ALL_CAPS pattern AND is a known rel-type
        all_caps_matches = _ALL_CAPS_PATTERN.findall(q)
        for token in all_caps_matches:
            if token in self._schema_rel_types:
                return False, f"Contains schema relationship type: '{token}'"

        return True, ""


# ---------------------------------------------------------------------------
# Module-level convenience function (no schema awareness)
# ---------------------------------------------------------------------------


def validate(question: str, schema: Optional[dict[str, Any]] = None) -> tuple[bool, str]:
    """
    Validate a question string.

    Args:
        question: The question text to validate.
        schema:   Optional dataset schema dict for schema-aware validation.

    Returns:
        (True, "")          — valid business-language question
        (False, reason)     — invalid, with explanation
    """
    v = QuestionValidator(schema=schema)
    return v.validate(question)


# ---------------------------------------------------------------------------
# Self-test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Schema for schema-aware tests
    schema_for_test = {
        "nodes": {"Organization": {}, "Article": {}, "User": {}},
        "relationships": [
            {"type": "HAS_SUBSIDIARY"},
            {"type": "MENTIONS"},
            {"type": "SIMILAR_TO"},
        ],
    }

    validator = QuestionValidator(schema=schema_for_test)
    no_schema_validator = QuestionValidator()

    _TESTS: list[tuple[str, bool, bool]] = [
        # (question, expected_with_schema, expected_without_schema)

        # ── Valid business questions (should PASS) ──────────────────────────
        ("Which companies have more than 5 subsidiaries?", True, True),
        ("Show me the top 10 movies by average rating", True, True),
        ("What are the most popular tags in the last year?", True, True),
        # Previously false-positive cases that should now PASS:
        ("List all distinct categories", True, True),
        ("Return its name and the count", True, True),
        ("Find the shortest path between X and Y", True, True),
        ("Create a new user named Alice", True, True),
        ("Delete all orphaned records", True, True),
        ("Which users have distinct preferences?", True, True),  # 'distinct' as English
        ("What is the profile of the top customer?", True, True),  # 'profile' as English
        ("Collect all results and show the summary", True, True),  # 'collect' as English
        ("Match the invoice to the purchase order", True, True),  # 'match' as English
        # Book title with colon — should NOT trigger label detection
        (
            "Find all books reachable from 'The Berlin Stories: The Last of Mr Norris'",
            True,
            True,
        ),
        # MAC address with colon — should NOT trigger label detection
        (
            "Trace the snapshot history for device with MAC '08:55:31:6A:FF:5'",
            True,
            True,
        ),

        # ── True violations — Cypher syntax (should FAIL regardless of schema) ─
        ("Find all (:Organization)-[:HAS_SUBSIDIARY]->() with depth > 2", False, False),
        ("MATCH (n:Movie) RETURN n.title LIMIT 10", False, False),
        ("MATCH (n:Organization) RETURN n", False, False),
        ("[:HAS_SUBSIDIARY]", False, False),
        ("gds.pageRank is highest", False, False),
        ("Use apoc.text.split to tokenize names", False, False),
        ("Get the movie.title for films after 2000", False, False),
        ("WHERE n.age > 30", False, False),
        ("n.name = 'Alice'", False, False),
        # ── Schema-aware violations (FAIL with schema, PASS without) ──────────
        ("Show me all User nodes in the graph", False, True),
        ("Which users have bought products?", True, True),  # 'users' != 'User' label
    ]

    passed = 0
    failed = 0
    for question, expected_schema, expected_no_schema in _TESTS:
        ok_schema, reason_schema = validator.validate(question)
        ok_no_schema, reason_no_schema = no_schema_validator.validate(question)

        schema_ok = ok_schema == expected_schema
        no_schema_ok = ok_no_schema == expected_no_schema
        all_ok = schema_ok and no_schema_ok

        status = "PASS" if all_ok else "FAIL"
        if all_ok:
            passed += 1
        else:
            failed += 1

        print(f"[{status}] schema={ok_schema!s:5}(exp={expected_schema!s:5})  "
              f"no-schema={ok_no_schema!s:5}(exp={expected_no_schema!s:5})  "
              f"{question[:60]}")
        if not schema_ok:
            print(f"         Schema reason: {reason_schema}")
        if not no_schema_ok:
            print(f"         No-schema reason: {reason_no_schema}")

    print(f"\n{passed}/{passed + failed} tests passed")
    if failed:
        raise SystemExit(1)
