# Performance patterns for generated Cypher

Correctness mistakes return wrong answers; performance mistakes hang the database. LLM-generated Cypher tends to be shape-correct but plan-hostile. These are the patterns that matter in practice.

The rule underneath all of them: **filter early, project late, let the index do the work**.

## Validate plans with `EXPLAIN`, not `PROFILE`

- `EXPLAIN <query>` — compile only, produces the plan, never hits the data. **Use this for every generated query before executing.**
- `PROFILE <query>` — executes the query and annotates the plan with actual row counts. Use for tuning, not validation. A text2cypher review loop should use `EXPLAIN`.

A generator that loops over `EXPLAIN` → feed errors back → regenerate catches roughly all syntactic issues in one or two retries.

## Six things to look for in the plan

| Operator in plan                  | Means                                              | Fix                                                                     |
|-----------------------------------|----------------------------------------------------|-------------------------------------------------------------------------|
| `AllNodesScan`                    | Reading every node; no label/index                 | Add a label on the `MATCH`; create an index on the filter property       |
| `NodeByLabelScan` on a huge label | Scanning all `:Organization` then filtering        | Create an index on the property you filter by; use `WHERE prop = $p`    |
| `CartesianProduct`                | Two disconnected `MATCH`es being cross-joined      | Connect patterns, or pull one into a `CALL { }` subquery                |
| `Eager`                           | Whole intermediate result buffered in memory       | Split read/write phases; avoid writes that re-read what you just wrote  |
| `Expand(All)` on a super-node     | Traversing a node with 100k+ relationships         | Move the filter onto the relationship/neighbor; add a rel-type index    |
| `Filter` right before `Produce`   | Filter applied too late                            | Move the predicate into the `MATCH`'s inline map or onto an earlier `WHERE` |

## Top eight authoring rules

1. **Always put a label on every node pattern.** `MATCH (n)` without a label is a full graph scan.
2. **Filter with indexed properties.** Check `SHOW INDEXES` before generating. If the LLM is picking a non-indexed property for the anchor, nudge it.
3. **Use parameters, not literals, for filter values.** `WHERE o.name = $name` caches the plan; `WHERE o.name = 'Apple'` forces a replan on every distinct value.
4. **Cap variable-length patterns.** `(a)-[:R*1..5]->(b)` not `(a)-[:R*]->(b)`. Unbounded patterns on moderately dense graphs exhaust memory.
5. **Project properties, not nodes.** `RETURN o.name, o.revenueValue` beats `RETURN o` — the server ships less over the wire and avoids touching cold properties.
6. **Aggregate before collecting.** `MATCH (o)-[:HAS_CATEGORY]->(c) WITH c, count(o) AS n ORDER BY n DESC LIMIT 10` — aggregate early so `ORDER BY`/`LIMIT` operates on small rows.
7. **`LIMIT` every exploratory query.** An LLM asked for "companies in SF" should get `LIMIT 100` even if the user didn't ask. If they want more, they'll say so.
8. **Prefer `COUNT { }` / `EXISTS { }` over `size([… | …])`.** See [advanced-patterns.md](advanced-patterns.md).

## Super-node traversal

When a small number of nodes concentrate most of the graph's edges (e.g. "United States" `Country` or a common `Technology` like "JavaScript"), the planner's naive `Expand(All)` is what kills performance. Two techniques:

```cypher
// Bad — expands all orgs in the US then filters
MATCH (c:Country {name:'United States'})<-[:IN_COUNTRY]-(city:City)<-[:IN_CITY]-(o:Organization)
WHERE o.isPublic = true
RETURN o.name LIMIT 50
```

```cypher
// Good — anchor on the filter first, join to the super-node last
MATCH (o:Organization)-[:IN_CITY]->(city:City)-[:IN_COUNTRY]->(c:Country {name:'United States'})
WHERE o.isPublic = true
RETURN o.name LIMIT 50
```

The planner reads the `MATCH` left-to-right when choosing the starting operator; put the selective filter at the left end.

## Writes — separate the phases

Read-then-write in one pipeline triggers the `Eager` operator, buffering the whole read before any write, because Cypher must protect against writes affecting still-in-flight reads. Symptom: a query that's fast as a read becomes 50× slower when you add `SET`.

```cypher
// Triggers Eager on most versions
MATCH (o:Organization) WHERE o.revenueValue > 1e9 SET o:BigCo
```

Two mitigations:

- Use `CALL { ... } IN TRANSACTIONS OF 10000 ROWS` for big batch updates — each batch is a small, disposable transaction.
- Collect ids first, then update in a second query (or second `CALL { }` block). This keeps each phase tight.

## Bulk writes — one round-trip, `UNWIND` a list

```cypher
UNWIND $rows AS row
MERGE (p:Person {id: row.id})
SET p += row
```

Single transaction, single network round-trip, server loops in-process. 10k `MERGE` this way takes under a second; 10k driver calls takes minutes.

## `MERGE` vs `CREATE`

`MERGE` is match-then-create — two operations. If you know the row is new, use `CREATE` and halve the work. If you don't, make sure the `MERGE` key has a **constraint or index** — otherwise `MERGE` scans the whole label set on every call.

## Indexes a text2cypher generator should create

For any graph that a generator will query:

1. **Unique constraint + index on `uri` / `id`** for every entity label — enables fast by-id lookup.
2. **Range/text index on the display-name property** (`name`, `title`, `fullName`) — the most-asked filter.
3. **Full-text index across the alias fields** (`allNames`, `aliases`) — so the generator can emit `db.index.fulltext.queryNodes('alias_ft', $q)` instead of scanning `WHERE any(n IN o.allNames …)`.
4. **Range index on date/datetime properties used for filtering** (`foundingDate`, `filingDate`) — turns date-range queries from scans into seeks.
5. **(Cypher 25)** Vector index on any embedding property used for semantic search.

`SHOW INDEXES` should be the first thing the generator reads after the schema.

## References

- [Query tuning (official)](https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/query-tuning/)
- [Impact of indexes](https://neo4j.com/docs/cypher-manual/current/indexes/search-performance-indexes/using-indexes/)
- [Advanced tuning tutorial](https://neo4j.com/docs/cypher-manual/current/appendix/tutorials/advanced-query-tuning/)
- [Improving Cypher performance — Aura](https://neo4j.com/docs/aura/tutorials/performance-improvements/)
- [Execution plans reference](https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/)
