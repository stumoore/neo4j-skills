> Source: git@github.com:neo4j/docs-cypher.git@238ab12a
> Files: subqueries/subqueries-in-transactions.adoc
> Curated: 2026-03-20

# Cypher 25 — CALL IN TRANSACTIONS Reference

For batch writes: bulk import, large deletes, batch updates. Executes subquery in separate inner transactions.
For read subqueries (`COUNT {}`, `COLLECT {}`, `EXISTS {}`, plain `CALL`), see `read/cypher25-subqueries.md`.

## Full syntax

```
CALL (vars) {
  subQuery
} IN [N CONCURRENT] TRANSACTIONS
  [OF batchSize ROW[S]]
  [ON ERROR {CONTINUE | BREAK | FAIL | RETRY [FOR duration SEC[S]] [THEN {CONTINUE | BREAK | FAIL}]}]
  [REPORT STATUS AS statusVar]
```

## Key constraints

- Only allowed in **implicit transactions** — not in explicit `BEGIN`/`COMMIT` blocks.
- Default batch size: **1000 rows**.
- **Batching applies to input rows fed outside the subquery** — match/produce data before `CALL`, not inside.
- Cancelling the outer transaction cancels pending inner ones; already-committed inner batches are **not rolled back**.
- `REPORT STATUS AS` is disallowed with `ON ERROR FAIL`.

## Common patterns

```cypher
-- Batch delete (recommended for large deletes)
MATCH (n:OldData)
CALL (n) {
  DETACH DELETE n
} IN TRANSACTIONS OF 10000 ROWS

-- CSV import with batching
LOAD CSV FROM 'file:///friends.csv' AS line
CALL (line) {
  CREATE (:Person {name: line[1], age: toInteger(line[2])})
} IN TRANSACTIONS OF 500 ROWS

-- Batch write with error handling and status reporting
LOAD CSV WITH HEADERS FROM 'file:///data.csv' AS row
CALL (row) {
  MERGE (:Person {id: row.id, name: row.name})
} IN TRANSACTIONS OF 500 ROWS
  ON ERROR CONTINUE
  REPORT STATUS AS s
WITH s WHERE s.errorMessage IS NOT NULL
RETURN s.transactionId, s.errorMessage

-- Concurrent batch import (parallel inner transactions)
LOAD CSV WITH HEADERS FROM 'file:///movies.csv' AS row
CALL (row) {
  MERGE (m:Movie {id: row.movieId})
} IN 4 CONCURRENT TRANSACTIONS OF 10 ROWS
  ON ERROR CONTINUE
  REPORT STATUS AS status
```

## ON ERROR options

| Option | Behavior | Outer tx result |
|---|---|---|
| `FAIL` (default) | Error in inner tx fails outer tx immediately | Fails |
| `CONTINUE` | Skip failed batch, continue with next batches | Succeeds |
| `BREAK` | Stop on first error, skip remaining batches | Succeeds |
| `RETRY FOR N SECS [THEN ...]` | Retry deadlocked tx for N seconds, then CONTINUE/BREAK/FAIL | Depends on THEN |

## REPORT STATUS fields

`statusVar` is a map with fields:
- `started` — BOOLEAN: inner tx was started
- `committed` — BOOLEAN: inner tx committed successfully
- `transactionId` — STRING: the transaction ID
- `errorMessage` — STRING?: error message if failed (null on success)

## Batching rules

- Batch size is an **upper limit** — a batch may be smaller if the target database changes (composite databases).
- For large datasets, prefer larger batches (e.g., 10000 ROWS) for performance.
- Filter/match data **before** the subquery; filtering inside collapses all work to one transaction.

```cypher
-- CORRECT: filtering before subquery enables batching
MATCH (n:Label) WHERE n.prop > 100
CALL (n) {
  DETACH DELETE n
} IN TRANSACTIONS OF 5000 ROWS

-- WRONG: filtering inside subquery = single transaction (no batching)
CALL () {
  MATCH (n:Label) WHERE n.prop > 100
  DETACH DELETE n
} IN TRANSACTIONS OF 5000 ROWS  -- batching has no effect here
```
