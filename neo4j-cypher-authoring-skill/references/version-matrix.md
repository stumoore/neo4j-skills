> Source: git@github.com:neo4j/docs-cypher.git@238ab12a — hand-authored from changelog + release notes
> Generated: 2026-03-22T00:00:00Z
> See: deprecations-additions-removals-compatibility.adoc

# Cypher 25 Feature Version Matrix

Use this file to check whether a feature is available on the target database before generating a query.
Cross-reference with the `database.neo4j_version` in the injected schema context.

| Feature | Min Version | Edition | GA / Preview |
|---|---|---|---|
| `CYPHER 25` pragma | 2025.06 | All | GA |
| `SHORTEST` keyword (replaces `shortestPath()`) | 2025.06 | All | GA |
| Quantified path patterns (QPE `{m,n}`) | 2025.06 | All | GA |
| `REPEATABLE ELEMENTS` match mode | 2025.06 | All | GA |
| `DIFFERENT RELATIONSHIPS` match mode | 2025.06 | All | GA |
| `vector()` constructor | 2025.10 | All | GA |
| `SEARCH` clause — vector indexes | 2026.02.1 | All | GA |
| `GRAPH TYPE` DDL clauses | 2026.02 | Enterprise | Preview |

## Notes

- **SEARCH clause**: GA for **vector indexes only** in 2026.02.1. Fulltext indexes still require
  `db.index.fulltext.queryNodes()` — SEARCH does not cover fulltext.
- **GRAPH TYPE**: Enterprise Edition only, Preview status. Not for production use.
- **`+` / `*` QPE shorthands**: Availability as shorthand for `{1,}` / `{0,}` — confirm against
  target version. Use explicit `{1,}` / `{0,}` for maximum compatibility.
- **`REPEATABLE ELEMENTS`**: Requires **bounded quantifiers** — `{m,n}` form only.
  Cannot be combined with `+`, `*`, or `{1,}` (unbounded).
- **`SHORTEST` keyword**: Do NOT use bare `(a)-[:REL]+(b)` — wrap the hop in a QPE group:
  `SHORTEST 1 (a)(()-[:REL]->()){1,}(b)`.
- **`elementId()`**: Replaces deprecated `id()` (which returns INTEGER) — available from 2025.06+.
  `elementId()` returns a STRING, stable only within a single transaction.
- **Aura caveat**: Aura instances report an internal version number. Treat Aura as always at
  the latest GA feature set (i.e., assume all features above are available).

## Version Compatibility Quick Reference

| Target DB | Available Features |
|---|---|
| Neo4j 2026.02.1+ (local/cloud) | All features above including SEARCH clause (vector) and GRAPH TYPE (Enterprise) |
| Neo4j 2025.10 – 2026.01.x | QPE, SHORTEST, REPEATABLE ELEMENTS, vector() — no SEARCH clause, no GRAPH TYPE |
| Neo4j 2025.06 – 2025.09.x | QPE, SHORTEST, REPEATABLE ELEMENTS — no vector(), no SEARCH clause |
| demo.neo4jlabs.com (companies/recommendations) | Treat as 2025.10–2026.01 range: no SEARCH clause; use `{1,}` not `+` for QPE |
