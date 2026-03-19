> Source: git@github.com:neo4j/docs-cypher.git@238ab12a / git@github.com:neo4j/docs-cheat-sheet.git@e11fe2f2
> Generated: 2026-03-20T00:00:00Z
> Files: functions/aggregating.adoc, functions/list.adoc, functions/string.adoc, functions/scalar.adoc, functions/predicate.adoc, functions/mathematical-numeric.adoc, functions/spatial.adoc, functions/temporal/index.adoc, functions/vector.adoc

## Aggregating Functions

Aggregating functions collapse multiple rows into a single value. All **ignore `null`** unless otherwise noted.

| Function | Returns | Null behavior |
| --- | --- | --- |
| `avg(expr)` | `INTEGER \| FLOAT \| DURATION` | nulls excluded; returns `null` if all null |
| `collect(expr)` | `LIST<ANY>` | nulls **dropped** from list; `collect(null)` → `[]` |
| `count(*)` | `INTEGER` | counts all rows **including** null rows |
| `count(expr)` | `INTEGER` | ignores nulls; `count(null)` → `0` |
| `max(expr)` | `ANY` | nulls excluded |
| `min(expr)` | `ANY` | nulls excluded |
| `sum(expr)` | `INTEGER \| FLOAT \| DURATION` | nulls excluded; `sum(null)` → `0` |
| `stDev(expr)` | `FLOAT` | sample std dev (N-1 denominator) |
| `stDevP(expr)` | `FLOAT` | population std dev (N denominator) |
| `percentileCont(expr, pct)` | `FLOAT` | linear interpolation; `pct` in [0.0, 1.0] |
| `percentileDisc(expr, pct)` | `ANY` | nearest value; `pct` in [0.0, 1.0] |

Use `DISTINCT` inside aggregating functions to deduplicate before aggregation:

```cypher
RETURN count(DISTINCT n.country) AS countries, collect(DISTINCT n.tag) AS tags
```

## List Functions

| Function | Signature | Returns |
| --- | --- | --- |
| `keys()` | `keys(node \| rel \| map)` | `LIST<STRING>` — property names |
| `labels()` | `labels(node)` | `LIST<STRING>` — node labels |
| `nodes()` | `nodes(path)` | `LIST<NODE>` |
| `relationships()` | `relationships(path)` | `LIST<RELATIONSHIP>` |
| `range()` | `range(start, end [, step])` | `LIST<INTEGER>` inclusive arithmetic progression |
| `reverse()` | `reverse(list)` | `LIST<ANY>` reversed |
| `tail()` | `tail(list)` | `LIST<ANY>` — all but first element |
| `head()` | `head(list)` | `ANY` — first element; `null` if empty |
| `last()` | `last(list)` | `ANY` — last element; `null` if empty |
| `reduce()` | `reduce(acc = init, x IN list \| expr)` | accumulated value |
| `toBooleanList()` | `toBooleanList(list)` | `LIST<BOOLEAN>` — non-convertible → `null` |
| `toFloatList()` | `toFloatList(list)` | `LIST<FLOAT>` — non-convertible → `null` |
| `toIntegerList()` | `toIntegerList(list)` | `LIST<INTEGER>` — non-convertible → `null` |
| `toStringList()` | `toStringList(list)` | `LIST<STRING>` — non-convertible → `null` |

**List comprehension** (not a function, but commonly used alongside):
```cypher
[x IN list WHERE x > 0 | x * 2]
```

## String Functions

All string functions return `null` when input is `null`.

| Function | Signature | Returns |
| --- | --- | --- |
| `toLower()` | `toLower(str)` | `STRING` lowercase (alias: `lower()`) |
| `toUpper()` | `toUpper(str)` | `STRING` uppercase (alias: `upper()`) |
| `trim()` | `trim(str)` | `STRING` strip leading/trailing whitespace |
| `ltrim()` | `ltrim(str [, chars])` | `STRING` strip leading chars |
| `rtrim()` | `rtrim(str [, chars])` | `STRING` strip trailing chars |
| `btrim()` | `btrim(str [, chars])` | `STRING` strip both ends |
| `left()` | `left(str, n)` | `STRING` first n characters |
| `right()` | `right(str, n)` | `STRING` last n characters |
| `substring()` | `substring(str, start [, length])` | `STRING` zero-based |
| `replace()` | `replace(str, search, replacement)` | `STRING` |
| `split()` | `split(str, delimiter)` | `LIST<STRING>` |
| `reverse()` | `reverse(str)` | `STRING` |
| `toString()` | `toString(expr)` | `STRING` — converts INTEGER/FLOAT/BOOL/POINT/temporal |
| `toStringOrNull()` | `toStringOrNull(expr)` | `STRING \| null` — returns `null` for unsupported types |
| `normalize()` | `normalize(str [, form])` | `STRING` Unicode NFC normalization |

