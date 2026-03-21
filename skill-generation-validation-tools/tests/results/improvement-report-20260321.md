# Neo4j Cypher Authoring Skill — Harness Improvement Report

**Generated**: 2026-03-21T13:22:42Z  
**Input files**: 3  
  - `companies-run-20260321-141045.json`
  - `recommendations-run-20260321-141051.json`
  - `ucfraud-run-20260321-141057.json`

## 1. Overall Summary

| Metric | Count |
|--------|------:|
| Total cases (deduplicated) | 89 |
| PASS | 63 |
| WARN | 0 |
| FAIL | 26 |
| Overall pass rate | 70.8% |

## 2. Per-Difficulty Pass Rate vs PRD Targets

| Difficulty | Total | PASS | WARN | FAIL | Actual | Target | Delta |
|------------|------:|-----:|-----:|-----:|-------:|-------:|------:|
| Basic | 22 | 16 | 0 | 6 | 72.7% | 90% | -17.3% |
| Intermediate | 22 | 19 | 0 | 3 | 86.4% | 80% | +6.4% |
| Advanced | 22 | 15 | 0 | 7 | 68.2% | 70% | -1.8% |
| Complex | 13 | 8 | 0 | 5 | 61.5% | 60% | +1.5% |
| Expert | 10 | 5 | 0 | 5 | 50.0% | 60% | -10.0% |

## 3. Per-Gate Failure Breakdown

| Gate | Description | FAIL | WARN | Total Non-PASS |
|-----:|-------------|-----:|-----:|---------------:|
| 1 | Syntax (EXPLAIN) | 4 | 0 | 4 |
| 2 | Correctness (row count / execution) | 22 | 0 | 22 |

### Non-PASS Cases Detail

