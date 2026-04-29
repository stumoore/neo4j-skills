---
name: neo4j-cypher-skill
description: Generates, optimizes, and validates Cypher 25 queries for Neo4j 2025.x and 2026.x.
  Use when writing new Cypher queries, optimizing slow queries, graph pattern matching, vector
  or fulltext search, subqueries, or batch writes. Covers MATCH, MERGE, CREATE, WITH, RETURN,
  CALL, UNWIND, FOREACH, LOAD CSV, SEARCH, expressions, functions, indexes, and subqueries.
  Does NOT handle driver migration or API changes — use neo4j-migration-skill.
  Does NOT cover DB administration or server ops — use neo4j-cli-tools-skill.
compatibility: Neo4j >= 2025.01 (safe baseline); Cypher 25
---

## When to Use
- Writing, optimizing, or debugging Cypher queries
- Graph pattern matching, QPEs, variable-length paths
- Vector/fulltext search, subqueries, batch writes, LOAD CSV

## When NOT to Use
- **Driver migration/API changes** → `neo4j-migration-skill`
- **DB admin** (users, config, backups) → `neo4j-cli-tools-skill`
- **GQL clauses** (`LET`, `FINISH`, `FILTER`, `INSERT`) — illegal in Cypher; use `WITH`/`RETURN`/`WHERE`/`CREATE`

---

## Pre-flight

| ? | Known | Unknown |
|---|---|---|
| Schema | Use directly | Run Schema-First Protocol |
| Neo4j version | Use version features | Default to 2025.01 safe set |
| Executing (not generating)? | Use EXPLAIN + write gate | State query is unvalidated |

Schema unknown + no tool → produce non-executable sketch outside a code block:
```
(<SOURCE_LABEL> {<KEY>: $value})-[:<REL_TYPE>]->(<TARGET_LABEL>)
```
Never fill guessed names — realistic guesses get copied blindly.

---

## Defaults — apply every query

1. `CYPHER 25` — first token; never repeat after `UNION` or inside subqueries
2. Schema first — inspect before writing; if schema in prompt, use it directly
3. `MERGE` on constrained key only; rel `MERGE` on already-bound endpoints only
4. Label-free `MATCH (n)` forbidden unless bound or followed by `WHERE n:$($label)`
5. `LIMIT 25` default on all exploratory reads; push `WITH n LIMIT` before high-cardinality operations (variable-length traversals, fan-out MATCH, Cartesian products)
6. Comments: `//` only — `--` is SQL, invalid
7. `REPEATABLE ELEMENTS` / `DIFFERENT RELATIONSHIPS` go after `MATCH`, not end of pattern
8. `SHOW` commands: `YIELD` before `WHERE`; no `UNION`
9. Inline node predicates `(:Label WHERE p=x)` — valid in `MATCH` only
10. `WHERE` cannot follow bare `UNWIND` — use `WITH x WHERE`
11. `(a)-[:R]-(b)` — undirected matches both directions, double-counts; use directed unless unknown
12. `DETACH DELETE` — plain `DELETE` throws if node has relationships

---

## Style

| Element | Convention |
|---|---|
| Node labels | PascalCase `:Person` |
| Rel types | SCREAMING_SNAKE_CASE `:KNOWS` |
| Properties/vars | camelCase `firstName` |
| Clauses | UPPERCASE `MATCH` |
| Booleans/null | lowercase `true false null` |
| Strings | single-quoted; double only if contains `'` |

> Schema is truth. `:Person`, `:KNOWS`, `name` in examples are illustrative — substitute real names from schema.

---

## Schema-First Protocol

Schema in context → use it, skip inspection.

Schema missing → run:
```cypher
CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships;
SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state WHERE state = 'ONLINE';
SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties;
SHOW PROCEDURES YIELD name RETURN split(name,'.')[0] AS namespace, count(*) AS procedures;
```

Property types per label — check APOC first:
```cypher
// If APOC available (preferred — use this):
CALL apoc.meta.schema() YIELD value RETURN value;

// No APOC AND database ≤ 100k nodes/rels only (expensive on large graphs):
CALL db.schema.nodeTypeProperties() YIELD nodeType, propertyName, propertyTypes, mandatory;
CALL db.schema.relTypeProperties() YIELD relType, propertyName, propertyTypes, mandatory;
```

Validate before returning any query: label exists · rel type+direction correct · property on that label · index ONLINE.

---

## Key Patterns

