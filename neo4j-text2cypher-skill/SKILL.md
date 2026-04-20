---
name: neo4j-text2cypher-skill
description: Use when generating Cypher from natural language via the official Neo4j MCP Cypher server (mcp-neo4j-cypher). Covers the server's three tools (get_neo4j_schema, read_neo4j_cypher, write_neo4j_cypher), the silent-wrong-answer correctness patterns, the performance rules that matter under the server's 30s timeout, and the modern Cypher idioms a generator should prefer.
allowed-tools: WebFetch
---

# Neo4j text2cypher skill (via mcp-neo4j-cypher)

This skill is tuned to the **official Neo4j MCP Cypher server** — [`mcp-neo4j-cypher`](https://github.com/neo4j-contrib/mcp-neo4j/tree/main/servers/mcp-neo4j-cypher), distributed on PyPI, Docker Hub, and as part of the Neo4j Labs MCP stack. It is **not** tied to any specific graph; all advice applies whatever schema the server is pointed at.

If the MCP server is namespaced (env `NEO4J_NAMESPACE=mydb`), every tool name is prefixed with that namespace — e.g. `mydb-read_neo4j_cypher`. The rest of this file refers to the unprefixed names.

## The three tools

| Tool                    | Purpose                                   | Input                                     | Output                                                |
|-------------------------|-------------------------------------------|-------------------------------------------|-------------------------------------------------------|
| `get_neo4j_schema`      | Introspect labels, rel-types, properties  | optional `sample_param` (int)             | JSON — nodes with properties (type + `indexed` flag) and relationships |
| `read_neo4j_cypher`     | Run a read-only Cypher query              | `query` (string), optional `params` (dict)| JSON array of result rows                             |
| `write_neo4j_cypher`    | Run a write / schema / admin query        | `query` (string), optional `params` (dict)| Summary counters                                      |

Server-side constraints you must plan around:

- **30-second read timeout by default** (`NEO4J_READ_TIMEOUT`). Queries exceeding it are cancelled.
- **Response token truncation** when `NEO4J_RESPONSE_TOKEN_LIMIT` is set — a large result can silently return a truncated prefix. Always `LIMIT`.
- **Schema sampling** via `NEO4J_SCHEMA_SAMPLE_SIZE` (default 1000). Rare properties and long tails may be missed; don't treat `get_neo4j_schema` as ground truth for every property.
- **Read-only mode** (`NEO4J_READ_ONLY=true`) disables `write_neo4j_cypher` entirely. In this mode the generator cannot create indexes or constraints — plan for the index that's already there.
- **APOC required** for `get_neo4j_schema`. If APOC is missing, the tool errors; fall back to `CALL db.labels()`, `CALL db.relationshipTypes()`, `CALL db.schema.nodeTypeProperties()`.

## The three failure classes

Text2cypher failures are rarely syntax errors. They fall into three classes, all of which this skill addresses:

1. **Correctness** — query runs, no error, wrong rows. The most dangerous class. See [correctness.md](references/correctness.md).
2. **Performance** — query runs but scans the whole graph, times out at 30s, or returns a truncated result. See [performance.md](references/performance.md).
3. **Staleness** — the LLM emits 2019-era Cypher (list comprehensions for counting, `id()`, `OPTIONAL MATCH` + `collect`) when `COUNT { }`, `elementId()`, and `COLLECT { }` are cleaner and faster. See [advanced-patterns.md](references/advanced-patterns.md).

Version-specific items (Cypher 5 vs Cypher 25) live in [cypher-5-vs-25.md](references/cypher-5-vs-25.md).

## When to use

Use this skill when:
- wiring an LLM to `mcp-neo4j-cypher` (Claude Desktop, Claude Code, another MCP client)
- reviewing LLM-generated Cypher before `read_neo4j_cypher` / `write_neo4j_cypher` executes it
- debugging a query that "works" but returns the wrong rows, gets truncated, or times out
- picking the Cypher version prefix the generator should emit

## Ground rules for the generator

1. **Always call `get_neo4j_schema` first in a new session** and inject the JSON verbatim into the LLM context. Do not summarize. Property **types** and the **`indexed`** flag are the two most load-bearing hints; rel-properties are the most commonly omitted.
2. **Also call `SHOW INDEXES`** via `read_neo4j_cypher` — the schema tool reports which properties are indexed but not what kind (range / text / point / vector / fulltext). Full-text and vector indexes enable entirely different query patterns.
3. **Use the tool's `params` argument for every value.** `read_neo4j_cypher({query: "MATCH (n:Person {name:$name}) RETURN n", params: {name: "Alice"}})`. Never string-interpolate user input into `query`.
4. **Always emit `LIMIT`.** The 30-second timeout and token-limit truncation both punish unbounded results. Even for "top N", write `ORDER BY … LIMIT N` explicitly.
5. **Route writes through `write_neo4j_cypher` only.** If the server is in read-only mode this tool won't exist — the generator must be told up-front.
6. **Emit `CYPHER 5` or `CYPHER 25` as the first token** so results are deterministic across databases with different defaults.
7. **Prefer modern subquery syntax.** `COUNT { }`, `EXISTS { }`, `COLLECT { }` beat `size([…|…])`, `OPTIONAL MATCH` + `collect()`, and most `WITH` pipelines.
8. **On an error from `read_neo4j_cypher`, feed the error back to the LLM and retry once.** Don't retry blindly more than that — repeated errors mean the schema or intent needs to be revisited.

## The fourteen correctness patterns (summary)

These silently return the wrong rows under every version and every driver.

1. **Names are not unique** — multiple nodes can share the display name. Use a unique key (`elementId()`, `uri`, `id`).
2. **Relationship direction ≠ semantic symmetry** — "competitor of" feels symmetric but is stored one-way. Use undirected `-[:R]-`.
3. **Equality against a `LIST<…>` returns zero** — use `IN` or `any(x IN list WHERE …)`.
4. **String vs `DATE`/`DATE_TIME` returns zero** — wrap literals with `date()` / `datetime()`.
5. **`NOT x = true` drops NULLs** — use `coalesce(x, false) = false`.
6. **Aggregations skip NULLs** — always return `count(prop)` next to `count(*)` to surface coverage.
7. **Units/currencies are not normalized** — constrain or normalize.
8. **Alias lists (`allNames`, `aliases`, translations) are noisy** — use the canonical property for filters.
9. **List-of-string "records"** need parsing, not direct aggregation.
10. **Hierarchy properties (`level`, `depth`, `tier`)** cause double-counting if ignored.
11. **Variable-length / multi-hop paths explode** — always `LIMIT` and aggregate.
12. **Relationships carry properties too** — always inspect via `get_neo4j_schema`.
13. **`id()` is deprecated** — use `elementId()`.
14. **Fuzzy match is not `=`** — use `CONTAINS`, `=~`, or a full-text index.

Copy-paste-ready before/after queries with schema-agnostic examples: [correctness.md](references/correctness.md).

## The eight performance rules (summary)

1. **Label every node pattern.** `MATCH (n)` is a full graph scan.
2. **Filter on indexed properties at the anchor.** Check `SHOW INDEXES`.
3. **Cap variable-length patterns.** `[:R*1..5]` not `[:R*]`.
4. **Project properties, not whole nodes.** Smaller rows, fewer cold reads, less risk of response truncation.
5. **Aggregate before projecting.** `WITH x, count(y) AS n ORDER BY n DESC LIMIT 10` keeps sort/limit on small rows.
6. **Separate read and write phases** to avoid the `Eager` operator.
7. **Bulk writes: one `UNWIND $rows` call.** Pass the list via `params`; do not loop `write_neo4j_cypher`.
8. **`MERGE` needs a constraint or index** on its key property, otherwise it scans the whole label on every call.

Plan reading, super-node mitigation, and MCP-specific timing: [performance.md](references/performance.md).

## Modern patterns to prefer

- `WHERE EXISTS { (x)-[:R]-(:Y) }` instead of `size([…|…]) > 0`
- `WHERE COUNT { (x)-[:R]-(:Y) } > 5` instead of `OPTIONAL MATCH … WITH count(*)`
- `RETURN COLLECT { MATCH (x)-[:R]-(y) RETURN y.name } AS ys` instead of `OPTIONAL MATCH` + `collect()`
- `CALL (x) { … }` scoped subqueries (Cypher 25)
- `((a)-[r:R WHERE r.active]->(b)){1,5}` quantified paths with inline predicates
- `SHORTEST 1` / `SHORTEST k GROUPS` / `ALL SHORTEST` for shortest-path queries
- `CALL db.index.fulltext.queryNodes(name, q)` for approximate-name lookup
- `CALL db.index.vector.queryNodes(name, k, v)` / `SEARCH … NEAREST $v` (Cypher 25) for semantic similarity
- GDS procedures for "most central" / "community" / "similar" questions

Full examples plus an NL-intent → Cypher-pattern cheat sheet: [advanced-patterns.md](references/advanced-patterns.md).

## Instructions (end-to-end loop)

When invoked to generate Cypher against an `mcp-neo4j-cypher` server:

1. **Session warmup, once per connection:**
   - Call `get_neo4j_schema` — inject JSON verbatim into LLM context.
   - Call `read_neo4j_cypher({query: "SHOW INDEXES"})` — include index types (range/text/point/fulltext/vector).
   - If the graph uses GDS, inspect available procedures (`CALL gds.list()` or the MCP's GDS-procedures tool where exposed).

2. **Per user question:**
   - Retrieve 3–5 question/Cypher few-shots that are semantically close to the question (vector similarity over a curated example bank).
   - Ask the LLM to produce Cypher with `CYPHER 25` (or `CYPHER 5`) as the first token, and every value as `$param` — it must return `{query, params}` shape for the MCP call.
   - Audit the generated query against the fourteen correctness patterns and eight performance rules. Top three of each in practice:
     - Correctness: date-vs-string (#4), list equality (#3), directional asymmetry (#2)
     - Performance: missing label, missing `LIMIT`, unbounded variable-length
   - Execute via `read_neo4j_cypher` (or `write_neo4j_cypher` for mutations). On error, feed the error back to the LLM and retry once.

3. **When results look thin or wrong:**
   - For aggregations, re-run with `count(*)` + `count(prop)` to see coverage.
   - For name lookups, also run `CALL db.index.fulltext.queryNodes(...)` if a fulltext index exists.
   - For negations, check whether the query is missing NULL rows (#5).

4. **Always surface uncertainty.** Report the row count, and for aggregations, report coverage. Do not present an `avg()` over 10% of the corpus as "the average".

## Resources

- [`mcp-neo4j-cypher` README](https://github.com/neo4j-contrib/mcp-neo4j/blob/main/servers/mcp-neo4j-cypher/README.md)
- [Neo4j MCP docs](https://neo4j.com/docs/mcp/current/)
- [Text2Cypher Guide (Neo4j)](https://neo4j.com/blog/genai/text2cypher-guide/)
- [neo4j-labs/text2cypher — datasets & evals](https://github.com/neo4j-labs/text2cypher)
- [Cypher execution plans and query tuning](https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/)
- [Cypher version selection](https://neo4j.com/docs/cypher-manual/current/queries/select-version/)
