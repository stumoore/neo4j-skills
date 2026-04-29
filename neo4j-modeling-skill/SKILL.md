---
name: neo4j-modeling-skill
description: Use when designing or reviewing a Neo4j graph data model: choosing node labels and
  relationship types, deciding what to embed vs reference, normalizing or denormalizing
  for traversal performance, reviewing a schema against graph modeling best practices,
  or migrating a relational/document schema to a graph. Does NOT handle Cypher query
  writing — use neo4j-cypher-skill. Does NOT handle application-side mapping (Spring
  Data Neo4j OGM, GraphQL type definitions) — use neo4j-spring-data-skill or
  neo4j-graphql-skill.
status: draft
version: 0.1.0
allowed-tools: WebFetch
---

# Neo4j Modeling Skill

## When to Use

- Designing a graph data model from scratch (domain → nodes, relationships, properties)
- Reviewing an existing model for anti-patterns (generic nodes, unnecessary collections)
- Deciding what to model as a node vs a property vs a relationship
- Migrating a relational or document schema to a graph

## When NOT to Use

- **Writing or optimizing Cypher queries** → use `neo4j-cypher-skill`
- **Spring Data Neo4j entity mapping (@Node, @Relationship)** → use `neo4j-spring-data-skill`
- **GraphQL type definitions** → use `neo4j-graphql-skill`
- **Importing data** → use `neo4j-import-skill`

---

## MCP Tool Usage

When designing or reviewing an existing schema, use `get-schema` first:

| Operation | MCP tool | Notes |
|---|---|---|
| Inspect existing schema | `get-schema` | Run before proposing any changes |
| `SHOW CONSTRAINTS`, `SHOW INDEXES` | `read-cypher` | Verify what already exists |
| `CREATE CONSTRAINT ... IF NOT EXISTS` | `write-cypher` | Safe to run repeatedly |

Never propose schema changes without first inspecting the current state.

---

## Inspect Before Designing

**On an existing database**, always run this before proposing model changes:
```cypher
CALL db.schema.visualization() YIELD nodes, relationships RETURN nodes, relationships;
SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties RETURN name, type, labelsOrTypes, properties;
SHOW INDEXES YIELD name, type, labelsOrTypes, state WHERE state = 'ONLINE' RETURN name, type, labelsOrTypes;
```

---

## Modeling Decision Tree

```
1. Is it a "thing" with identity and multiple query entry points? → Node
2. Is it a connection between two things with direction or properties? → Relationship
3. Is it a simple scalar always queried with its parent? → Property on parent node
4. Is it a fact with its own properties or multiple connections? → Intermediate node
5. Is it a type/category queried separately? → Label (not a property)
```

### Property vs Separate Node

Extract property → node when:
- Value is shared across many nodes (high duplication risk)
- Need to traverse/query through it (e.g., "all movies in English")
- Value has its own attributes

Keep as property when:
- Always queried alongside the parent; never traversed independently
- Low cardinality variation; indexing not needed
- Computed or derived value

---

## Core Principles

**Labels** — noun-like, PascalCase, describe what an entity *is* (`:Person`, `:Product`). Avoid generic labels like `:Node` or `:Entity`.
Max 4 labels per node — overuse degrades lookup performance.

**Relationship types** — verb-like, SCREAMING_SNAKE_CASE, describe the *direction* of the connection (`:KNOWS`, `:PURCHASED`). Avoid generic types like `:RELATED_TO`.

**Properties** — camelCase. Only store what you query. Large blobs (embeddings, full text) belong on dedicated nodes.

**Constraints** — every node type used in MERGE must have a uniqueness constraint on its key property. Apply before importing data.

---

## Fanout and Supernodes

**Fanout** = one node connected to many others via the same relationship type. Intentional when the node represents a genuine hub (e.g., a `Language` node linked to all movies). Accidental when it should be a property.

**Supernode** = node with 100K+ relationships. Causes full-neighbor scans; query plans degrade. Signs: profiler shows very high db hits on a single node.