### MERGE
```cypher
// MERGE on constrained key; set extras in ON CREATE/ON MATCH
CYPHER 25
MATCH (a:Person {id: $a}) MATCH (b:Person {id: $b})
MERGE (a)-[r:KNOWS]->(b)
  ON CREATE SET r.since = date()
  ON MATCH  SET r.lastSeen = date()
```
`SET n = {}` replaces all props. `SET n += {}` merges (safe partial update). Use `+=` for updates.

### WITH scope
```cypher
CYPHER 25
MATCH (a:Person)-[:KNOWS]->(b:Person)
WITH a, count(*) AS friends   // b dropped here
WHERE friends > 5
RETURN a.name, friends ORDER BY friends DESC
```
Every var not listed in `WITH` is dropped. `WITH *` carries all forward.

### Subqueries — cheat sheet
```
EXISTS { (a)-[:R]->(b) }                           // boolean check
COUNT  { (a)-[:R]->(b) WHERE a.x > 0 }             // count
COLLECT { MATCH (a)-[:R]->(b) RETURN b.name }       // collect list (full MATCH+RETURN required)
CALL (p) { MATCH (p)-[:ACTED_IN]->(m) RETURN m }    // correlated subquery (explicit import)
OPTIONAL CALL (p) { ... }                           // nullable subquery
```
`CALL { WITH x ... }` deprecated → `CALL (x) { ... }`. `COLLECT {}` returns exactly one column.

### CALL IN TRANSACTIONS (bulk writes)
```cypher
CYPHER 25
LOAD CSV WITH HEADERS FROM 'file:///data.csv' AS row
CALL (row) {
  MERGE (p:Person {id: row.id}) SET p += row
} IN TRANSACTIONS OF 1000 ROWS ON ERROR CONTINUE REPORT STATUS AS s
```
Input stream must be outside subquery. Auto-commit only — never wrap in `beginTransaction()`. `PERIODIC COMMIT` deprecated.

### QPE basics
```cypher
CYPHER 25
MATCH SHORTEST 1 (a:Person {name:'Alice'})(()-[:KNOWS]->()){1,}(b:Person {name:'Bob'})
RETURN b.name
```
Quantifier outside group: `(pattern){N,M}`. Groups start+end with node. `REPEATABLE ELEMENTS` needs bounded `{m,n}`.

---

## Common Syntax Traps (top causes of broken queries)

| Wrong | Right |
|---|---|
| `ORDER BY n.prop AS x DESC` | `ORDER BY n.prop DESC` |
| `ORDER BY preAggVar` after agg RETURN | Use RETURN alias |
| `count(r WHERE r.x=5)` | `sum(CASE WHEN r.x=5 THEN 1 ELSE 0 END)` |
| `UNWIND list AS x WHERE x>5` | `UNWIND list AS x WITH x WHERE x>5` |
| `least(a,b)` / `greatest(a,b)` | `CASE WHEN a<b THEN a ELSE b END` |
| `-- comment` | `// comment` |
| `shortestPath((a)-[*]->(b))` | `SHORTEST 1 (a)(()-[]->()){1,}(b)` |
| `id(n)` | `elementId(n)` |
| `[:REL*1..5]` | `(()-[:REL]->()){1,5}` |
| `CALL { WITH x ... }` | `CALL (x) { ... }` |
| `COLLECT { (a)-[:R]->(b) }` | `COLLECT { MATCH ... RETURN b }` |
| `SET n = {k:v}` partial update | `SET n += {k:v}` |
| `DELETE n` with relationships | `DETACH DELETE n` |
| `WHERE n.x = null` | `WHERE n.x IS NULL` |
| `toInteger(null)` throws | `toIntegerOrNull(null)` |
| `n.$key` dynamic property | `n[$key]` |
| `SET n:$label` | `SET n:$($label)` |
| `ZONED DATETIME >= date(...)` → 0 rows | Use `datetime(...)` or `.year` accessor |
| `FOREACH ... RETURN` | `UNWIND ... RETURN` |

Full trap table → [references/syntax-traps.md](references/syntax-traps.md)

---

## Output Mode and Write Gate

Default: parameterized queries.
```cypher
CYPHER 25 MATCH (n:Organization {name: $name}) RETURN n.name LIMIT 10
// parameters: {name: "Apple"}
```

**Validation workflow:**
1. `EXPLAIN` before any write — catches syntax errors, missing indexes
2. New read: test with `LIMIT 1` first
3. Write: verify read half as `RETURN` before replacing with `SET`/`CREATE`/`DELETE`
4. `PROFILE` to measure db hits; check for `AllNodesScan`, `CartesianProduct`, `Eager`

