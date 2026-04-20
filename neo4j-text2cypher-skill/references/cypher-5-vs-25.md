# Cypher 5 vs Cypher 25 — what a generator needs to know

Since Neo4j 2025.06, Cypher is versioned independently of the server. Two languages coexist:

- **Cypher 5** — frozen. Bug fixes and perf only.
- **Cypher 25** — evolving. All new features land here (vector type, dynamic labels, conditional subqueries, `coll.*` functions, walk semantics, GQL syntax).

From Neo4j 2026.02 Cypher 25 is the default for new databases. Existing databases upgraded from earlier versions stay on Cypher 5 until `ALTER DATABASE … SET DEFAULT LANGUAGE CYPHER 25`.

## Selecting a version

```cypher
CYPHER 25
MATCH (p:Person {name: $name}) RETURN p
```

Always emit the prefix in generated queries — same query, same result, on any database.

Check a database's default:

```cypher
SHOW DATABASES YIELD name, defaultLanguage
```

## What changes for generated queries

### Safe on both

Anything in a basic `MATCH … WHERE … RETURN` pipeline with built-in functions (`toLower`, `count`, `collect`, `coalesce`, `size`, `split`, `datetime`, …). A text2cypher generator can ignore versioning if it sticks to this core.

### Broken under Cypher 25 (emit Cypher 5 if unavoidable)

1. `SET n = r` where `r` is a node/rel. → `SET n = properties(r)`
2. `MERGE (a {foo:1})-[:T]->(b {foo: a.foo})` (cross-entity reference). → split into two `MERGE`s.
3. `USE composite.` + backticked sub-graph name. → backtick the whole thing: `` USE `composite.sub1` ``.
4. `CREATE INDEX … OPTIONS {indexProvider:'…'}` — drop the option.
5. Calls to `db.create.setVectorProperty`, `db.index.vector.createNodeIndex`, `dbms.upgrade`, `dbms.quarantineDatabase` — removed.
6. `id(n)` — deprecated in both, effectively gone in Cypher 25 semantics. Use `elementId(n)`.

### Only works under Cypher 25

If your generator wants to produce these, the target DB must be on Cypher 25:

- **Dynamic labels / rel types / property keys**: `MATCH (n:$($label) {$($key): $value})`, `MERGE ()-[:$($type)]->()`. No more APOC for this.
- **Vector type**: `vector([0.1, 0.2, 0.3], 3, FLOAT32)`, `vector_distance()`, `vector_norm()`, `vector_dimension_count()`.
- **Vector search in `MATCH`**: `MATCH (m:Movie) SEARCH m.embedding NEAREST $q LIMIT 10`.
- **Conditional update subqueries**: `CALL { WHEN cond THEN … ELSE … }`.
- **Collection namespace**: `coll.sort`, `coll.distinct`, `coll.flatten`, `coll.max`, `coll.min`, `coll.indexOf`, `coll.insert`, `coll.remove`.
- **GQL-style composition**: `LET`, `NEXT`, `FILTER`, `RETURN ALL`.
- **Walk semantics**: `MATCH REPEATABLE ELEMENTS …` (allows revisiting relationships).
- **Temporal formatting**: `format(datetime(), 'yyyy-MM-dd')`.
- **Read→write without `WITH`**: `MATCH (p:Person) CREATE (p)-[:OWNS]->(:Pet)` directly.
- **Numeric-leading parameter names**: `$0user`.
- **New constraint kinds**: `NODE_LABEL_EXISTENCE`, `RELATIONSHIP_SOURCE_LABEL`, `RELATIONSHIP_TARGET_LABEL`.

## Cheat sheet for a generator's system prompt

```
Target Cypher version: 25          # or 5
Emit `CYPHER 25` as the first token of every query.
Use `elementId(n)`, never `id(n)`.
For dynamic labels, use `n:$(...)` — never string-concatenate labels.
Wrap date/datetime literals with `date()` / `datetime()`.
Use `coll.sort`, `coll.distinct` for list ops (Cypher 25 only).
```

Drop the "Cypher 25 only" items from the prompt if the target is 5.

## References

- [Cypher version selection](https://neo4j.com/docs/cypher-manual/current/queries/select-version/)
- [Cypher additions, deprecations, removals](https://neo4j.com/docs/cypher-manual/current/deprecations-additions-removals-compatibility/)
- [Cypher versioning (blog)](https://neo4j.com/blog/developer/cypher-versioning/)
- [Cypher 25 cheat sheet](https://neo4j.com/docs/cypher-cheat-sheet/25/all/)
