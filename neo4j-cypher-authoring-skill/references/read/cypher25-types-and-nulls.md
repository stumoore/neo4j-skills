> Source: git@github.com:neo4j/docs-cypher.git@238ab12a
> Generated: 2026-03-20T00:11:34Z — manually curated
> Files: values-and-types/working-with-null.adoc, values-and-types/casting-data.adoc, values-and-types/property-structural-constructed.adoc, expressions/predicates/type-predicate-expressions.adoc

# Cypher 25 — Types and Nulls

## Type hierarchy (quick reference)

| Category | Types |
|---|---|
| **Property** (storable) | `BOOLEAN`, `INTEGER`, `FLOAT`, `STRING`, `DATE`, `LOCAL DATETIME`, `ZONED DATETIME`, `LOCAL TIME`, `ZONED TIME`, `DURATION`, `POINT`, `VECTOR`, `LIST<T>` (homogeneous, no nulls) |
| **Structural** (not storable) | `NODE`, `RELATIONSHIP`, `PATH` |
| **Constructed** | `MAP`, `LIST<ANY>` (heterogeneous) |
| **Special** | `NULL`, `ANY` (supertype), `NOTHING` (empty set) |

## Null propagation rules

**Core rule:** `null` represents a missing/unknown value. Most expressions propagate `null` when any input is `null`.

| Context | Result |
|---|---|
| Arithmetic: `1 + null` | `null` |
| Comparison: `1 < null` | `null` |
| Missing property: `n.missingProp` | `null` |
| Missing list element: `[][0]`, `head([])` | `null` |
| `null = null` | `null` (not `true`) |
| `null <> null` | `null` |
| `NOT null` | `null` |

**WHERE clause:** anything that is not `true` (including `null`) is treated as `false` — rows with null predicates are filtered out.

### Logical operators (three-valued logic)

| a | b | AND | OR | XOR | NOT a |
|---|---|---|---|---|---|
| `false` | `null` | `false` | `null` | `null` | `true` |
| `true` | `null` | `null` | `true` | `null` | `false` |
| `null` | `null` | `null` | `null` | `null` | `null` |

### IN operator and null

| Expression | Result |
|---|---|
| `2 IN [1, null, 3]` | `null` |
| `2 IN [1, 2, null]` | `true` |
| `null IN [1, 2, 3]` | `null` |
| `null IN []` | `false` |

### [] accessor and null

| Expression | Result |
|---|---|
| `[1,2,3][null]` | `null` |
| `{age:25}[null]` | `null` |

Workaround for nullable bounds: `a[coalesce($lower,0)..coalesce($upper,size(a))]`

## IS NULL / IS NOT NULL

**Never use `= null` or `<> null`** — both always return `null`.
Use the dedicated operators:

```cypher
MATCH (n:Person)
WHERE n.email IS NOT NULL
RETURN n.name, n.email
```

```cypher
MATCH (n:Person)
WHERE n.phone IS NULL
RETURN n.name
```

## coalesce()

Returns the first non-null value from its arguments. Signature: `coalesce(expr [, expr]...) → ANY`.

```cypher
MATCH (n:Person)
RETURN n.name, coalesce(n.nickname, n.name) AS displayName
```

- Evaluates arguments left to right, returns first non-null
- Returns `null` if all arguments are `null`

## Casting functions

All casting functions return `null` when input cannot be converted (OrNull variants) or throw an error (base variants).

| Function | Input types | Returns | On unconvertible |
|---|---|---|---|
| `toBoolean(x)` | `STRING`, `INTEGER`, `BOOLEAN` | `BOOLEAN` | error |
| `toBooleanOrNull(x)` | any | `BOOLEAN` | `null` |
| `toInteger(x)` | `BOOLEAN`, `INTEGER`, `FLOAT`, `STRING` | `INTEGER` | error |
| `toIntegerOrNull(x)` | any | `INTEGER` | `null` |
| `toFloat(x)` | `INTEGER`, `FLOAT`, `STRING` | `FLOAT` | error |
| `toFloatOrNull(x)` | any | `FLOAT` | `null` |
| `toString(x)` | `INTEGER`, `FLOAT`, `BOOLEAN`, `STRING`, `POINT`, `DURATION`, all temporal | `STRING` | error |
| `toStringOrNull(x)` | any | `STRING` | `null` |
| `date(x)` | `STRING` (ISO 8601), `MAP`, `DATE` | `DATE` | error |
| `datetime(x)` | `STRING`, `MAP`, temporal | `ZONED DATETIME` | error |
| `localdatetime(x)` | `STRING`, `MAP`, temporal | `LOCAL DATETIME` | error |
| `time(x)` | `STRING`, `MAP`, temporal | `ZONED TIME` | error |
| `localtime(x)` | `STRING`, `MAP`, temporal | `LOCAL TIME` | error |
| `duration(x)` | `STRING` (ISO 8601), `MAP` | `DURATION` | error |

