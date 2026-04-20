# Text2Cypher gotchas — with verified before/after

Each gotcha below was reproduced on a real 76k-organization company/patent graph. The numbers in the examples are real; what changes between the "bad" and "good" query is the one thing an LLM routinely gets wrong.

---

## 1. Names are not unique

```cypher
// Bad: assumes one "Google"
MATCH (o:Organization {name: 'Google'}) RETURN o
// → returned 3 distinct Google entities
```

```cypher
// Good: use a unique identifier when you want one entity
MATCH (o:Organization {uri: 'http://diffbot.com/entity/EUFq-3WlpNsq0pvfUYWXOEA'})
RETURN o
```

**For disambiguation at prompt time**: first run a discovery query with `LIMIT 10` and a display key, then re-query by `uri`/`id`.

---

## 2. Relationship direction is rarely symmetric

```cypher
// Apple declaring competitors
MATCH (Apple:Organization {name:'Apple Inc.'})-[:HAS_COMPETITOR]->(c) RETURN count(c)  // 26

// Competitors declaring Apple
MATCH (Apple:Organization {name:'Apple Inc.'})<-[:HAS_COMPETITOR]-(c) RETURN count(c)  // 386
```

```cypher
// Good: undirected when the predicate is semantically symmetric
MATCH (a:Organization {name:'Apple Inc.'})-[:HAS_COMPETITOR]-(c) RETURN count(DISTINCT c)  // 412
```

The schema tells you *which* direction the edge is stored; it does **not** tell you whether the predicate's meaning is symmetric. Default to undirected `-[:REL]-` for predicates like `HAS_COMPETITOR`, `HAS_PARTNER`, `KNOWS`, `SIMILAR_TO`.

---

## 3. Equality against a list is silently empty

```cypher
// Bad: categories is LIST<STRING>
MATCH (t:Technology) WHERE t.categories = 'Programming Languages' RETURN t
// → 0 rows, no error
```

```cypher
// Good
MATCH (t:Technology) WHERE 'Programming Languages' IN t.categories RETURN t LIMIT 20
// or, case-insensitive:
MATCH (t:Technology)
WHERE any(c IN t.categories WHERE toLower(c) CONTAINS 'programming')
RETURN t LIMIT 20
```

Every `LIST<…>` property in the schema is a landmine for `=`. Flag them when building the prompt.

---

## 4. String vs date/datetime silently returns zero

```cypher
// Bad: a.date is DATE_TIME
MATCH (a:Article) WHERE a.date > '2024-01-01' RETURN count(a)  // 0
```

```cypher
// Good
MATCH (a:Article) WHERE a.date > datetime('2024-01-01') RETURN count(a)  // 4551
```

Cast to the property's actual type: `date(…)`, `datetime(…)`, `localdatetime(…)`, `duration(…)`. Under Cypher 5 a string-vs-datetime compare is non-erroring but always false; under Cypher 25 it's tightened.

---

## 5. `NOT x = true` drops NULLs

```cypher
// Bad: "companies that aren't public"
MATCH (o:Organization) WHERE NOT o.isPublic = true RETURN count(o)  // 6010
// Actual non-public set (null + false) is 72,467
```

```cypher
// Good
MATCH (o:Organization)
WHERE coalesce(o.isPublic, false) = false
RETURN count(o)  // 72467
```

Three-valued logic: `null <> true` is `null`, not `true`. Any Boolean negation needs a `coalesce()` or explicit `IS NULL OR`.

---

## 6. Aggregations skip NULLs — report coverage

```cypher
// Misleading
MATCH (o:Organization) RETURN avg(o.revenueValue)
// 356B — but only 7,904 of 76,102 orgs have revenueValue set
```

```cypher
// Good: always show coverage
MATCH (o:Organization)
RETURN avg(o.revenueValue)     AS avg,
       count(o.revenueValue)   AS withValue,
       count(*)                AS total
```

This catches aggregation-over-tiny-subset bugs immediately.

---

## 7. Units/currencies

```cypher
// Bad: mixes USD, EUR, INR, JPY, etc.
MATCH (o:Organization) WHERE o.revenueValue IS NOT NULL
RETURN o.name ORDER BY o.revenueValue DESC LIMIT 10
```

```cypher
// Good: constrain currency
MATCH (o:Organization)
WHERE o.revenueValue IS NOT NULL AND o.revenueCurrency = 'USD'
RETURN o.name, o.revenueValue ORDER BY o.revenueValue DESC LIMIT 10
```

When the user asks "biggest by revenue", the generator should ask which currency to normalize to — or pin USD and say so.

---

## 8. `allNames` / alias lists are noisy

```cypher
// Bad: matches Apple Music AND unrelated HSBC entities (Apple appeared in a Chinese blurb)
MATCH (o:Organization) WHERE 'Apple' IN o.allNames RETURN o.name LIMIT 10
```

