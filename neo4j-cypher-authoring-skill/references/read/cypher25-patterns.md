> Source: git@github.com:neo4j/docs-cypher.git + git@github.com:neo4j/docs-cheat-sheet.git@238ab12a / e11fe2f2
> Generated: 2026-03-20T00:11:34Z
> Files: quantified-path-patterns.adoc (cheat), patterns/variable-length-patterns.adoc (cypher), patterns/shortest-paths.adoc (cypher), patterns/non-linear-patterns.adoc (cypher), patterns/match-modes.adoc (cypher), patterns/variable-length-patterns.adoc (cypher)

## DO-NOT: Common QPE Syntax Errors

```cypher
-- DON'T: bare quantifier on relationship without enclosing node groups — SYNTAX ERROR
MATCH (a:Account)-[:SHARED_IDENTIFIERS]-{2,4}-(b:Account)   -- WRONG

-- DO: enclose the hop pattern in group parentheses
MATCH (a:Account) (()-[:SHARED_IDENTIFIERS]-(){2,4}) (b:Account) RETURN a, b;

-- DON'T: SHORTEST with bare + or {1,} outside group — SYNTAX ERROR
MATCH path = SHORTEST 1 (a)-[:KNOWS]+(b)                    -- WRONG

-- DO: wrap hop in group
MATCH path = SHORTEST 1 (a)(()-[:KNOWS]->()){1,}(b) RETURN path;

-- DON'T: ACYCLIC / SHORTEST with bare quantified relationship — SYNTAX ERROR
MATCH (a:Account)-[:TRANSACTED_TO]-{3,5}->(b:Account)       -- WRONG (no ACYCLIC keyword in Cypher 25)

-- DO: use QPE group syntax
MATCH (a:Account) (()-[:TRANSACTED_TO]->(){3,5}) (b:Account) RETURN a, b;
```

**Rule**: Every quantifier (`{m,n}`, `{1,}`, `{0,}`, `+`, `*`) must attach to a node-pair group `(pattern){q}` or a single relationship in a quantified relationship. Naked `(a)-[:REL]-{m,n}-(b)` without an enclosing node group is always a syntax error.

# Quantified path patterns^

```cypher
((m:Person)-[:KNOWS]->(n:Person) WHERE m.born < n.born){1,5}
```

Paths of between `1` and `5` hops of a `Person` who knows another `Person` younger than them.

```cypher
(n:Person {name: "Alice"})-[:KNOWS]-{1,3}(m:Person)
```

Paths of between `1` and `3` hops of relationship of type `KNOWS` from `Person` with name `Alice` to another `Person`.

```cypher
(n:Person {name: "Christina Ricci"}) (()-[:ACTED_IN]->(:Movie)<-[:ACTED_IN]-(:Person)){1,3} (m:Person)
```

Paths that connect `Christina Ricci` to a `Person`, traversing between `1` and `3` node pairs each consisting of two `Person` nodes with an `ACTED_IN` relationship to the same `Movie`.

```cypher
(n:Person)-[:KNOWS]-{,4}(m:Person)-[:ACTED_IN]->(:Movie)<-[:ACTED_IN]-(:Person {name: "Christina Ricci"})
```

Paths from a `Person` within `4` hops of relationship of type `KNOWS` to a `Person` who `ACTED_IN` the same `Movie` as `Christina Ricci`.

---

# Match Modes

> **Available: Neo4j 2025.06+** — `REPEATABLE ELEMENTS` and `DIFFERENT RELATIONSHIPS` require Cypher 25.

Match modes control how QPE traversal handles repeated elements. They appear between `MATCH` and the pattern:

```cypher
CYPHER 25
MATCH REPEATABLE ELEMENTS (a:Station) (()-[:NEXT]-(){1,3}) (b:Station)
RETURN a.name, b.name
```

| Match Mode | Semantics |
|---|---|
| `DIFFERENT RELATIONSHIPS` (default) | No relationship is traversed more than once per path; nodes MAY be revisited |
| `REPEATABLE ELEMENTS` | Nodes AND relationships may be revisited (cyclic paths allowed); requires **bounded quantifiers** (`{m,n}` only — not `+`, `*`, `{1,}`) |
| `ANY` | Deprecated alias for `REPEATABLE ELEMENTS` |
| `ALL` | Deprecated alias for `DIFFERENT RELATIONSHIPS` |

## When to Use Each Mode

**`DIFFERENT RELATIONSHIPS` (default)** — use when you want acyclic traversals where each relationship is used at most once. This is the standard graph traversal mode and is suitable for most queries (hierarchy traversal, network hop counting, path finding).

```cypher
-- Default: each HAS_SUBSIDIARY relationship traversed once per path
CYPHER 25
MATCH (parent:Organization) (()-[:HAS_SUBSIDIARY]->()){1,3} (child:Organization)
WHERE parent.name CONTAINS 'Comcast'
RETURN parent.name, child.name, COUNT(*) AS pathCount
```

**`REPEATABLE ELEMENTS`** — use when cyclic traversal is intentional or when you want to count all possible walks (including those revisiting nodes/rels). Typical uses: counting all walks of a fixed length, computing redundancy in a network, enumerating all possible routes.

```cypher
-- REPEATABLE ELEMENTS: count ALL walks of exactly 3 hops (including cycles)
CYPHER 25
MATCH REPEATABLE ELEMENTS (a:Account) (()-[:TRANSACTED_TO]->()){3,3} (b:Account)
WHERE a.accountNumber <> b.accountNumber
RETURN a.accountNumber, b.accountNumber, COUNT(*) AS walkCount
ORDER BY walkCount DESC LIMIT 10
```

**Critical**: `REPEATABLE ELEMENTS` REQUIRES bounded quantifiers — `{m,n}` with both m and n specified. The following will fail:

```cypher
-- DON'T: unbounded quantifier with REPEATABLE ELEMENTS — SYNTAX ERROR
MATCH REPEATABLE ELEMENTS (a:Account) (()-[:TRANSACTED_TO]->()){1,} (b:Account)

-- DON'T: + shorthand with REPEATABLE ELEMENTS — SYNTAX ERROR
MATCH REPEATABLE ELEMENTS (a:Account) (()-[:TRANSACTED_TO]->()){1,} (b:Account)

-- DO: bounded {m,n} quantifier — correct
MATCH REPEATABLE ELEMENTS (a:Account) (()-[:TRANSACTED_TO]->()){2,4} (b:Account)
WHERE a.accountNumber <> b.accountNumber
RETURN a.accountNumber, b.accountNumber, COUNT(*) AS walkCount LIMIT 20
```

## DIFFERENT RELATIONSHIPS Example

```cypher
-- Explicit DIFFERENT RELATIONSHIPS: same semantics as default, but explicit for clarity
CYPHER 25
MATCH DIFFERENT RELATIONSHIPS (c1:Customer) (()-[:SHARED_IDENTIFIERS]-()){1,3} (c2:Customer)
WHERE c1.customerID < c2.customerID
RETURN c1.name AS customer1, c2.name AS customer2
LIMIT 20
```

> **Note**: Content truncated to token budget.
