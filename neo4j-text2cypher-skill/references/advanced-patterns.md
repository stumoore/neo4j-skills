# Advanced Cypher patterns a generator should prefer

Modern Cypher (late 5.x and 25) has several idioms that are both more readable *and* faster than the constructions an LLM tends to produce by default. Bias the prompt toward these — they replace old anti-patterns one-for-one.

## Subquery expressions: `COUNT { }`, `EXISTS { }`, `COLLECT { }`

These three replace the most common contortions in generated Cypher.

### `EXISTS { }` — for "has any"

Old way (works, but the generator often gets the scope wrong):

```cypher
MATCH (p:Person)
WHERE size([(p)-[:HAS_CEO]-(:Organization) | 1]) > 0
RETURN p
```

Modern:

```cypher
MATCH (p:Person)
WHERE EXISTS { (p)<-[:HAS_CEO]-(:Organization) }
RETURN p
```

- Outer variables are automatically in scope — no `WITH` plumbing.
- The planner can short-circuit on first match. Faster on selective predicates.
- Supports a full `MATCH … WHERE …` body, not just a pattern.

### `COUNT { }` — for "has more than N"

Old way:

```cypher
MATCH (p:Person)
OPTIONAL MATCH (p)-[:INVENTED]->(pat:Patent)
WITH p, count(pat) AS n
WHERE n > 5
RETURN p
```

Modern:

```cypher
MATCH (p:Person)
WHERE COUNT { (p)-[:INVENTED]->(:Patent) } > 5
RETURN p
```

The old form also introduces a row-per-person through the `OPTIONAL MATCH`, so memory grows with the people count. `COUNT { }` scopes to the row.

### `COLLECT { }` — for "list of related things" in `RETURN`

```cypher
MATCH (o:Organization {name:'Apple Inc.'})
RETURN o.name AS company,
       COLLECT { MATCH (o)-[:HAS_CEO]->(p) RETURN p.name } AS ceos,
       COLLECT { MATCH (o)-[:HAS_BOARD_MEMBER]->(p) RETURN p.name } AS board
```

- Each subquery is scoped to the outer row, so you don't get the Cartesian blow-up you'd see from two `OPTIONAL MATCH` + `collect()`.
- Often 3× faster than the OPTIONAL MATCH + collect form.
- The subquery's `RETURN` must produce exactly one column.

## `CALL { }` subqueries — when you need interleaved logic

For multi-step logic with variable piping, a `CALL { }` subquery is cleaner than a long `WITH` pipeline:

```cypher
MATCH (o:Organization)
CALL (o) {
  MATCH (o)-[:HAS_CEO]->(p:Person)
  RETURN p.name AS ceoName
}
RETURN o.name, ceoName LIMIT 10
```

Cypher 25's scoped-variable syntax `CALL (o) { … }` replaces the old `WITH o CALL { WITH o … }`. If you need batching, `CALL { … } IN TRANSACTIONS OF 10000 ROWS` lets you split one huge transaction into manageable chunks.

## Quantified path patterns (Cypher 25)

The new `(pattern){min,max}` replaces `-[:R*min..max]-` for anything non-trivial:

```cypher
// Old variable-length — only the relationship can be quantified
MATCH (a:Stop)-[:NEXT*1..3]->(b:Stop)
RETURN a, b

// Quantified path — can quantify a whole subpath with a predicate
MATCH (a:Stop) ((:Stop)-[r:NEXT WHERE r.isActive]->(:Stop)){1,3} (b:Stop)
RETURN a, b
```

Key differences:
- A quantified path can quantify **nodes + relationships + inline predicates**, not just a single rel.
- Inline `WHERE` inside the quantified block prunes during traversal, not after.
- GQL-conformant syntax.

Always set a bound (`{1,3}`, `{0,5}`). Unbounded `(…)+` on a dense graph is a runaway.

## `SHORTEST` path selectors

Cypher 25 exposes shortest-path variants cleanly:

```cypher
MATCH p = SHORTEST 1 (a:Organization {name:'Apple Inc.'})-[:HAS_CUSTOMER|HAS_SUPPLIER*]-(b:Organization {name:'Samsung'})
RETURN p

MATCH p = SHORTEST 3 GROUPS (a)-[*]-(b) RETURN p  // top 3 groups of equal-length paths
MATCH p = ALL SHORTEST (a)-[*]-(b) RETURN p       // every path sharing the minimum length
```

Prefer `SHORTEST k` over post-hoc `ORDER BY length(p) LIMIT k` — the planner uses a shortest-path algorithm (BFS-like) and stops early. The naïve version enumerates all paths first.

