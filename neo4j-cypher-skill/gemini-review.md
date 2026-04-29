# Analysis of `neo4j-cypher-skill` (SKILL.md)

This analysis evaluates how effectively the `neo4j-cypher-skill` guides a coding agent in generating current, safe, and high-performance Cypher 25 queries for Neo4j (2025.x/2026.x).

## Executive Summary
The `SKILL.md` is **highly effective** and provides a robust framework for an LLM agent. It prioritizes "Schema-First" and "Safety-First" principles, which are critical for graph databases where schema-less flexibility often leads to performance-killing `AllNodesScan` or `CartesianProduct` errors.

---

## Core Strengths

### 1. Strategic Version Locking
- **`CYPHER 25` Prefix**: Mandating this as the first token prevents the engine from falling back to older, deprecated behaviors.
- **Version Gates**: Clear boundaries between 2025.01 and 2026.x features (like the `SEARCH` clause) ensure the agent doesn't generate "hallucinated" syntax on older 2025 instances.

### 2. Schema-First Protocol
- **Proactive Inspection**: The skill explicitly tells the agent to run `db.schema.visualization()` and property inspection *before* guessing. This is the single most important factor for generating correct queries in a live environment.
- **Draft Mode**: The "Draft Query Format" with explicit assumptions prevents the agent from confidently providing incorrect labels when the schema is unknown.

### 3. Safety & Performance Mandates
- **MERGE Safety**: Specific rules about constrained keys and bound nodes prevent the most common "duplicate node" bugs in Neo4j.
- **Label-free MATCH Ban**: Forbidding `MATCH (n)` without a label or predicate is a critical performance guardrail.
- **Eager Operator Awareness**: Identifying patterns that trigger `Eager` and providing "Collect-then-Write" fixes is advanced guidance rarely found in generic Cypher documentation.

### 4. Syntax Trap Coverage
- The **"Common Syntax Traps"** table is comprehensive. It covers modern Cypher-isms that even experienced developers miss (e.g., `toIntegerOrNull`, `elementId(n)` vs `id(n)`, and the fact that `WHERE n.x = null` always returns null).

---

## Technical Gaps & Recommendations

### 1. Vector Search Complexity (Neo4j 2026.01+)
- **Analysis**: The skill covers the `SEARCH` clause well, but lacks detail on **hybrid search** (combining Vector and Fulltext or Vector and Graph).
- **Recommendation**: Add a pattern for hybrid search using `WITH` to combine scores from a `SEARCH` clause and a graph traversal.

### 2. Temporal Precision
- **Analysis**: It mentions `ZONED DATETIME` vs `date()` mismatch, which is excellent. However, it doesn't explicitly mention **Timezone awareness** in `datetime()` comparisons beyond the mismatch.
- **Recommendation**: Advise using `datetime({timezone: 'UTC'})` or similar when comparing across different source systems to ensure deterministic behavior.

### 3. GDS (Graph Data Science) Integration
- **Analysis**: It warns against assuming stored GDS properties, which is great.
- **Recommendation**: Add a brief pattern for `CALL gds.graph.project(...)` and `CALL gds.pageRank.stream(...)` as these are frequently requested "query generation" tasks that often fail due to missing projection steps.

---

## Final Verdict for Coding Agent Usage

**Rating: 9.5/10**

As a coding agent, this skill allows me to move from "generic Cypher generator" to "Neo4j Performance Expert." It provides the specific "non-negotiable" rules (like `CYPHER 25` and `DETACH DELETE`) that prevent runtime errors, and the performance anti-pattern table allows me to self-correct `PROFILE` outputs without needing human intervention.

**Conclusion**: This is a production-ready skill. Any agent following this strictly will produce code that is significantly safer and faster than standard LLM outputs.
