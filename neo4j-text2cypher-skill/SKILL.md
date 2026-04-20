---
name: neo4j-text2cypher-skill
description: Use when generating Cypher from a natural-language question against a Neo4j graph (text2cypher / LLM-driven querying). Covers schema-first prompting, the silent-wrong-answer correctness patterns, performance rules for LLM-generated queries, the modern Cypher subquery/quantified-path/SHORTEST idioms a generator should prefer, and picking between Cypher 5 and Cypher 25.
allowed-tools: WebFetch
---

# Neo4j text2cypher skill

Generating Cypher from a natural-language question is easy; generating Cypher that returns the **right** answer at an acceptable cost is not. Text2cypher failures fall into three buckets:

1. **Correctness** — query runs, no error, wrong rows. The most dangerous class.
2. **Performance** — query runs, returns rows, but scans the whole graph or blows the heap.
3. **Staleness** — the LLM emits 2019-era Cypher (list comprehensions for counting, `id()`, `OPTIONAL MATCH` + `collect`) when modern Cypher has cleaner and faster equivalents.

This skill covers all three, with reference material for each.

## When to use

Use this skill when:
- building an LLM → Cypher pipeline (RAG over a graph, "chat with your graph", text2cypher fine-tuning data, an agent that queries Neo4j)
- reviewing LLM-generated Cypher before it runs against production
- debugging a query that runs but returns the wrong rows or is unexpectedly slow
- deciding whether to target Cypher 5 or Cypher 25 in the generator

## Ground rules for the generator

1. **Give the LLM the schema, not the data.** `CALL apoc.meta.schema()` or the MCP schema endpoint. Inject node labels, rel types, property **types**, the **indexed** flag, **and relationship properties** — most schema extractors drop the last item, and missing rel-properties is the root cause of several correctness bugs (`IN_CITY.isCurrent`, etc.).
2. **Read `SHOW INDEXES` and tell the LLM which properties are indexed.** The biggest single lever on performance is whether the anchor filter hits an index.
3. **Show few-shot examples with intent + Cypher.** Three examples covering aggregation, multi-hop traversal, and a negation pattern remove the most common mistakes. Include at least one undirected relationship example and one `COUNT { }` / `EXISTS { }` example.
4. **Parameterize, don't interpolate.** User input goes in `$params`, never f-string interpolation. Prevents injection and stabilizes the query plan cache.
5. **Add `LIMIT` by default.** An LLM-authored 3-hop pattern without a limit on a moderately dense graph is a production incident. Even for "top N", make the generator emit `ORDER BY … LIMIT N` explicitly.
6. **Validate with `EXPLAIN`, not `PROFILE`.** `EXPLAIN` compiles only. `PROFILE` runs the query. In an LLM review loop, `EXPLAIN` is the safe gate.
7. **Emit the Cypher version prefix.** `CYPHER 5` or `CYPHER 25` as the first token, so the query returns the same result on any database regardless of that database's default language.
8. **Prefer modern subquery syntax.** `COUNT { }`, `EXISTS { }`, `COLLECT { }` beat `size([… | …])`, `OPTIONAL MATCH` + `collect()`, and most `WITH` pipelines. See [advanced-patterns.md](references/advanced-patterns.md).

## The fourteen correctness patterns

Each was reproduced on a real 76k-organization graph. They do not raise errors; they return the wrong rows.

1. **Names are not unique.** `{name:'Google'}` returned three distinct entities. Use `uri` / `elementId()` for single-entity lookup.
2. **Relationship direction rarely matches semantic symmetry.** `Apple-[:HAS_COMPETITOR]->()` = 26; `()-[:HAS_COMPETITOR]->Apple` = 386. For semantically-symmetric predicates, use undirected `-[:R]-`.
3. **Equality against a `LIST` property silently returns zero.** Use `'x' IN list` or `any(y IN list WHERE …)`.
4. **String vs `DATE`/`DATE_TIME` silently returns zero.** Wrap the literal with `date()` / `datetime()`.
5. **`NOT x = true` drops NULLs.** Use `coalesce(x, false) = false`.
6. **Aggregations skip NULLs.** `avg(revenueValue)` averaged over 7,904 of 76,102 rows silently. Always return `count(prop)` alongside `count(*)` for coverage visibility.
7. **Units and currencies are not normalized** — constrain or normalize.
8. **Multilingual alias lists (`allNames`) are noisy.** `'Apple' IN o.allNames` matched HSBC because Chinese-language blurbs contained "Apple".
9. **List-of-string "records"** (`"2024: 391B USD"`) need parsing, not direct aggregation.
10. **Hierarchy properties (`level`, `depth`) cause double-counting** if ignored.
11. **Multi-hop patterns explode.** 3 hops of `HAS_CUSTOMER` from one node returned 686 paths. Always `LIMIT` and aggregate.
12. **Relationships carry properties.** `IN_CITY.isCurrent`, `IN_CITY.isPrimary`, etc. — easy to forget.
13. **`id()` is deprecated** — use `elementId()`.
14. **Fuzzy match is not `=`** — use `CONTAINS`, `=~`, or a full-text index.