## Full-text search for name-ish filters

If the graph has a full-text index:

```cypher
CALL db.index.fulltext.queryNodes('orgFullText', $q) YIELD node, score
WHERE score > 1.5
RETURN node.name, score
ORDER BY score DESC LIMIT 10
```

`SHOW INDEXES` reveals which indexes exist. A generator should default to this for "companies called X" questions — it handles misspellings, word-order, and tokenization that `CONTAINS` / `=~` cannot.

## Vector search (Cypher 25)

```cypher
MATCH (m:Movie) SEARCH m.embedding NEAREST $query_vec LIMIT 10
RETURN m.title
```

Or the explicit index-procedure form (Cypher 5-compatible):

```cypher
CALL db.index.vector.queryNodes('movieEmbedding', 10, $query_vec) YIELD node, score
RETURN node.title, score
```

Pair the vector result with graph traversal in the same query — that's the "graph RAG" pattern:

```cypher
CALL db.index.vector.queryNodes('movieEmbedding', 10, $q) YIELD node AS m, score
MATCH (m)<-[:ACTED_IN]-(actor:Person)
RETURN m.title, score, collect(actor.name)[..5] AS cast
ORDER BY score DESC
```

## Graph Data Science (GDS)

When the question is about structure itself — centrality, communities, similarity — neither plain Cypher nor a fine-tuned text2cypher model will produce the right call. The generator should recognize these questions and route to a GDS procedure instead of writing it from scratch.

Common ones:
- `gds.pageRank.stream(graphName)` — importance
- `gds.louvain.stream(graphName)` — community detection
- `gds.nodeSimilarity.stream(graphName)` — "similar to X"
- `gds.shortestPath.dijkstra.stream(graphName, {...})` — weighted shortest path

Discover what's installed via the `list-gds-procedures` tool or `CALL gds.list()`. Remember the projection lifecycle: `gds.graph.project(...)` → run → `gds.graph.drop(...)` to free memory.

## Question → pattern cheat-sheet

| NL intent                                 | Pattern                                     |
|-------------------------------------------|---------------------------------------------|
| "does X have any Y"                       | `WHERE EXISTS { (x)-[:R]->(:Y) }`           |
| "how many Y does X have"                  | `RETURN COUNT { (x)-[:R]->(:Y) }`           |
| "list the Ys attached to each X"          | `RETURN x.name, COLLECT { MATCH (x)-[:R]->(y) RETURN y.name } AS ys` |
| "top N Xs by count of Y"                  | `MATCH (x)-[:R]->(:Y) WITH x, count(*) AS n ORDER BY n DESC LIMIT N` |
| "shortest connection between X and Y"     | `MATCH p = SHORTEST 1 (x)-[*]-(y)`          |
| "everything within k hops of X"           | `MATCH (x) ((:L)-[:R]-(:L)){1,k} (y)`       |
| "find by approximate name"                | `CALL db.index.fulltext.queryNodes(...)`    |
| "similar embedding to this text"          | `CALL db.index.vector.queryNodes(...)`      |
| "most central / most connected"           | `CALL gds.pageRank.stream(...)` (needs projection) |
| "communities / clusters"                  | `CALL gds.louvain.stream(...)`              |
| "symmetric predicate (competitor / peer)" | undirected `(a)-[:R]-(b)`                    |
| "count by category, one level only"       | `WHERE c.level = 1 WITH c, count(DISTINCT x) AS n` |

Feed this table to the generator via few-shot examples — each row becomes one positive example.

## References

- [Subqueries (overview)](https://neo4j.com/docs/cypher-manual/current/subqueries/)
- [COUNT subqueries](https://neo4j.com/docs/cypher-manual/current/subqueries/count/)
- [EXISTS subqueries](https://neo4j.com/docs/cypher-manual/current/subqueries/existential/)
- [COLLECT subqueries](https://neo4j.com/docs/cypher-manual/current/subqueries/collect/)
- [CALL subqueries + `IN TRANSACTIONS`](https://neo4j.com/docs/cypher-manual/current/subqueries/call-subquery/)
- [Quantified path patterns](https://neo4j.com/docs/cypher-manual/current/patterns/variable-length-patterns/)
- [Shortest paths](https://neo4j.com/docs/cypher-manual/current/patterns/shortest-paths/)
- [Full-text indexes](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/full-text-indexes/)
- [Vector indexes](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/)
- [Graph Data Science library](https://neo4j.com/docs/graph-data-science/current/)
- [Neo4j text2cypher guide (blog)](https://neo4j.com/blog/genai/text2cypher-guide/)
