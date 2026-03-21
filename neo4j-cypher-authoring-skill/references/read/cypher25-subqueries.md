> Source: git@github.com:neo4j/docs-cypher.git@238ab12a
> Files: subqueries/call-subquery.adoc, subqueries/count.adoc, subqueries/collect.adoc, subqueries/existential.adoc
> Curated: 2026-03-20

# Cypher 25 — Read Subqueries Reference

Covers: `CALL` subqueries (read), `COUNT {}`, `COLLECT {}`, `EXISTS {}`.
For bulk-write subqueries (`CALL IN TRANSACTIONS`), see `write/cypher25-call-in-transactions.md`.

## Subquery forms at a glance

| Form | Used in | Returns | Outer vars auto-imported? |
|---|---|---|---|
| `CALL (vars) { ... }` | Standalone clause | Multiple columns, multiple rows | No — must declare in `()` |
| `COUNT { ... }` | Expression (WHERE, RETURN, etc.) | INTEGER | Yes |
| `COLLECT { ... RETURN x }` | Expression | LIST | Yes |
| `EXISTS { ... }` | Predicate expression | BOOLEAN | Yes |

`COUNT {}` vs `count()`: `COUNT { pattern }` counts **rows** from a subquery; `count(expr)` is an aggregating function over the current row stream — not interchangeable.

---

## CALL subqueries

### Scope (variable import) — Cypher 25

Variables from the outer scope **must be explicitly imported** via a scope clause:

```cypher
MATCH (t:Team)
CALL (t) {
  MATCH (p:Player)-[:PLAYS_FOR]->(t)
  RETURN collect(p) AS players
}
RETURN t, players
```

Scope clause variants:
- `CALL (x, y)` — import specific variables
- `CALL (*)` — import all outer variables
- `CALL ()` — import nothing (isolated subquery)

**Rules:**
- Imported vars are globally visible inside the subquery; a subsequent `WITH` cannot delist them.
- Variable names cannot be aliased in the scope clause (`CALL (x AS y)` is invalid).
- Subquery cannot return a name already used in outer scope — rename it.
- `CALL` subqueries **without** a scope clause are **deprecated**.

### Deprecated importing WITH (do not use)

```cypher
-- DEPRECATED
CALL {
  WITH x        -- importing WITH, must be first clause
  MATCH (n:Label {id: x})
  RETURN n
}
```

Restrictions: cannot follow `WITH` with `DISTINCT`, `ORDER BY`, `WHERE`, `SKIP`, `LIMIT`.

### Execution semantics

- Executes **once per incoming row**; each execution can observe changes from previous executions.
- Variables returned by the subquery are added to the outer row.
- Memory benefit: intermediate data structures released after each row's execution.

### OPTIONAL CALL

```cypher
MATCH (p:Player)
OPTIONAL CALL (p) {
  MATCH (p)-[:PLAYS_FOR]->(t:Team)
  RETURN t
}
RETURN p, t  -- t is null if no team found
```

Behaves like `OPTIONAL MATCH` — null-pads missing rows instead of dropping them.

---

## COUNT subquery

```cypher
-- In WHERE
MATCH (person:Person)
WHERE COUNT { (person)-[:HAS_DOG]->(:Dog) } > 1
RETURN person.name

-- With WHERE inside subquery
MATCH (person:Person)
WHERE COUNT {
  (person)-[:HAS_DOG]->(dog:Dog)
  WHERE person.name = dog.name
} = 1
RETURN person.name

-- In RETURN
MATCH (p:Person)
RETURN p.name, COUNT { (p)-[:HAS_DOG]->() } AS dogCount
```

- Outer-scope variables **automatically in scope** — no import needed.
- Returns `INTEGER` — use in numeric comparisons or as a RETURN expression.
- Pattern-only form: `COUNT { (a)-[:R]->(b) }` (no MATCH keyword needed for simple patterns).
- Full Cypher form: `COUNT { MATCH (a)-[:R]->(b) WHERE ... RETURN a }` — `RETURN` is optional.

---

## COLLECT subquery

```cypher
-- In WHERE (membership test)
MATCH (person:Person)
WHERE 'Ozzy' IN COLLECT { MATCH (person)-[:HAS_DOG]->(d:Dog) RETURN d.name }
RETURN person.name

-- In SET / RETURN
MATCH (person:Person)
SET person.dogNames = COLLECT { MATCH (person)-[:HAS_DOG]->(d:Dog) RETURN d.name }

-- With WHERE inside
MATCH (person:Person)
RETURN person.name, COLLECT {
  MATCH (person)-[r:HAS_DOG]->(d:Dog)
  WHERE r.since > 2017
  RETURN d.name
} AS recentDogs
```

- `RETURN` clause is **mandatory** and must return **exactly one column**.
- Outer-scope variables automatically in scope.
- Returns `LIST` — use anywhere a list is expected.

---

## EXISTS subquery

```cypher
MATCH (person:Person)
WHERE EXISTS {
  MATCH (person)-[:HAS_DOG]->(dog:Dog)
  WHERE person.name = dog.name
}
RETURN person.name
```

- Outer-scope variables automatically in scope.
- Returns `BOOLEAN` — use only as a predicate.
- Pattern-only form: `EXISTS { (a)-[:R]->(b) }` for simple patterns.
- Short-circuits on first match (efficient).

---

## Scope summary

| Subquery | Outer vars | Import syntax |
|---|---|---|
| `CALL` | Not auto-imported | `CALL (x, y)` required |
| `COUNT { }` | Auto-imported | None |
| `COLLECT { }` | Auto-imported | None |
| `EXISTS { }` | Auto-imported | None |
