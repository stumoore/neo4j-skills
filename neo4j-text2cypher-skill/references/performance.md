# Performance patterns for generated Cypher

Correctness mistakes return wrong answers; performance mistakes hit the MCP server's **30-second read timeout** or get silently truncated by its **response token limit**. LLM-generated Cypher tends to be shape-correct but plan-hostile. The rule underneath everything here: **filter early, project late, let the index do the work**.

## MCP-specific constraints you must plan around

- `NEO4J_READ_TIMEOUT` — default **30 s**. Any `read_neo4j_cypher` call that exceeds it is cancelled. Plan for this: bound every variable-length pattern, always `LIMIT`, never materialize whole result sets.
- `NEO4J_RESPONSE_TOKEN_LIMIT` — when set, large results are **silently truncated** by tiktoken. A query that logically returns 10k rows may surface as a truncated prefix with no error. Prefer projections (`RETURN n.name, n.value`) over whole-node returns, and paginate with `SKIP` / `LIMIT` for large scans.
- `NEO4J_SCHEMA_SAMPLE_SIZE` — default **1000**. Rare properties on long-tail nodes may be missing from `get_neo4j_schema`. If the LLM filters on a property the schema doesn't mention, fall back to `CALL db.schema.nodeTypeProperties()` to confirm.
- In read-only mode (`NEO4J_READ_ONLY=true`) the generator **cannot create indexes** on the fly — it must work with what `SHOW INDEXES` already lists.

## Top eight authoring rules

1. **Always put a label on every node pattern.** `MATCH (n)` without a label is a full graph scan.
2. **Filter with indexed properties.** Check `SHOW INDEXES` before generating. If the LLM is picking a non-indexed property for the anchor, nudge it.
3. **Use parameters, not literals, for filter values.** `WHERE c.name = $name` caches the plan; `WHERE c.name = 'Apple'` forces a replan on every distinct value.
4. **Cap variable-length patterns.** `(a)-[:R*1..5]->(b)` not `(a)-[:R*]->(b)`. Unbounded patterns on moderately dense graphs exhaust memory or timeout.
5. **Project properties, not nodes.** `RETURN c.name, c.price` beats `RETURN c` — smaller rows, fewer cold reads, less risk of response-token truncation.
6. **Aggregate before collecting.** `MATCH (c)-[:IN_CATEGORY]->(cat) WITH cat, count(c) AS n ORDER BY n DESC LIMIT 10` — aggregate early so `ORDER BY` / `LIMIT` runs on small rows.
7. **`LIMIT` every exploratory query.** If the user asks for "users in Berlin", emit `LIMIT 100` even if they didn't. If they want more, they'll say so.
8. **Prefer `COUNT { }` / `EXISTS { }` over `size([… | …])`.** See [advanced-patterns.md](advanced-patterns.md).

## Super-node traversal

When a small number of nodes concentrate most of the graph's edges (popular countries, common tags, the world's busiest airport), naive traversal from the super-node is what kills performance.

```cypher
// Bad — expands all products attached to the super-node, then filters
MATCH (cat:Category {name:'Electronics'})<-[:IN_CATEGORY]-(p:Product)
WHERE p.inStock = true
RETURN p.name LIMIT 50
```

```cypher
// Good — anchor on the selective filter first, join to the super-node at the end
MATCH (p:Product) WHERE p.inStock = true
MATCH (p)-[:IN_CATEGORY]->(cat:Category {name:'Electronics'})
RETURN p.name LIMIT 50
```

The planner reads the `MATCH` left-to-right when choosing the starting point; put the selective filter at the left.

## Writes — separate the phases

Reading and writing in the same pipeline forces Cypher to buffer the whole read set before any write (to protect against self-feedback). A query that's fast as a read becomes much slower when you add `SET`.

```cypher
// Slow on large label sets — whole read materialized before any write
MATCH (p:Product) WHERE p.price > 1000 SET p:Premium
```

Two mitigations:

- **Batch**: `CALL { … } IN TRANSACTIONS OF 10000 ROWS` breaks the update into small disposable transactions and avoids the buffer.
- **Two-phase**: collect ids first, then update in a separate `write_neo4j_cypher` call driven by the id list.

## Bulk writes — one round-trip via `UNWIND`

```cypher
UNWIND $rows AS row
MERGE (p:Person {id: row.id})
SET p += row
```

Pass the list through the MCP call's `params`, not interpolated into the query text. 10k `MERGE` this way takes under a second; 10k separate `write_neo4j_cypher` calls take minutes.

## `MERGE` vs `CREATE`

`MERGE` is match-then-create — two operations. If you know the row is new, use `CREATE` and halve the work. If you don't, make sure the `MERGE` key has a **constraint or index** — otherwise `MERGE` scans the whole label set on every call.

## Indexes a text2cypher generator should expect / create

For any graph a generator will query:

1. **Unique constraint + index on the stable identifier** (`uri`, `externalId`, `sku`) for every entity label — enables fast by-id lookup and safe `MERGE`.
2. **Range / text index on the display-name property** (`name`, `title`, `fullName`) — the most-asked filter.
3. **Full-text index across alias / multilingual fields** — so the generator can emit `db.index.fulltext.queryNodes(name, $q)` instead of scanning `WHERE any(x IN c.aliases …)`.
4. **Range index on every date / datetime property used in filters** — turns date-range queries from scans into seeks.
5. **(Cypher 25)** Vector index on any embedding property used for semantic search.

`SHOW INDEXES` should be the first `read_neo4j_cypher` call after `get_neo4j_schema`.

## References

- [Query tuning (official)](https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/query-tuning/)
- [Impact of indexes](https://neo4j.com/docs/cypher-manual/current/indexes/search-performance-indexes/using-indexes/)
- [Advanced tuning tutorial](https://neo4j.com/docs/cypher-manual/current/appendix/tutorials/advanced-query-tuning/)
- [Improving Cypher performance — Aura](https://neo4j.com/docs/aura/tutorials/performance-improvements/)
