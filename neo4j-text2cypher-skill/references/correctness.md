# Correctness patterns — silent-wrong-answer bugs

These are the query-shape mistakes that do **not** raise an error but return the wrong rows. Each pattern was observed against a real Neo4j graph through `mcp-neo4j-cypher`; the examples below use schema-neutral labels (`:Person`, `:Movie`, `:Product`, `:Order`) so the lesson carries across graphs. If you only fix one class of text2cypher bugs, fix these.

For performance / plan issues see [performance.md](performance.md). For the modern Cypher idioms that replace old shapes see [advanced-patterns.md](advanced-patterns.md).

---

## 1. Display names are not unique

```cypher
// Bad: assumes one "Apple"
MATCH (c:Company {name: 'Apple'}) RETURN c
// may return multiple distinct companies sharing the display name
```

```cypher
// Good: use a unique identifier
MATCH (c:Company {uri: $uri}) RETURN c
// or, for id-style graphs:
MATCH (c:Company) WHERE elementId(c) = $eid RETURN c
```

For discovery, run a first query with a display-friendly `LIMIT`, then re-query by the unique key the user picks.

---

## 2. Relationship direction rarely matches semantic symmetry

The meaning of a predicate like "competitor of", "peer of", "sibling of" is symmetric, but the graph stores one direction per source. A single-direction pattern misses most of the data.

```cypher
// Bad: only edges outgoing from Apple
MATCH (a:Company {name:'Apple'})-[:COMPETES_WITH]->(c) RETURN count(c)
// e.g. 26
// Bad: only edges incoming
MATCH (a:Company {name:'Apple'})<-[:COMPETES_WITH]-(c) RETURN count(c)
// e.g. 386
```

```cypher
// Good: undirected for semantically symmetric predicates
MATCH (a:Company {name:'Apple'})-[:COMPETES_WITH]-(c) RETURN count(DISTINCT c)
```

The schema tells you **which** direction the rel is stored; it does **not** tell you whether the predicate is semantically symmetric. Default to undirected `-[:R]-` for `COMPETES_WITH`, `PARTNERS_WITH`, `KNOWS`, `SIMILAR_TO`, `CONNECTED_TO`, etc.

---

## 3. Equality against a list silently returns zero

```cypher
// Bad: categories is LIST<STRING>
MATCH (p:Product) WHERE p.categories = 'Electronics' RETURN p
// → 0 rows, no error
```

```cypher
// Good
MATCH (p:Product) WHERE 'Electronics' IN p.categories RETURN p LIMIT 20

// Case-insensitive substring match against any element:
MATCH (p:Product)
WHERE any(c IN p.categories WHERE toLower(c) CONTAINS 'electronic')
RETURN p LIMIT 20
```

Every `LIST<…>` property in `get_neo4j_schema` output is a landmine for `=`. Flag them when building the prompt.

---

## 4. String compared to `DATE` / `DATE_TIME` silently returns zero

```cypher
// Bad: a.publishedAt is DATE_TIME
MATCH (a:Article) WHERE a.publishedAt > '2024-01-01' RETURN count(a)
// → 0 (silently), the compare is either always false or errors depending on version
```

```cypher
// Good
MATCH (a:Article) WHERE a.publishedAt > datetime('2024-01-01') RETURN count(a)
```

Always cast the literal to match the property's type: `date(…)`, `datetime(…)`, `localdatetime(…)`, `localtime(…)`, `duration(…)`. Under Cypher 5 the compare silently returns false; under Cypher 25 it's tightened and tends to error — either way the original query is wrong.

---

## 5. `NOT x = true` drops NULLs

Three-valued logic means `null <> true` evaluates to `null`, which does not satisfy a `WHERE` predicate. "Users who are not admins" expressed as `NOT u.isAdmin = true` misses everyone where `isAdmin` is not set.

```cypher
// Bad
MATCH (u:User) WHERE NOT u.isAdmin = true RETURN count(u)
// misses rows where isAdmin IS NULL
```

```cypher
// Good
MATCH (u:User) WHERE coalesce(u.isAdmin, false) = false RETURN count(u)
// or
MATCH (u:User) WHERE u.isAdmin IS NULL OR u.isAdmin = false RETURN count(u)
```

Any Boolean negation on an optional property needs a `coalesce()` or explicit `IS NULL OR` — this is one of the most common silent bugs.

---

## 6. Aggregations skip NULLs — report coverage

```cypher
// Misleading: averages only over rows where the property is set
MATCH (p:Product) RETURN avg(p.price)
```

```cypher
// Good: surface coverage next to the aggregate
MATCH (p:Product)
RETURN avg(p.price)     AS avgPrice,
       count(p.price)   AS withPrice,
       count(*)         AS total
```

If `withPrice` is 10% of `total`, the single-number `avgPrice` is misleading. A text2cypher generator should always return both.

---

## 7. Units, currencies, time zones are not normalized

A field called `price` may mix USD/EUR/JPY; a `duration` may mix seconds and milliseconds; timestamps may be local or UTC. Aggregating without grouping by the unit-bearing companion property is wrong.

```cypher
// Bad: mixes currencies
MATCH (p:Product) RETURN sum(p.price)

// Good: group by currency, or filter
MATCH (p:Product) WHERE p.currency = 'USD' RETURN sum(p.price)
// or
MATCH (p:Product) RETURN p.currency, sum(p.price) AS total
```

Detect unit-bearing pairs at schema-inspection time: if a numeric property sits next to a string property named `*Currency`, `*Unit`, `*Tz`, surface them together in the LLM prompt.

---

## 8. Alias / translation lists are noisy

A list property intended for display aliases (`allNames`, `aliases`, multilingual names) contains translations, marketing copy, and unrelated multilingual tokens. Filtering against it produces false positives.

