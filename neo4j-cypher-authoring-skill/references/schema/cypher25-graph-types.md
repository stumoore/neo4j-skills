> Source: verified against Neo4j 2026.02.2 Enterprise — hand-authored
> Generated: 2026-03-24T00:00:00Z
> See: version-matrix.md for availability

> **PREVIEW — Enterprise Edition only, Neo4j 2026.02+**
> GRAPH TYPE DDL is a Preview feature. Not for production use. Syntax may change before GA.
> Only available in Enterprise Edition. Community Edition does not support GRAPH TYPE.

# GRAPH TYPE DDL

GRAPH TYPE DDL adds optional schema constraints to a graph database. Only explicitly declared
element types (node types and relationship types) are subject to constraint enforcement. All
other nodes and relationships remain unconstrained (open-model semantics).

## CRITICAL: Syntax Differs From Documentation — Use Verified Forms Below

The correct syntax uses `IMPLIES {}` blocks (NOT `::` or `[]` notation from older docs):

```
-- Property declaration: propName TYPE [NOT NULL]  (NO colon between name and type)
-- Valid: name STRING NOT NULL   OR   name STRING!
-- INVALID: name :: STRING NOT NULL  (the :: separator is NOT used inside IMPLIES blocks)
```

## SHOW CURRENT GRAPH TYPE

```cypher
CYPHER 25
SHOW CURRENT GRAPH TYPE
```

Returns 1 row with a `specification` column showing all declared element types.

```cypher
CYPHER 25
SHOW CURRENT GRAPH TYPE YIELD *
```

> **Note**: `SHOW GRAPH TYPES` is NOT valid — use `SHOW CURRENT GRAPH TYPE`.

## ALTER CURRENT GRAPH TYPE SET (declare element types)

Each call to `ALTER CURRENT GRAPH TYPE SET { ... }` adds to (or updates) the existing graph type.
To "extend" the schema, simply call `ALTER CURRENT GRAPH TYPE SET` again with new element types.
There is no separate EXTEND command — `EXTEND GRAPH TYPE WITH` is NOT valid syntax.

### Declare a node element type

```cypher
CYPHER 25
ALTER CURRENT GRAPH TYPE SET {
  (:Person IMPLIES { name STRING NOT NULL, age INTEGER })
}
```

- Properties: `propName TYPE` — no colon between name and type
- `NOT NULL` or `!` marks a property as mandatory: `name STRING NOT NULL` or `name STRING!`
- Optional properties (type-validated if present): `age INTEGER`

### Declare a relationship element type

```cypher
CYPHER 25
ALTER CURRENT GRAPH TYPE SET {
  (:Person)-[:KNOWS IMPLIES { since DATE }]->(:Person)
}
```

Relationship element types require source and target node label patterns.
The `IMPLIES {}` block lists property constraints (empty `{}` is valid for no property constraints).

### Declare multiple element types in one statement

```cypher
CYPHER 25
ALTER CURRENT GRAPH TYPE SET {
  (:Person IMPLIES { name STRING NOT NULL }),
  (:Person)-[:KNOWS IMPLIES { since DATE NOT NULL }]->(:Person)
}
```

## Adding Element Types to Existing Schema ("Extend")

To add new element types without removing existing ones, call `ALTER CURRENT GRAPH TYPE SET`
with only the new types. Existing element types are preserved.

```cypher
-- First declaration:
CYPHER 25
ALTER CURRENT GRAPH TYPE SET {
  (:Company IMPLIES { name STRING NOT NULL, founded INTEGER })
}

-- Later, add more types (does not remove Company):
CYPHER 25
ALTER CURRENT GRAPH TYPE SET {
  (:Employee IMPLIES { employeeId STRING NOT NULL }),
  (:Company)-[:EMPLOYS IMPLIES { startDate DATE NOT NULL }]->(:Employee)
}
```

## Element Type Property Types

Valid property types in IMPLIES blocks:

| Type | Example |
|---|---|
| `STRING` | `name STRING NOT NULL` |
| `INTEGER` | `age INTEGER` |
| `FLOAT` | `amount FLOAT NOT NULL` |
| `BOOLEAN` | `active BOOLEAN` |
| `DATE` | `startDate DATE` |
| `DATETIME` | `createdAt DATETIME NOT NULL` |
| `DURATION` | `ttl DURATION` |

## SKILL.md Routing

GRAPH TYPE clauses are SCHEMA operations — route to `references/schema/` alongside indexes and constraints.

> **Available: Neo4j 2026.02+ Enterprise Edition** — use `references/version-matrix.md` to check availability before generating GRAPH TYPE queries.