```cypher
// Good: prefer canonical name for direct lookup
MATCH (o:Organization) WHERE o.name = 'Apple Inc.' RETURN o
// or use a full-text index over canonical-name-only
```

Alias fields typically contain translations and marketing copy. They're for display/discovery, not for filtering.

---

## 9. List-of-string "records"

```cypher
// yearlyRevenues = ["2024: 391035000000.0 USD", "2023: 383285000000.0 USD", ...]
```

```cypher
// Good: parse if you have to
MATCH (o:Organization {name:'Apple Inc.'})
UNWIND o.yearlyRevenues AS row
WITH split(row, ': ') AS parts
WITH parts[0] AS year, split(parts[1], ' ') AS rest
RETURN year AS y,
       toFloat(rest[0]) AS amount,
       rest[1]          AS currency
ORDER BY y DESC
```

When the schema shows a `LIST<STRING>` that looks tabular, document the shape for the LLM or surface a real relationship instead.

---

## 10. Hierarchies double-count

```cypher
// Bad
MATCH (o:Organization)-[:HAS_CATEGORY]->(c:IndustryCategory)
RETURN c.name, count(*) ORDER BY count(*) DESC
// Orgs attached to level-1, level-2, AND level-3 categories → triple counted overall
```

```cypher
// Good: pick the level you care about
MATCH (o:Organization)-[:HAS_CATEGORY]->(c:IndustryCategory {level: 1})
RETURN c.name, count(DISTINCT o) ORDER BY count(DISTINCT o) DESC LIMIT 10
```

When a property like `level`, `depth`, `rank`, `tier` exists, the generator must consume it.

---

## 11. Multi-hop paths explode

```cypher
// Bad: no LIMIT, no aggregation
MATCH (a:Organization {name:'Apple Inc.'})-[:HAS_CUSTOMER]->(b)-[:HAS_CUSTOMER]->(c)
RETURN a, b, c
// 686 paths from a single seed — at scale this becomes 6+ figures
```

```cypher
// Good: aggregate to what you actually want
MATCH (a:Organization {name:'Apple Inc.'})-[:HAS_CUSTOMER]->(b)-[:HAS_CUSTOMER]->(c)
RETURN c.name, count(DISTINCT b) AS via
ORDER BY via DESC LIMIT 10
```

For variable-length patterns (`-[:R*1..3]->`) put an upper bound and a `LIMIT`.

---

## 12. Relationships have properties

```cypher
// Bad: counts historical addresses too
MATCH (o:Organization)-[:IN_CITY]->(c:City {name:'San Francisco'})
RETURN count(DISTINCT o)
```

```cypher
// Good
MATCH (o:Organization)-[r:IN_CITY]->(c:City {name:'San Francisco'})
WHERE r.isCurrent = true
RETURN count(DISTINCT o)
```

Always pass rel-properties to the LLM. `apoc.meta.schema()` returns them; many schema extractors drop them.

---

## 13. `id()` is deprecated

```cypher
// Bad (deprecated since Neo4j 5, removed from Cypher 25 planner semantics)
MATCH (n) WHERE id(n) = 123 RETURN n
```

```cypher
// Good
MATCH (n) WHERE elementId(n) = '4:abc...' RETURN n
```

Old training data leans on `id()`. Patch prompts; reject generated Cypher that uses it.

---

## 14. Fuzzy match is not `=`

```cypher
// Bad: misses "Apple Inc.", "Apple Music", etc.
MATCH (o:Organization) WHERE o.name = 'Apple' RETURN o
```

```cypher
// Better: substring, case-insensitive
MATCH (o:Organization) WHERE toLower(o.name) CONTAINS 'apple' RETURN o LIMIT 20

// Best (if a fulltext index exists):
CALL db.index.fulltext.queryNodes('orgFullText', 'apple~') YIELD node, score
RETURN node.name, score LIMIT 20
```

Check `SHOW INDEXES` before the prompt; if there's a full-text index, tell the LLM to use it for name-ish filters.

---

## Bonus: three systemic smells to grep for

| Smell                                                     | Usually means                         | Fix                                       |
|-----------------------------------------------------------|---------------------------------------|-------------------------------------------|
| `= '\d{4}-\d{2}-\d{2}'` against date property             | #4, string-vs-date                    | wrap literal with `date()` / `datetime()` |
| `WHERE x IS NOT NULL AND NOT x`                           | #5, three-valued logic                | `coalesce(x, false) = false`              |
| single-directed edge on a symmetric predicate             | #2, directional asymmetry             | drop the arrow                            |
| aggregation without `count(prop)` sibling                 | #6, silent NULL skip                  | return both `count(*)` and `count(prop)`  |
| `t.listProp = 'value'` where schema says `LIST<…>`        | #3, list equality                     | `'value' IN t.listProp`                   |
| pattern with no `LIMIT` and no aggregating `RETURN`       | #11, cardinality blow-up              | add `LIMIT` or aggregate                  |

These six regexes running over generated Cypher will catch most silent-wrong-answer bugs before the query hits the database.