Full copy-paste-ready before/after examples: [correctness.md](references/correctness.md).

## The eight performance rules

1. **Always label every node pattern.** `MATCH (n)` is a full scan.
2. **Filter on indexed properties at the anchor.** Check `SHOW INDEXES`.
3. **Cap variable-length patterns.** `[:R*1..5]` not `[:R*]`.
4. **Project properties, not nodes.** `RETURN o.name, o.revenueValue`, not `RETURN o`.
5. **Aggregate before collecting.** `WITH c, count(o) AS n ORDER BY n DESC LIMIT 10` runs `ORDER BY`/`LIMIT` on small rows.
6. **Separate read and write phases** to avoid the `Eager` operator. Big batch updates go through `CALL { … } IN TRANSACTIONS OF 10000 ROWS`.
7. **Bulk writes: one `UNWIND $rows` call, not a loop.** 10k `MERGE` in a list-param takes one round-trip.
8. **`MERGE` needs an index/constraint on its key**, else it scans the whole label.

Plan reading, super-node mitigation, index recommendations: [performance.md](references/performance.md).

## Modern patterns a generator should prefer

- `EXISTS { (x)-[:R]-(:Y) }` instead of `size([…|…]) > 0`
- `COUNT { (x)-[:R]-(:Y) } > 5` instead of `OPTIONAL MATCH` + `WITH count(...)`
- `COLLECT { MATCH (x)-[:R]-(y) RETURN y.name }` in `RETURN`, scoped per row
- `CALL (x) { … }` (Cypher 25) for cleaner scoped subqueries
- `((n:L)-[r:R WHERE r.active]->(m:L)){1,5}` quantified paths with inline predicates
- `SHORTEST 1` / `SHORTEST k GROUPS` / `ALL SHORTEST` instead of `ORDER BY length(p) LIMIT`
- `CALL db.index.fulltext.queryNodes(...)` for approximate-name search
- `CALL db.index.vector.queryNodes(...)` for embedding similarity
- GDS procedures for "most central" / "community" / "similar" questions

Full examples plus an NL-intent → Cypher-pattern cheat sheet: [advanced-patterns.md](references/advanced-patterns.md).

## Cypher version for generated queries

- **Target Cypher 25** if the database is on Neo4j 2025.06+ and defaults to Cypher 25, or if you need the vector type, `$(…)` dynamic labels, or `WHEN/THEN` conditional subqueries.
- **Target Cypher 5** if the database still defaults to it.
- **Always emit the prefix.** `CYPHER 25 MATCH …` — deterministic results across databases.

Full diff: [cypher-5-vs-25.md](references/cypher-5-vs-25.md).

## Instructions

When invoked:

1. Pull the schema (APOC or MCP) **and** `SHOW INDEXES`. Inject both into the prompt verbatim — don't summarize.
2. Retrieve 3–5 question/Cypher few-shots that are semantically close to the user's question (vector similarity over a curated example bank).
3. Generate the Cypher with `CYPHER 25` / `CYPHER 5` as the first token.
4. Run `EXPLAIN` on the generated query. On syntax error, feed the error back and retry once.
5. Audit against the fourteen correctness patterns (three highest-hit: date-vs-string, list-equality, direction asymmetry).
6. Audit against the eight performance rules (three highest-hit: missing label, missing `LIMIT`, unbounded variable-length).
7. Bias toward modern subquery / quantified-path / `SHORTEST` forms when they fit.
8. Execute and return results with coverage (`count(*)` + `count(prop)` where applicable).

## Resources

- [Text2cypher guide (Neo4j blog)](https://neo4j.com/blog/genai/text2cypher-guide/)
- [APOC schema inspection](https://neo4j.com/docs/apoc/current/overview/apoc.meta/apoc.meta.schema/)
- [Execution plans and query tuning](https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/)
- [Neo4j MCP server](https://neo4j.com/docs/mcp/current/)
- [Cypher version selection](https://neo4j.com/docs/cypher-manual/current/queries/select-version/)
- [neo4j-labs/text2cypher repo (datasets + evals)](https://github.com/neo4j-labs/text2cypher)