Mitigation:
- Replace generic rel type with specific ones: `:ACTED_IN` → `:ACTED_IN_1995` (year-bucketed)
- Partition using intermediate nodes (e.g., `Employment` between `Person` and `Company`)
- Filter relationship traversal with `WHERE` on rel properties before collecting

---

## Refactoring Pattern

Three-step process — always follow this order:

1. **Design new model** — identify what changes (add label, extract node, specialize rel)
2. **Transform data** — write Cypher to migrate; use `CALL IN TRANSACTIONS` on large graphs
3. **Retest use cases** — run PROFILE on all affected queries; verify no regressions

### Add label (subtype extraction)

```cypher
// Add :Actor label to Person nodes that have ACTED_IN relationships
MATCH (p:Person)
WHERE EXISTS { (p)-[:ACTED_IN]->() }
SET p:Actor
```

### Extract property → node (deduplication)

```cypher
// Turn languages list property into Language nodes
MATCH (m:Movie)
UNWIND m.languages AS language
MERGE (l:Language {name: language})
MERGE (m)-[:IN_LANGUAGE]->(l)
SET m.languages = null
```

### Specialize relationship types (performance)

```cypher
// Add year-bucketed rels alongside generic ones (keep both)
MATCH (a:Actor)-[:ACTED_IN]->(m:Movie)
CALL apoc.merge.relationship(a, 'ACTED_IN_' + left(m.released, 4), {}, {}, m, {}) YIELD rel
RETURN count(*) AS merged
```

After specialization the year-scoped query traverses far fewer nodes:
```cypher
// Before: traverses all Tom Hanks movies
MATCH (p:Actor {name:'Tom Hanks'})-[:ACTED_IN]->(m:Movie) WHERE m.released STARTS WITH '1995' RETURN m.title
// After: direct traversal
MATCH (p:Actor {name:'Tom Hanks'})-[:ACTED_IN_1995]->(m:Movie) RETURN m.title
```

---

## Intermediate Nodes

Use when:
- Relationship needs more than two endpoint properties (hyperedge)
- Multiple entities need to share the same "connection data"
- The relationship itself has its own lifecycle or attributes

Example — `Employment` intermediate node:
```cypher
// Before: WORKS_AT with from/to/role loses role-sharing
// After: Employment node connects Person, Company, and Role
(:Person)-[:HAS_EMPLOYMENT]->(:Employment {from: date('2020-01-01'), to: null})
    -[:AT_COMPANY]->(:Company)
(:Employment)-[:WITH_ROLE]->(:Role {title: 'Engineer'})
```

---

## Schema Review Checklist

- [ ] Every node label has a unique constraint on its identifier property
- [ ] No generic labels (`:Node`, `:Entity`, `:Thing`) — max 4 labels per node
- [ ] No generic relationship types (`:RELATED_TO`, `:HAS`)
- [ ] Relationship direction encodes meaning (not arbitrary)
- [ ] Duplicated property values extracted to shared nodes
- [ ] No supernodes (>100K rels) — partition or bucket if present
- [ ] Embedding properties stored on dedicated `:Chunk` nodes, not on business nodes
- [ ] Properties that are never filtered/sorted are not indexed
- [ ] Intermediate nodes used for many-to-many with properties (not bare relationships)
- [ ] Labels are PascalCase; relationship types are SCREAMING_SNAKE_CASE

---

## Output Format (Schema Assessment)

```
## Schema Assessment

### Compliant
- [item checked]

### Issues Found
#### [Issue Title] — Severity: HIGH / MEDIUM / LOW
- Current: [what the model does]
- Problem: [why it is an issue]
- Fix: [specific recommendation]

## Recommended Schema
[nodes, relationships, properties, constraints]
```

---

## References

- [Graph Data Modeling Guide](https://neo4j.com/docs/getting-started/data-modeling/)
- [GraphAcademy: Graph Data Modeling Fundamentals](https://graphacademy.neo4j.com/courses/modeling-fundamentals/)