List variants: `toBooleanList()`, `toIntegerList()`, `toFloatList()`, `toStringList()` — convert `LIST<ANY>`, nulls in input become nulls in output.

## Type predicate expressions

Syntax: `<expr> IS :: <TYPE>` — returns `BOOLEAN`.

**Key rule:** All Cypher types include `null`. `IS :: TYPE` returns `true` for `null` unless `NOT NULL` is appended.

```cypher
-- Basic type check
UNWIND [42, true, 'abc', null] AS val
RETURN val, val IS :: INTEGER AS isInt
-- Results: true, false, false, true  ← null matches any type
```

```cypher
-- Exclude null: append NOT NULL
RETURN NULL IS :: BOOLEAN NOT NULL AS isNotNullBoolean
-- Result: false
```

```cypher
-- Negation
RETURN val IS NOT :: STRING AS notString
-- null → false (null is "not not a string"? no — null matches all, so IS NOT :: returns false for null)
```

### NOT NULL suffix

| Expression | null result | non-null result |
|---|---|---|
| `x IS :: INTEGER` | `true` | `true` if INTEGER, else `false` |
| `x IS :: INTEGER NOT NULL` | `false` | `true` if INTEGER, else `false` |
| `x IS NOT :: STRING` | `false` | `true` if not STRING, else `false` |
| `x IS NOT :: STRING NOT NULL` | `true` | `true` if not STRING, else `false` |

### Closed Dynamic Unions

Test multiple types in one predicate using `|`:

```cypher
UNWIND [42, 42.0, "42"] AS val
RETURN val, val IS :: INTEGER | FLOAT AS isNumber
-- Results: true, true, false
```

All inner types must have the same nullability (all nullable or all `NOT NULL`).

### List type predicates

```cypher
-- All elements must match the inner type
RETURN [42, null] IS :: LIST<INTEGER> AS ok  -- true (null allowed)
RETURN [42, 42.0] IS :: LIST<INTEGER> AS ok  -- false (FLOAT ≠ INTEGER)
RETURN [] IS :: LIST<NOTHING> AS ok          -- true (empty matches any)
```

### Alternative syntax

```cypher
x IS TYPED INTEGER       -- same as IS :: INTEGER
x IS NOT TYPED INTEGER   -- same as IS NOT :: INTEGER
x :: INTEGER             -- shorthand (same semantics)
```

### Type predicate for property filtering

```cypher
MATCH (n:Person)
WHERE n.age IS :: INTEGER AND n.age > 18
RETURN n.name, n.age
-- Only returns nodes where age is an INTEGER (filters out STRING ages)
```

### Special types ANY and NOTHING

```cypher
RETURN 42 IS :: ANY AS t     -- true (ALL values match ANY)
RETURN 42 IS :: NOTHING AS t -- false (no value matches NOTHING)
```

### PROPERTY VALUE type

```cypher
-- Check if storable as a property
RETURN {a:1} IS :: PROPERTY VALUE AS ok  -- false (MAP not storable)
RETURN 42 IS :: PROPERTY VALUE AS ok     -- true
```

## Common agent pitfalls

| Mistake | Correct pattern |
|---|---|
| `WHERE n.x = null` | `WHERE n.x IS NULL` |
| `WHERE n.x <> null` | `WHERE n.x IS NOT NULL` |
| `toFloat('abc')` (crashes) | `toFloatOrNull('abc')` |
| Casting DATE to FLOAT | Use `toString(date_val)` first |
| `IS :: INTEGER` accepts null | Append `NOT NULL` to exclude null |