| ID | Difficulty | Verdict | Gate | Tags | Reason |
|----|------------|---------|-----:|------|--------|
| `companies-basic-006` | basic | FAIL | 2 | match, relationship, subsidiary | Query returned 0 rows, expected ≥ 1 |
| `companies-basic-010` | basic | FAIL | 1 | match, aggregation, case-when, sentiment | Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid in |
| `companies-advanced-001` | advanced | FAIL | 1 | qpe, quantified-path, relationship, trav | Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid in |
| `companies-advanced-004` | advanced | FAIL | 1 | vector, index, similarity, procedure | Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid in |
| `companies-advanced-009` | advanced | FAIL | 2 | match, multi-pattern, relationship, aggr | Query returned 0 rows, expected ≥ 1 |
| `companies-complex-001` | complex | FAIL | 2 | call-in-transactions, batch, read | Execution error: {code: Neo.DatabaseError.Transaction.TransactionStartFailed} {m |
| `companies-complex-002` | complex | FAIL | 2 | call-subquery, aggregation, multi-level, | Query returned 0 rows, expected ≥ 1 |
| `rec-basic-003` | basic | FAIL | 2 | match, filter, order-by, limit | Query returned 0 rows, expected ≥ 10 |
| `rec-basic-005` | basic | FAIL | 2 | match, relationship, filter | Query returned 0 rows, expected ≥ 1 |
| `rec-advanced-005` | advanced | FAIL | 2 | variable-length, match, relationship, fi | Query returned 0 rows, expected ≥ 1 |
| `rec-advanced-006` | advanced | FAIL | 2 | fulltext, index, search, match | Execution error: {code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: |
| `rec-expert-002` | expert | FAIL | 2 | qpe, quantified-path, match, relationshi | Query returned 0 rows, expected ≥ 1 |
| `rec-expert-003` | expert | FAIL | 2 | vector, index, similarity, search | Query returned 0 rows, expected ≥ 1 |
| `ucf-basic-002` | basic | FAIL | 2 | match, filter, property | Query returned 0 rows, expected ≥ 1 |
| `ucf-basic-004` | basic | FAIL | 2 | match, filter, fraud | Query returned 0 rows, expected ≥ 1 |
| `ucf-intermediate-003` | intermediate | FAIL | 2 | match, temporal, aggregation | Query returned 0 rows, expected ≥ 1 |
| `ucf-intermediate-004` | intermediate | FAIL | 2 | match, traversal, fraud, shared-identifi | Query returned 0 rows, expected ≥ 1 |
| `ucf-intermediate-005` | intermediate | FAIL | 2 | match, aggregation, filter, email | Query returned 0 rows, expected ≥ 1 |
| `ucf-advanced-001` | advanced | FAIL | 1 | qpe, fraud-ring, quantified-path | Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid in |
| `ucf-advanced-002` | advanced | FAIL | 2 | shortest-path, traversal, fraud | Query returned 0 rows, expected ≥ 1 |
| `ucf-complex-001` | complex | FAIL | 2 | fraud-ring, shared-identifiers, call-sub | Query returned 0 rows, expected ≥ 1 |
| `ucf-complex-002` | complex | FAIL | 2 | temporal, aggregation, fraud, with | Query returned 0 rows, expected ≥ 1 |
| `ucf-complex-004` | complex | FAIL | 2 | search, fulltext, traversal, money-flow | Query returned 0 rows, expected ≥ 1 |
| `ucf-expert-002` | expert | FAIL | 2 | all-shortest, qpe, fraud-ring, paths | Query returned 0 rows, expected ≥ 1 |
| `ucf-expert-003` | expert | FAIL | 2 | qpe, money-laundering, traversal, deep-p | Query returned 0 rows, expected ≥ 1 |
| `ucf-expert-004` | expert | FAIL | 2 | call-in-transactions, batch, write, frau | Execution error: {code: Neo.ClientError.Statement.TypeError} {message: Don't kno |

## 4. Failure Pattern Analysis

Each detected pattern is mapped to the most likely responsible SKILL.md section.

### Detected Patterns Summary

| # | Pattern | Cases | SKILL.md Section |
|---|---------|------:|-----------------|
| 1 | QPE syntax error (wrong quantifier form) | 12 | Core Pattern Cheat Sheet — Quantified Path Expressions |
| 2 | Subquery scope / importing variables | 7 | Core Pattern Cheat Sheet — CALL subqueries |
| 3 | Performance threshold exceeded (Gate 4 WARN/FAIL) | 6 | EXPLAIN / PROFILE Validation Loop |
| 4 | SEARCH clause used for fulltext (vector-only in Preview) | 4 | Core Pattern Cheat Sheet — SEARCH Clause |
| 5 | Vector index dimension mismatch | 3 | Schema-First Protocol |
| 6 | CALL IN TRANSACTIONS inside explicit transaction | 2 | FOREACH vs UNWIND / Core Pattern Cheat Sheet |
| 7 | Unsafe MERGE / missing ON CREATE / ON MATCH | 2 | Core Pattern Cheat Sheet — MERGE Safety |
| 8 | Deprecated variable-length pattern [:REL*] | 1 | Deprecated Syntax → Cypher 25 Preferred |
| 9 | Deprecated shortestPath() / allShortestPaths() | 1 | Deprecated Syntax → Cypher 25 Preferred |
| 10 | Type casting error (toInteger vs toIntegerOrNull) | 1 | Types and Nulls (cypher25-types-and-nulls.md) |

### Pattern Details and Recommendations

#### Pattern 1: QPE syntax error (wrong quantifier form)

**SKILL.md Section**: `Core Pattern Cheat Sheet — Quantified Path Expressions`  
**Affected cases**: 12  

The QPE quantifier uses an unsupported form. Common errors: `+` instead of `{1,}` (demo DB limitation), spaces inside `{m,n}`, or mixing QPE with legacy `[:REL*]` syntax.

**Affected test cases**:

- `companies-basic-010` (FAIL): Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'a': expected an
- `companies-advanced-001` (FAIL): Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '-': expected '(
- `companies-advanced-004` (FAIL): Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '..': expected a
- `companies-complex-001` (FAIL): Execution error: {code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A query with
- `rec-advanced-005` (FAIL): Query returned 0 rows, expected ≥ 1
- `rec-advanced-006` (FAIL): Execution error: {code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to invoke pr
- `rec-expert-002` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-advanced-001` (FAIL): Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '-': expected '(
- `ucf-advanced-002` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-expert-002` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-expert-003` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-expert-004` (FAIL): Execution error: {code: Neo.ClientError.Statement.TypeError} {message: Don't know how to treat that 

**Before (problematic pattern)**:

```cypher
MATCH (a)(()-[:HAS_SUBSIDIARY]->())+(b) RETURN b.name
```

**After (recommended pattern)**:

```cypher
CYPHER 25
MATCH (a)(()-[:HAS_SUBSIDIARY]->()){1,}(b) RETURN b.name
```

**Recommended SKILL.md edit**:

> Add a QPE compatibility note: 'Prefer `{1,}` over `+` and `{0,}` over `*` for maximum database compatibility. The `+` / `*` shorthands may not be enabled on all servers.' Update the QPE syntax table to show both forms with a compatibility column.

#### Pattern 2: Subquery scope / importing variables

**SKILL.md Section**: `Core Pattern Cheat Sheet — CALL subqueries`  
**Affected cases**: 7  

Variables are not correctly imported into a CALL subquery. In Cypher 25, use `CALL (x, y) { ... }` scope clause syntax. The deprecated `WITH x, y` as first clause inside CALL is no longer valid.

**Affected test cases**:

- `companies-basic-010` (FAIL): Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'a': expected an
- `companies-advanced-004` (FAIL): Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '..': expected a
- `companies-complex-001` (FAIL): Execution error: {code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A query with
- `companies-complex-002` (FAIL): Query returned 0 rows, expected ≥ 1
- `rec-advanced-006` (FAIL): Execution error: {code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to invoke pr
- `ucf-complex-001` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-expert-004` (FAIL): Execution error: {code: Neo.ClientError.Statement.TypeError} {message: Don't know how to treat that 

**Before (problematic pattern)**:

```cypher
MATCH (n) CALL { WITH n MATCH (n)-[:HAS_SUBSIDIARY]->(s) RETURN s }
```

**After (recommended pattern)**:

```cypher
CYPHER 25
MATCH (n)
CALL (n) { MATCH (n)-[:HAS_SUBSIDIARY]->(s) RETURN s }
RETURN s.name
```

**Recommended SKILL.md edit**:

> Update the subqueries reference: replace all `CALL { WITH x ...}` examples with the `CALL (x) { ... }` scope clause form. Add a migration note: 'Importing WITH inside CALL is deprecated in Cypher 25.'

#### Pattern 3: Performance threshold exceeded (Gate 4 WARN/FAIL)

**SKILL.md Section**: `EXPLAIN / PROFILE Validation Loop`  
**Affected cases**: 6  

The query exceeds the configured db-hits, memory, or elapsed-time threshold. Often caused by: full label scans instead of index seeks, Cartesian products from unlinked patterns, or collecting unbounded result sets.

**Affected test cases**:

- `companies-basic-010` (FAIL): Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'a': expected an
- `companies-advanced-009` (FAIL): Query returned 0 rows, expected ≥ 1
- `companies-complex-002` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-intermediate-003` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-intermediate-005` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-complex-002` (FAIL): Query returned 0 rows, expected ≥ 1

**Before (problematic pattern)**:

```cypher
-- Full label scan + Cartesian product --
MATCH (a:Organization), (b:Organization)
WHERE a.name CONTAINS 'Inc' RETURN count(*)
```

**After (recommended pattern)**:

```cypher
CYPHER 25
-- Use index-backed predicate --
MATCH (a:Organization)
WHERE a.name CONTAINS 'Inc'
RETURN count(*)
```

**Recommended SKILL.md edit**:

> In the EXPLAIN/PROFILE Validation Loop section, add: 'When PROFILE shows high dbHits, check for: (1) missing index hints, (2) Cartesian products (look for `CartesianProduct` in the plan), (3) unbounded traversals without LIMIT.' Link to the indexes L3 reference for hint syntax.

#### Pattern 4: SEARCH clause used for fulltext (vector-only in Preview)

**SKILL.md Section**: `Core Pattern Cheat Sheet — SEARCH Clause`  
**Affected cases**: 4  

The SEARCH clause is vector-only in Neo4j 2026.01 (Preview). For fulltext queries, the skill must use `db.index.fulltext.queryNodes()` or `db.index.fulltext.queryRelationships()`.

**Affected test cases**:

- `companies-advanced-004` (FAIL): Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '..': expected a
- `rec-advanced-006` (FAIL): Execution error: {code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to invoke pr
- `rec-expert-003` (FAIL): Query returned 0 rows, expected ≥ 1
- `ucf-complex-004` (FAIL): Query returned 0 rows, expected ≥ 1

**Before (problematic pattern)**:

```cypher
CYPHER 25
SEARCH (n:Article USING fulltext) WHERE n.text CONTAINS 'graph'
```

**After (recommended pattern)**:

```cypher
CYPHER 25
CALL db.index.fulltext.queryNodes('entity', 'graph') YIELD node, score
RETURN node.name, score
```

**Recommended SKILL.md edit**:

> Add a clear callout to the SEARCH Clause section: 'The SEARCH clause is **vector-only** (Preview). For fulltext indexes, always use the `db.index.fulltext.queryNodes()` procedure.' Put this note on the first line of the section.

#### Pattern 5: Vector index dimension mismatch

**SKILL.md Section**: `Schema-First Protocol`  
**Affected cases**: 3  

The query passes a vector of the wrong dimensionality to a vector index. The skill must inspect the index `OPTIONS` map for `vector.dimensions` before authoring vector queries.

**Affected test cases**:

- `companies-advanced-004` (FAIL): Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input '..': expected a
- `rec-advanced-006` (FAIL): Execution error: {code: Neo.ClientError.Procedure.ProcedureCallFailed} {message: Failed to invoke pr
- `rec-expert-003` (FAIL): Query returned 0 rows, expected ≥ 1

**Before (problematic pattern)**:

```cypher
-- hard-codes 1536-dim vector without checking the index --
CALL db.index.vector.queryNodes('news', 5, $embedding)
```

**After (recommended pattern)**:

```cypher
-- Schema-First: inspect first --
SHOW VECTOR INDEXES YIELD name, options
-- Then use the correct dimension from options.vector.dimensions
```

**Recommended SKILL.md edit**:

> Add an explicit step to the Schema-First Protocol: 'For vector queries, run `SHOW VECTOR INDEXES YIELD name, options` and read `options.vector.dimensions` before calling the vector procedure. Never hard-code embedding dimensions.' Also add this as a note in the SEARCH Clause section.

#### Pattern 6: CALL IN TRANSACTIONS inside explicit transaction

**SKILL.md Section**: `FOREACH vs UNWIND / Core Pattern Cheat Sheet`  
**Affected cases**: 2  

`CALL { ... } IN TRANSACTIONS` requires an *implicit* transaction. The harness wraps write queries in an explicit `BEGIN` transaction, which causes `TransactionStartFailed`. The query itself may be correct but cannot be tested this way.

**Affected test cases**:

- `companies-complex-001` (FAIL): Execution error: {code: Neo.DatabaseError.Transaction.TransactionStartFailed} {message: A query with
- `ucf-expert-004` (FAIL): Execution error: {code: Neo.ClientError.Statement.TypeError} {message: Don't know how to treat that 

**Before (problematic pattern)**:

```cypher
-- Fails in explicit BEGIN/COMMIT block --
CALL { MATCH (n:Org) CALL { WITH n ... } IN TRANSACTIONS OF 100 ROWS }
```

**After (recommended pattern)**:

```cypher
-- Correct: only valid as top-level implicit transaction --
CYPHER 25
MATCH (n:Organization)
CALL { WITH n ... } IN TRANSACTIONS OF 100 ROWS
```

**Recommended SKILL.md edit**:

> Add a warning box to the CALL IN TRANSACTIONS reference file: 'This construct MUST be the outermost query (no wrapping BEGIN/COMMIT). Test harness marks these is_write_query=true; failures here are a harness limitation, not a skill deficiency.' Also ensure runner.py marks such failures with a note in gate_details.

#### Pattern 7: Unsafe MERGE / missing ON CREATE / ON MATCH

**SKILL.md Section**: `Core Pattern Cheat Sheet — MERGE Safety`  
**Affected cases**: 2  

The MERGE clause is missing `ON CREATE SET` / `ON MATCH SET` sub-clauses, or MERGE is applied to a pattern that is too broad (e.g., MERGE on a relationship without both anchored nodes already bound).

**Affected test cases**:

- `companies-basic-010` (FAIL): Syntax error: {code: Neo.ClientError.Statement.SyntaxError} {message: Invalid input 'a': expected an
- `ucf-expert-004` (FAIL): Execution error: {code: Neo.ClientError.Statement.TypeError} {message: Don't know how to treat that 

**Before (problematic pattern)**:

```cypher
MERGE (o:Organization {name: $name})-[:HAS_CEO]->(p:Person {name: $ceo})
```

**After (recommended pattern)**:

```cypher
CYPHER 25
MERGE (o:Organization {name: $name})
ON CREATE SET o.createdAt = datetime()
MERGE (p:Person {name: $ceo})
MERGE (o)-[:HAS_CEO]->(p)
```

**Recommended SKILL.md edit**:

> Reinforce the MERGE Safety section: 'MERGE a relationship only after MERGE-ing (or MATCH-ing) both endpoint nodes separately. Always include ON CREATE SET / ON MATCH SET to set timestamps or counters.' Add a two-step MERGE pattern as the canonical example.

#### Pattern 8: Deprecated variable-length pattern [:REL*]

**SKILL.md Section**: `Deprecated Syntax → Cypher 25 Preferred`  
**Affected cases**: 1  

The query uses the deprecated `[:REL*]` variable-length syntax instead of a Quantified Path Expression (QPE).

**Affected test cases**:

- `rec-advanced-005` (FAIL): Query returned 0 rows, expected ≥ 1

**Before (problematic pattern)**:

```cypher
MATCH (a)-[:HAS_SUBSIDIARY*1..5]->(b) RETURN b.name
```

**After (recommended pattern)**:

```cypher
CYPHER 25
MATCH (a)(()-[:HAS_SUBSIDIARY]->()){1,5}(b) RETURN b.name
```

**Recommended SKILL.md edit**:

> The Deprecated Syntax table maps `[:REL*]` → QPE. Add a callout box in the QPE section: 'Never use [:REL*n..m]. Always use QPE `()-[:REL]->{n,m}()`.' Include a side-by-side old/new example.

#### Pattern 9: Deprecated shortestPath() / allShortestPaths()

**SKILL.md Section**: `Deprecated Syntax → Cypher 25 Preferred`  
**Affected cases**: 1  

The query uses deprecated `shortestPath()` or `allShortestPaths()` instead of the Cypher 25 `SHORTEST` keyword.

**Affected test cases**:

- `ucf-advanced-002` (FAIL): Query returned 0 rows, expected ≥ 1

**Before (problematic pattern)**:

```cypher
MATCH p = shortestPath((a)-[:HAS_SUBSIDIARY*]->(b)) RETURN p
```

**After (recommended pattern)**:

```cypher
CYPHER 25
MATCH p = SHORTEST 1 (a)-[:HAS_SUBSIDIARY]->{1,}(b) RETURN p
```

**Recommended SKILL.md edit**:

> Expand the 'SHORTEST' row in the deprecated syntax table: add a note that `SHORTEST 1` replaces `shortestPath()` and `SHORTEST k` replaces `allShortestPaths()`. Include both migration examples.

#### Pattern 10: Type casting error (toInteger vs toIntegerOrNull)

**SKILL.md Section**: `Types and Nulls (cypher25-types-and-nulls.md)`  
**Affected cases**: 1  

Base casting functions (`toInteger`, `toFloat`, etc.) throw on unconvertible input. Agent queries should use the `OrNull` variants (`toIntegerOrNull`, `toFloatOrNull`) to avoid runtime errors on dirty data.

**Affected test cases**:

- `ucf-expert-004` (FAIL): Execution error: {code: Neo.ClientError.Statement.TypeError} {message: Don't know how to treat that 

**Before (problematic pattern)**:

```cypher
RETURN toInteger(n.population) AS pop
```

**After (recommended pattern)**:

```cypher
RETURN toIntegerOrNull(n.population) AS pop
```

**Recommended SKILL.md edit**:

> Add to the types-and-nulls reference: 'Prefer `toFloatOrNull()`, `toIntegerOrNull()` over base variants in agent queries — they return null instead of throwing on unconvertible input.' Bold this preference in the SKILL.md types section.

## 5. Unclassified Failures

The following non-PASS cases did not match any known pattern. Manual review required.

**`companies-basic-006`** (basic / FAIL)

> Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (:Organization {name: 'Blackstone Group'})-[:HAS_SUBSIDIARY]->(sub:Organization)
RETURN sub.name AS subsidiary
LIMIT 10
```

**`rec-basic-003`** (basic / FAIL)

> Query returned 0 rows, expected ≥ 10

```cypher
CYPHER 25
MATCH (m:Movie)
WHERE m.released > 2000
RETURN m.title, m.released, m.imdbRating
ORDER BY m.released DESC
LIMIT 10
```

**`rec-basic-005`** (basic / FAIL)

> Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (p:Person)-[:ACTED_IN]->(m:Movie {title: 'The Matrix'})
RETURN p.name AS actor, p.born AS birthYear
ORDER BY p.name
```

**`ucf-basic-002`** (basic / FAIL)

> Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (a:Account {status: "active"})
RETURN a.accountNumber AS accountNumber, a.balance AS balance
ORDER BY a.balance DESC
LIMIT 20
```

**`ucf-basic-004`** (basic / FAIL)

> Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (c:Customer)
WHERE c.fraudFlag = true
RETURN c.customerID, c.name, c.pagerank, c.betweenness, c.louvainCommunity
ORDER BY c.pagerank DESC
```

**`ucf-intermediate-004`** (intermediate / FAIL)

> Query returned 0 rows, expected ≥ 1

```cypher
CYPHER 25
MATCH (a:Account)-[:SHARED_IDENTIFIERS]->(b:Account)
WHERE a.accountNumber < b.accountNumber
RETURN a.accountNumber AS account1, b.accountNumber AS account2
ORDER BY account1, account2
```

## 6. Tag Cluster Analysis

Frequency of tags appearing in non-PASS cases:

| Tag | Occurrences |
|-----|------------:|
| `match` | 13 |
| `relationship` | 7 |
| `aggregation` | 6 |
| `filter` | 6 |
| `qpe` | 5 |
| `traversal` | 5 |
| `fraud` | 5 |
| `quantified-path` | 3 |
| `index` | 3 |
| `search` | 3 |
| `fraud-ring` | 3 |
| `vector` | 2 |
| `similarity` | 2 |
| `category` | 2 |
| `call-in-transactions` | 2 |
| `batch` | 2 |
| `call-subquery` | 2 |
| `depth` | 2 |
| `fulltext` | 2 |
| `temporal` | 2 |
| `shared-identifiers` | 2 |
| `subsidiary` | 1 |
| `case-when` | 1 |
| `sentiment` | 1 |
| `procedure` | 1 |
| `multi-pattern` | 1 |
| `read` | 1 |
| `multi-level` | 1 |
| `order-by` | 1 |
| `limit` | 1 |
| `variable-length` | 1 |
| `bounded` | 1 |
| `property` | 1 |
| `email` | 1 |
| `shortest-path` | 1 |
| `with` | 1 |
| `money-flow` | 1 |
| `all-shortest` | 1 |
| `paths` | 1 |
| `money-laundering` | 1 |
| `deep-path` | 1 |
| `write` | 1 |
| `fraud-flagging` | 1 |

---

_This report was generated by `scripts/analyze-results.py` at 2026-03-21T13:22:42Z. It is for human review only — no automatic changes are made to SKILL.md._