## Scalar Functions

| Function | Signature | Returns |
| --- | --- | --- |
| `coalesce()` | `coalesce(expr, ...)` | First non-null value; `null` if all null |
| `elementId()` | `elementId(node \| rel)` | `STRING` stable only within transaction |
| `size()` | `size(str \| list)` | `INTEGER` char count or list length |
| `char_length()` | `char_length(str)` | `INTEGER` alias for `size()` on strings |
| `type()` | `type(rel)` | `STRING` relationship type name |
| `startNode()` | `startNode(rel)` | `NODE` |
| `endNode()` | `endNode(rel)` | `NODE` |
| `length()` | `length(path)` | `INTEGER` number of relationships in path |
| `properties()` | `properties(node \| rel \| map)` | `MAP` of all properties |
| `id()` | `id(node \| rel)` | `INTEGER` internal id (deprecated — prefer `elementId()`) |

## Predicate Functions

All return `BOOLEAN`. Return `null` when input list is `null` or predicate is `null` for some element without being `false` elsewhere.

| Function | Signature |
| --- | --- |
| `all()` | `all(x IN list WHERE predicate)` — `true` if predicate holds for every element |
| `any()` | `any(x IN list WHERE predicate)` — `true` if predicate holds for at least one |
| `none()` | `none(x IN list WHERE predicate)` — `true` if predicate holds for no element |
| `single()` | `single(x IN list WHERE predicate)` — `true` if predicate holds for exactly one |
| `exists()` | `exists(pattern)` — `true` if pattern exists in graph |
| `isEmpty()` | `isEmpty(list \| string)` — `true` if empty; **not** suited for null checks (`null` → `null`) |

## Mathematical Functions

**Numeric**: `abs(n)` → `INTEGER|FLOAT`, `ceil(n)` → `FLOAT`, `floor(n)` → `FLOAT`, `round(n [, precision [, mode]])` → `FLOAT`, `sign(n)` → `-1|0|1`, `rand()` → `FLOAT` in [0,1), `isNaN(n)` → `BOOLEAN`

**Logarithmic**: `sqrt(n)`, `log(n)`, `log10(n)`, `exp(n)`, `e()` → `FLOAT`

**Trigonometric** (radians): `sin(r)`, `cos(r)`, `tan(r)`, `asin(r)`, `acos(r)`, `atan(r)`, `atan2(y,x)`, `pi()`, `degrees(r)`, `radians(d)` → `FLOAT`

## Temporal Functions

| Function | Returns |
| --- | --- |
| `date([string \| map])` | `DATE` |
| `datetime([string \| map])` | `ZONED DATETIME` |
| `localdatetime([string \| map])` | `LOCAL DATETIME` |
| `localtime([string \| map])` | `LOCAL TIME` |
| `time([string \| map])` | `ZONED TIME` |
| `duration(map \| string)` | `DURATION` |
| `date.realtime()` / `date.statement()` / `date.transaction()` | Current `DATE` by clock type |
| `date.truncate(unit, temporal)` | `DATE` truncated to unit |
| `datetime.fromEpoch(seconds, nanos)` | `ZONED DATETIME` |

Temporal string format: ISO 8601 — `"2026-03-20"`, `"2026-03-20T12:34:56Z"`, `"P1Y2M3D"`.

## Spatial Functions

| Function | Signature | Returns |
| --- | --- | --- |
| `point()` | `point({latitude, longitude})` or `point({x, y})` | `POINT` (WGS-84 or Cartesian) |
| `point.distance()` | `point.distance(p1, p2)` | `FLOAT` — distance in metres (WGS-84) or units (Cartesian) |
| `point.withinBBox()` | `point.withinBBox(p, lowerLeft, upperRight)` | `BOOLEAN` |

3D: `point({x, y, z})` or `point({latitude, longitude, height})`.

## Vector Functions

| Function | Signature | Returns |
| --- | --- | --- |
| `vector()` | `vector(values, dimension, coordType)` | `VECTOR` — new in Neo4j 2025.10 |
| `vector.similarity.cosine()` | `vector.similarity.cosine(a, b)` | `FLOAT` in [0,1]; `null` if either arg is `null` |
| `vector.similarity.euclidean()` | `vector.similarity.euclidean(a, b)` | `FLOAT` in [0,1]; `null` if either arg is `null` |
| `vector_dimension_count()` | `vector_dimension_count(v)` | `INTEGER` — dimension of vector |

Coordinate types: `INTEGER64`, `INTEGER32`, `INTEGER16`, `INTEGER8`, `FLOAT64`, `FLOAT32`.
