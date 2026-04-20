# Cypher 25 new features (vs Cypher 5)

Everything here is **additive** over Cypher 5 and only available under `CYPHER 25`.

## Vector type and functions

First-class vector value type:

```cypher
CREATE (m:Movie {title: "Matrix",
                 embedding: vector([0.1, 0.2, 0.3], 3, FLOAT32)})
```

Functions: `vector()`, `vector_distance(a, b, 'cosine'|'euclidean')`, `vector_norm(v)`, `vector_dimension_count(v)`.

Vector indexes now support **multiple labels / rel-types and filter properties**:

```cypher
CREATE VECTOR INDEX movie_emb FOR (m:Movie|Show) ON (m.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};
```

Vector-similarity search in `MATCH`:

```cypher
MATCH (m:Movie) SEARCH m.embedding NEAREST $query_vec LIMIT 10
RETURN m.title;
```

## Dynamic labels and relationship types

Native, no APOC needed:

```cypher
WITH 'Person' AS lbl, 'KNOWS' AS rel
MATCH (a:$(lbl) {name: 'Alice'})-[:$(rel)]->(b)
RETURN b;
```

Works in `MATCH`, `MERGE`, `CREATE`, `SET`, `REMOVE`.

## Conditional subqueries

```cypher
MATCH (p:Person {id: $id})
CALL {
  WITH p
  WHEN p.age >= 18 THEN
    CREATE (p)-[:IS]->(:Adult)
  ELSE
    CREATE (p)-[:IS]->(:Minor)
}
RETURN p;
```

## Collection functions (namespaced)

| Function           | Purpose                          |
|--------------------|----------------------------------|
| `coll.sort(list)`  | sorted copy                      |
| `coll.distinct(list)` | dedupe preserving order       |
| `coll.flatten(list)`  | one-level flatten             |
| `coll.max(list)` / `coll.min(list)` | extremes        |
| `coll.indexOf(list, x)` | first index of `x`          |
| `coll.insert(list, idx, x)` | insert at idx           |
| `coll.remove(list, idx)` | remove at idx              |

## GQL-style composition

```cypher
LET doubled = [x IN $nums | x * 2]
FILTER doubled > 10
NEXT
RETURN doubled;
```

- `LET` binds a value to a variable (like `WITH … AS …` but single-binding).
- `FILTER` is a standalone filtering clause.
- `NEXT` chains a subsequent statement without `WITH`.
- `RETURN ALL` / `WITH ALL` — explicit non-deduped projection.

## Walk semantics in `MATCH`

```cypher
MATCH REPEATABLE ELEMENTS p = (a)-[*..5]-(b)
WHERE a.name = 'Alice' AND b.name = 'Bob'
RETURN p;
```

`REPEATABLE ELEMENTS` allows the same relationship to appear more than once in a path (walk semantics). `DIFFERENT RELATIONSHIPS` (the default) matches Cypher 5 behavior.

## Temporal formatting

```cypher
RETURN format(datetime(), 'yyyy-MM-dd HH:mm:ss zzz') AS stamp;
```

Temporal constructors accept an optional pattern argument for parsing.

## Miscellaneous additions

- **Read→write without `WITH`**: `MATCH (p:Person) CREATE (p)-[:OWNS]->(:Pet {name:'Rex'})` is legal.
- **Parameters starting with a digit**: `$0user`, `$42`.
- **Parameters in `SHORTEST k`/`ANY` path selectors**: `MATCH p = SHORTEST $k (a)-[*]-(b)`.
- **`replace(str, from, to, limit)`** — optional `limit` argument.
- **`PROPERTY_EXISTS(element, 'name')`** — direct property existence check.
- **Hyperbolic trig**: `sinh`, `cosh`, `tanh`, `coth`.
- **GQL naming aliases** (same semantics, SQL/GQL-style names): `ceiling`, `ln`, `local_time`, `local_datetime`, `zoned_time`, `zoned_datetime`, `duration_between`, `path_length`, `collect_list`, `percentile_cont`, `percentile_disc`, `stdev_samp`, `stdev_pop`.
- **`allReduce(path, accumulator, expr)`** — stepwise path evaluation for planning/routing problems.
- **`SHOW TRANSACTIONS`** now exposes `currentQueryProgress`.
- **`SHOW CONSTRAINTS`** gains `enforcedLabel` and `classification` columns.
- **Imported variables are constants** inside `COLLECT { … }`, `COUNT { … }`, `EXISTS { … }` subqueries — no more surprise re-binding.

## New constraint kinds

```cypher
CREATE CONSTRAINT person_label_exists
FOR (n:Person) REQUIRE n:Person IS NODE LABEL EXISTENCE;

CREATE CONSTRAINT knows_source
FOR ()-[r:KNOWS]-() REQUIRE (r) IS RELATIONSHIP SOURCE LABEL Person;

CREATE CONSTRAINT knows_target
FOR ()-[r:KNOWS]-() REQUIRE (r) IS RELATIONSHIP TARGET LABEL Person;
```

## Graph type system (preview)

```cypher
SHOW CURRENT GRAPH TYPE;
ALTER CURRENT GRAPH TYPE ADD NODE (:Person {name: STRING});
```

Preview feature — the syntax may still evolve inside Cypher 25's additive window.