```cypher
// Bad: may match unrelated entities whose alias list happens to contain "Apple"
MATCH (c:Company) WHERE 'Apple' IN c.aliases RETURN c
```

```cypher
// Good: prefer canonical properties for filters
MATCH (c:Company) WHERE c.name = 'Apple' RETURN c

// Or use a full-text index scoped to canonical name
CALL db.index.fulltext.queryNodes('companyFulltext', 'Apple') YIELD node, score
RETURN node.name, score ORDER BY score DESC LIMIT 10
```

Alias fields are for display / discovery — not predicates.

---

## 9. List-of-string "records" need parsing, not aggregation

Some graphs encode tabular data in list-of-strings (e.g. `yearlyRevenue: ["2024: 391B USD", "2023: 383B USD", ...]`). They look queryable but are not aggregate-friendly.

```cypher
// Parse before aggregating
MATCH (c:Company {name:'Apple'})
UNWIND c.yearlyRevenue AS row
WITH split(row, ': ') AS parts
WITH parts[0] AS year, split(parts[1], ' ') AS rest
RETURN year, toFloat(rest[0]) AS amount, rest[1] AS currency
ORDER BY year DESC
```

Better: model these as first-class relationships (`(:Company)-[:REPORTED]->(:YearlyRevenue {year, amount, currency})`). Flag these patterns to the LLM at schema-inspection time.

---

## 10. Hierarchies double-count

Trees and tag hierarchies often attach an entity to every ancestor level. Ignoring the `level` / `depth` / `tier` property double- or triple-counts.

```cypher
// Bad: double-counts when products are attached to both level-1 and level-2 categories
MATCH (p:Product)-[:IN_CATEGORY]->(c:Category)
RETURN c.name, count(*) ORDER BY count(*) DESC
```

```cypher
// Good: pick the level you care about
MATCH (p:Product)-[:IN_CATEGORY]->(c:Category {level: 1})
RETURN c.name, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 10
```

Any `level`-like numeric property on a node type in the schema means the generator must consume it.

---

## 11. Multi-hop patterns explode

Multi-hop and variable-length patterns multiply cardinality. Three hops on a moderately dense graph easily produce six-figure path counts.

```cypher
// Bad: no LIMIT, path-level return
MATCH (a:Person {name:$name})-[:FOLLOWS]->(b)-[:FOLLOWS]->(c)
RETURN a, b, c
```

```cypher
// Good: aggregate to what you actually want
MATCH (a:Person {name:$name})-[:FOLLOWS]->(b)-[:FOLLOWS]->(c)
RETURN c.name, count(DISTINCT b) AS via
ORDER BY via DESC LIMIT 10
```

For variable-length (`-[:R*1..3]->`) or quantified paths, always put an upper bound and a `LIMIT`.

---

## 12. Relationships carry properties — filter on them

Many rel-types hold status flags (`isCurrent`, `isActive`, `endedAt`). Ignoring them counts stale / historical rows as if they were current.

```cypher
// Bad: counts historical employment too
MATCH (p:Person)-[:WORKS_AT]->(c:Company {name:$name})
RETURN count(DISTINCT p)
```

```cypher
// Good
MATCH (p:Person)-[r:WORKS_AT]->(c:Company {name:$name})
WHERE r.isCurrent = true
RETURN count(DISTINCT p)
```

`get_neo4j_schema` returns rel-properties — make sure they reach the LLM prompt. Many schema extractors drop them.

---

## 13. `id()` is deprecated

```cypher
// Bad — deprecated since Neo4j 5
MATCH (n) WHERE id(n) = 123 RETURN n
```

```cypher
// Good
MATCH (n) WHERE elementId(n) = $eid RETURN n
```

Old training data leans on `id()`. Patch prompts and reject generated Cypher that uses it. Internal IDs are also not stable across database restarts in Aura / large graphs — prefer application-level unique keys (`uri`, `externalId`).

---

## 14. Fuzzy match is not `=`

```cypher
// Misses "Apple Inc.", "Apple Music", etc.
MATCH (c:Company) WHERE c.name = 'Apple' RETURN c
```

```cypher
// Better: substring, case-insensitive (needs a text index to be fast)
MATCH (c:Company) WHERE toLower(c.name) CONTAINS 'apple' RETURN c LIMIT 20

// Best, if a fulltext index exists:
CALL db.index.fulltext.queryNodes('companyFulltext', 'apple~') YIELD node, score
RETURN node.name, score ORDER BY score DESC LIMIT 20
```

`SHOW INDEXES` (via `read_neo4j_cypher`) lists what's indexed and in which mode (range / text / fulltext / vector). Feed the list to the LLM so it prefers the right lookup pattern.

---

## Six smells to grep for in generated Cypher

| Smell                                                     | Usually means                         | Fix                                       |
|-----------------------------------------------------------|---------------------------------------|-------------------------------------------|
| `= '\d{4}-\d{2}-\d{2}'` against a date property           | #4, string-vs-date                    | wrap literal with `date()` / `datetime()` |
| `WHERE … AND NOT x` with nullable `x`                     | #5, three-valued logic                | `coalesce(x, false) = false`              |
| single-directed edge on a symmetric predicate             | #2, directional asymmetry             | drop the arrow                            |
| aggregation without a `count(prop)` sibling               | #6, silent NULL skip                  | return both `count(*)` and `count(prop)`  |
| `t.listProp = 'value'` where schema says `LIST<…>`        | #3, list equality                     | `'value' IN t.listProp`                   |
| pattern with no `LIMIT` and no aggregating `RETURN`       | #11, cardinality blow-up              | add `LIMIT` or aggregate                  |

Running these six checks before calling `read_neo4j_cypher` catches most silent-wrong-answer bugs before the query hits the database.
