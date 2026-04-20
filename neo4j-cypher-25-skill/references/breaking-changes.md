# Cypher 25 breaking changes (vs Cypher 5)

These are the items **removed** or **tightened** in Cypher 25. A query that depends on any of them will fail under `CYPHER 25`.

## Syntax removals

### `SET node = relationship` / `SET node = node` (right-hand side as entity)

Wrap the RHS in `properties()`.

```cypher
// Cypher 5 (still works there)
MATCH (n:Order)-[r:SHIPPED_TO]->(:Address)
SET n = r

// Cypher 25
MATCH (n:Order)-[r:SHIPPED_TO]->(:Address)
SET n = properties(r)
```

### Cross-entity property references inside a single `MERGE`

You can no longer read a property of one pattern element while still defining another in the same `MERGE`.

```cypher
// Cypher 5 (still works there)
MERGE (a {foo:1})-[:T]->(b {foo:a.foo})

// Cypher 25 — split it
MERGE (a {foo:1})
MERGE (a)-[:T]->(b {foo:a.foo})
```

### Composite-database graph references

A qualified composite graph name must be one backticked token.

```cypher
// Cypher 5
USE composite.`sub1`

// Cypher 25
USE `composite.sub1`
```

### Unicode in unescaped identifiers

Control / special-category codepoints (`\u0085`, `\u0024`, and others) are no longer accepted inside bare identifiers. Either rename the identifier or wrap it in backticks.

## Removed database / index options

- `CREATE INDEX … OPTIONS { indexProvider: '…' }` — drop the option; the planner picks the provider.
- `CREATE CONSTRAINT … OPTIONS { indexProvider: '…' }` — same.
- `CREATE DATABASE … OPTIONS { seedCredentials: … }` — removed.
- `CREATE DATABASE … OPTIONS { existingDataSeedInstance: … }` — replaced by `existingDataSeedServer`.

## Removed procedures

Replace calls before switching to Cypher 25:

| Removed                                   | Replacement                                                         |
|-------------------------------------------|---------------------------------------------------------------------|
| `db.create.setVectorProperty(n, p, arr)`  | `SET n[p] = vector($arr, $dim, FLOAT32)`                            |
| `db.index.vector.createNodeIndex(...)`    | `CREATE VECTOR INDEX name FOR (n:Label) ON (n.prop) OPTIONS {...}`  |
| `dbms.cluster.readReplicaToggle(...)`     | Modern cluster admin via `neo4j-admin` / Aura API                   |
| `dbms.cluster.uncordonServer(...)`        | `neo4j-admin server uncordon`                                       |
| `dbms.quarantineDatabase(...)`            | No direct replacement; use database lifecycle commands              |
| `dbms.upgrade()`                          | Handled automatically by the server on startup                      |
| `dbms.upgradeStatus()`                    | `SHOW DATABASES` plus server logs                                   |

## Behavior tightening

- **Impossible `REVOKE` statements now raise an error** (were silent notifications in Cypher 5). Audit any generated permission scripts.

## Things deprecated but not yet removed

- `CREATE DATABASE … OPTIONS { existingData: … }` — plan to move to `existingDataSeedServer`.

## Quick regex checklist for audits

```
SET\s+[A-Za-z_][\w]*\s*=\s*[A-Za-z_][\w]*\s*(?:[\s,;)\]]|$)   # SET a = b
MERGE\s*\([^)]*\{[^}]*\b\w+\.\w+\b                             # MERGE with x.y inside properties
OPTIONS\s*\{[^}]*indexProvider                                 # deprecated option
db\.create\.setVectorProperty                                  # removed procs
db\.index\.vector\.createNodeIndex
dbms\.(upgrade|upgradeStatus|quarantineDatabase|cluster\.readReplicaToggle|cluster\.uncordonServer)
```

The regexes are conservative; review each hit — a pattern like `SET a = b` is only a problem when `b` is a node or relationship variable.
