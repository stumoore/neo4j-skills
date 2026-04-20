---
name: neo4j-cypher-25-skill
description: Use when writing, reviewing, or migrating Cypher queries between Cypher 5 and Cypher 25 on Neo4j 2025.06+. Covers the version selector, breaking changes, and new features.
allowed-tools: WebFetch
---

# Cypher 5 vs Cypher 25 skill

Since Neo4j 2025.06, Cypher is versioned **independently** of the server. Two languages coexist:

- **Cypher 5** — frozen. Bug fixes and perf only, no new features. Supported for at least two more LTS cycles (~5–6 years).
- **Cypher 25** — the evolving language. All new Cypher features (vector type, conditional subqueries, `LET`/`NEXT`/`FILTER`, walk semantics, etc.) land here only. Guaranteed additive from 2025.06 onward.

From Neo4j 2026.02, Cypher 25 is the **default** for new databases. Existing databases upgraded from earlier versions stay on Cypher 5 until you opt in.

## When to use

Use this skill when:
- the user asks about Cypher 25, Cypher 5, version selectors, or `CYPHER 25`/`CYPHER 5` prefixes
- migrating queries from Cypher 5 to Cypher 25
- a query fails with a version-related error (e.g. `SET n = r` rejected, unknown function)
- deciding which language to default a new database to

## Version selector

**Per query** (overrides the database default):

```cypher
CYPHER 25
MATCH (p:Person {name: $name}) RETURN p
```

```cypher
CYPHER 5
MATCH (p:Person {name: $name}) RETURN p
```

Can be combined with other options: `CYPHER 25 runtime=parallel MATCH ...`.

**Per database**:

```cypher
CREATE DATABASE analytics SET DEFAULT LANGUAGE CYPHER 25;
ALTER  DATABASE analytics SET DEFAULT LANGUAGE CYPHER 25;
```

**Server-wide default** (2026.02+): `db.query.default_language=CYPHER_25` in `neo4j.conf`.

**Check a database's language**: `SHOW DATABASES YIELD name, currentPrimariesCount, defaultLanguage`.

## The handful of breaking changes a Cypher-5 query will hit

These are the ones that make an existing query fail under `CYPHER 25`:

1. **`SET n = r` is no longer allowed** (where `r` is a node/relationship on the right). Use `SET n = properties(r)`.
2. **`MERGE` can no longer reference one pattern entity's property from another** in the same `MERGE`. Example that now fails: `MERGE (a {foo:1})-[:T]->(b {foo:a.foo})`. Split into two `MERGE` statements.
3. **Composite-database graph references must be fully quoted as one token**: `` USE `composite.sub1` `` — not `` USE composite.`sub1` ``.
4. **Unicode in unescaped identifiers is rejected** (`\u0085`, `\u0024`, etc.). Wrap the identifier in backticks or rename it.
5. **`indexProvider` in `OPTIONS {…}` on `CREATE INDEX`/constraint is gone.** Drop it.
6. **Removed procedures** — replace calls to:
   - `db.create.setVectorProperty()` → `SET n.embedding = vector($values, $dim, FLOAT32)`
   - `db.index.vector.createNodeIndex()` → `CREATE VECTOR INDEX … FOR (n:Label) ON n.prop …`
   - `dbms.upgrade()`, `dbms.upgradeStatus()`, `dbms.quarantineDatabase()`, `dbms.cluster.readReplicaToggle()`, `dbms.cluster.uncordonServer()` — no direct replacement; handled by modern admin tooling.
7. **Impossible `REVOKE` statements now error** instead of silently returning a notification.

Full enumerated list: [references/breaking-changes.md](references/breaking-changes.md).

## The Cypher 25 features worth reaching for

- **Vector type and functions**: `VECTOR([1.0, 2.0, 3.0], 3, FLOAT32)`, `vector_distance()`, `vector_norm()`, `vector_dimension_count()`. Vector indexes now support multiple labels and extra filter properties.
- **Dynamic labels/types**: `MATCH (n:$(labelVar))` / `MERGE ()-[:$(typeVar)]->()` instead of APOC for the common case.
- **Conditional subqueries**: `CALL { WHEN cond THEN … ELSE … }` for branching updates.
- **Collection functions** (namespaced): `coll.sort()`, `coll.distinct()`, `coll.flatten()`, `coll.max()`, `coll.min()`, `coll.indexOf()`, `coll.insert()`, `coll.remove()`.
- **GQL-flavored composition**: `LET x = …`, `NEXT`, `FILTER`, `RETURN ALL`.
- **Walk semantics**: `MATCH REPEATABLE ELEMENTS …` lets a path reuse relationships; `DIFFERENT RELATIONSHIPS` is the Cypher-5-equivalent default.
- **Temporal `format(temporal, pattern)`** for dynamic formatting instead of `toString()` tricks.
- **Read → write transitions no longer need `WITH`**: `MATCH (p:Person) CREATE (p)-[:HAS]->(:Thing)` is accepted directly.
- **Parameters in more places**: numeric-leading names (`$0hello`), inside `SHORTEST` / `ANY` path selectors.
- **New constraint kinds**: `NODE_LABEL_EXISTENCE`, `RELATIONSHIP_SOURCE_LABEL`, `RELATIONSHIP_TARGET_LABEL`.

Full additions list and examples: [references/new-features.md](references/new-features.md).

## Instructions

When asked to migrate Cypher 5 → Cypher 25:

1. **Decide scope**: whole database (flip default with `ALTER DATABASE`) vs selected queries (prepend `CYPHER 25`).
2. **Grep the codebase / queries** for the breaking patterns above. The highest-hit ones in practice:
   - `SET\s+\w+\s*=\s*\w+\s*$` (plain `SET a = b` where b could be a node/rel)
   - `MERGE` patterns with cross-entity property references
   - `OPTIONS\s*{[^}]*indexProvider`
   - Calls to the removed procedures listed above
3. **For each break, apply the fix** from the breaking-changes list — do not just pin to `CYPHER 5`; that blocks future features.
4. **Recommend opt-in new features** only when they simplify existing code (dynamic labels replacing APOC, vector type replacing `db.create.setVectorProperty`). Don't rewrite working code for novelty.
5. **Verify** with `EXPLAIN CYPHER 25 <query>` — it will surface any remaining syntax rejections without executing.

When writing fresh Cypher for 2025.06+: default to Cypher 25.

## Resources

- [Cypher version selection](https://neo4j.com/docs/cypher-manual/current/queries/select-version/)
- [Cypher additions, deprecations, removals](https://neo4j.com/docs/cypher-manual/current/deprecations-additions-removals-compatibility/)
- [Cypher versioning blog post](https://neo4j.com/blog/developer/cypher-versioning/)
- [Default-language server config](https://neo4j.com/docs/operations-manual/current/configuration/cypher-version-configuration/)
- [Cypher 25 cheat sheet](https://neo4j.com/docs/cypher-cheat-sheet/25/all/)