**Query API v2** (no driver needed — works for schema inspection, EXPLAIN, reads, writes):
```bash
curl -X POST https://<instance>.databases.neo4j.io/db/<database>/query/v2 \
  -u <user>:<password> -H "Content-Type: application/json" \
  -d '{"statement": "EXPLAIN MATCH (n:Person {name: $name}) RETURN n", "parameters": {"name": "Alice"}}'
# Local: http://localhost:7474/db/<database>/query/v2
# Response: {"data": {"fields": [...], "values": [...]}}  — prefix EXPLAIN to plan without executing
```

**Write execution gate** — only when agent executes (MCP/cypher-shell/HTTP), NOT when generating for code/scripts/user to run:
1. Run `EXPLAIN` → report estimated rows affected
2. Wait for user confirmation before executing

---

## Version Gates

Default to 2025.01-safe features when version unknown.

| Feature | Min version | Fallback |
|---|---|---|
| `CYPHER 25`, QPEs, `CALL (x) {}` | 2025.01 | require 2025+ |
| Match modes (`DIFFERENT RELATIONSHIPS`, `REPEATABLE ELEMENTS`) | 2025.01 | require 2025+ |
| Dynamic labels `$($expr)`, `coll.sort()` | 2025.01 | APOC or app-side |
| `CONCURRENT TRANSACTIONS`, `REPORT STATUS` | 2025.01 | drop / omit |
| `SEARCH` clause (vector/fulltext) | 2026.01 | `CALL db.index.vector.queryNodes(...)` |

---

## Performance

EXPLAIN/PROFILE red flags: `AllNodesScan` `CartesianProduct` `NodeByLabelScan` `Eager`

Fix Eager — collect first, then write:
```cypher
// BEFORE: triggers Eager (MERGE on same label as MATCH)
MATCH (u:User {status:'active'}) MERGE (u)-[:HAS_SESSION]->(s:Session {id:randomUUID()})

// AFTER:
CYPHER 25
MATCH (u:User {status:'active'}) WITH collect(u) AS users
UNWIND users AS u MERGE (u)-[:HAS_SESSION]->(s:Session {id:randomUUID()})
```

`CONTAINS`/`ENDS WITH` → needs TEXT index (range index doesn't support them).
Chained `OPTIONAL MATCH` for nested data → replace with `COLLECT { MATCH ... RETURN }`.

Full anti-patterns → [references/performance.md](references/performance.md)

---

## Failure Recovery

- 0 results: check param types, remove WHERE predicates one-by-one, EXPLAIN for index use
- TypeErrors: use `toIntegerOrNull()`/`toFloatOrNull()`; guard with `IS NOT NULL`
- Variable out of scope: not listed in `WITH` → use `count(*)` not `count(droppedVar)`
- Timeouts: fix AllNodesScan → add early `LIMIT` → `CALL IN TRANSACTIONS OF 1000 ROWS`
- DateTime mismatch: `ZONED DATETIME >= date(...)` → 0 rows; use `datetime()` or `.year`
- Duration: `.inDays`/`.inMonths` don't exist; use `.days`/`.months`
- `Cannot merge node using null property value`: MERGE key resolved to null — validate params first
- `IndexNotFoundError`: `SHOW INDEXES YIELD name, state WHERE state <> 'ONLINE'`

---

## References

Load on demand:
- [references/cypher-syntax.md](references/cypher-syntax.md) — full syntax reference: WITH, DELETE, ORDER BY, CASE, null, lists, strings, dates, LOAD CSV, subqueries, QPEs, dynamic labels, SEARCH; functions annotated with version introduced
- [references/syntax-traps.md](references/syntax-traps.md) — 40+ syntax trap table
- [references/performance.md](references/performance.md) — anti-patterns, text vs fulltext indexes, Eager, parallel runtime

## WebFetch

| Need | URL |
|---|---|
| Clause semantics | `https://neo4j.com/docs/cypher-manual/25/clauses/{clause}/` |
| Function signatures | `https://neo4j.com/docs/cypher-manual/25/functions/{type}/` |
| QPE / paths | `https://neo4j.com/docs/cypher-manual/25/patterns/` |
| Full cheat sheet | `https://neo4j.com/docs/cypher-cheat-sheet/25/all/` |

---

## Checklist
- [ ] Schema inspected or confirmed in context
- [ ] `CYPHER 25` prefix on every top-level query
- [ ] `$parameters` used (not literals)
- [ ] `LIMIT` on exploratory reads (default 25)
- [ ] `EXPLAIN` run; red flags resolved
- [ ] Write half verified as `RETURN` before executing
- [ ] Write execution gate applied if agent is executing (not generating)
- [ ] `MERGE` on constrained key only
- [ ] No label-free `MATCH (n)`
- [ ] Schema ops not inside explicit transaction
