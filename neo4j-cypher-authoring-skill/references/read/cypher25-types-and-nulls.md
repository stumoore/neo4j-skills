> Source: git@github.com:neo4j/docs-cypher.git + git@github.com:neo4j/docs-cheat-sheet.git@238ab12a / e11fe2f2
> Generated: 2026-03-20T00:11:34Z
> Files: values-and-types/working-with-null.adoc (cypher), values-and-types/casting-data.adoc (cypher), values-and-types/property-structural-constructed.adoc (cypher), expressions/predicates/type-predicate-expressions.adoc (cypher)

# Working with `null`
## Logical operations with `null`

The boolean operators (`AND`, `OR`, `XOR`, `NOT`) treat `null` as the ***unknown value*** of three-valued logic.

| a | b | a `AND` b | a `OR` b | a `XOR` b | `NOT` a |
| --- | --- | --- | --- | --- | --- |
| `false` | `false` | `false` | `false` | `false` | `true` |
| `false` | `null` | `false` | `null` | `null` | `true` |
| `false` | `true` | `false` | `true` | `true` | `true` |
| `true` | `false` | `false` | `true` | `true` | `false` |
| `true` | `null` | `null` | `true` | `null` | `false` |
| `true` | `true` | `true` | `true` | `false` | `false` |
| `null` | `false` | `false` | `null` | `null` | `null` |
| `null` | `null` | `null` | `null` | `null` | `null` |
| `null` | `true` | `null` | `true` | `null` | `null` |

## The `IN` operator and `null`

The `IN` operator follows similar logic.
If Cypher can ascertain that something exists in a list, the result will be `true`.
Any list that contains a `null` and does not have a matching element will return `null`.
Otherwise, the result will be `false`.

| Expression | Result |
| --- | --- |
| 2 IN [1, 2, 3] | true |
| 2 IN [1, null, 3] | null |
| 2 IN [1, 2, null] | true |
| 2 IN [1] | false |
| 2 IN [] | false |
| null IN [1, 2, 3] | null |
| null IN [1, null, 3] | null |
| null IN [] | false |

Using `all`, `any`, `none`, and `single` follows a similar rule.
If the result can be calculated definitively, `true` or `false` is returned.
Otherwise `null` is produced.

## The `[]` operator and `null`

Accessing a list or a map with `null` will result in `null`:

| Expression | Result |
| --- | --- |
| [1, 2, 3][null] | null |
| [1, 2, 3, 4][null..2] | null |
| [1, 2, 3][1..null] | null |
| {age: 25}[null] | null |

Using parameters to pass in the bounds, such as `a[$lower..$upper]`, may result in a `null` for the lower or upper bound (or both).
The following workaround will prevent this from happening by setting the absolute minimum and maximum bound values:
```syntax
a[coalesce($lower,0)..coalesce($upper,size(a))]
```

## Expressions that return `null`

* Getting a missing element from a list: `[][0]`, `head([])`.
* Trying to access a property that does not exist on a node or relationship: `n.missingProperty`.
* Comparisons when either side is `null`: `1 < null`.
* Arithmetic expressions containing `null`: `1 + null`.
* Some function calls where any argument is `null`: e.g., `sin(null)`.

## Using `IS NULL` and `IS NOT NULL`
Testing any value against `null`, either with the `=` operator or with the `<>` operator, always evaluates to `null`.
Therefore,  use the special equality operators `IS NULL` or `IS NOT NULL`.

---

# Casting data values
## Functions for converting data values

The following functions are available for casting data values:

| Function | Description |
| --- | --- |
| `toBoolean()` | Converts a `STRING`, `INTEGER`, or `BOOLEAN` value to a `BOOLEAN` value. |
| toBooleanList() | Converts a `LIST<ANY>` and returns a `LIST<BOOLEAN>` values. |
| toBooleanOrNull() | Converts a `STRING`, `INTEGER` or `BOOLEAN` value to a `BOOLEAN` value. |
| toFloat() | Converts an `INTEGER`, `FLOAT`, or a `STRING` value to a `FLOAT` value. |
| toFloatList() | Converts a `LIST<ANY>` or, as of Neo4j 2025.10, additionally `VECTOR` and returns a `LIST<FLOAT>` values. |
| toFloatOrNull() | Converts an `INTEGER`, `FLOAT`, or a `STRING` value to a `FLOAT`. |
| toInteger() | Converts a `BOOLEAN`, `INTEGER`, `FLOAT` or a `STRING` value to an `INTEGER` value. |
| toIntegerList() | Converts a `LIST<ANY>` or, as of Neo4j 2025.10, additionally `VECTOR` to a `LIST<INTEGER>` values. If any values are not convertible to `INTEGER` they will be null in the `LIST<INTEGER>` returned. |
| toIntegerOrNull() | Converts a `BOOLEAN`, `INTEGER`, `FLOAT` or a `STRING` value to an `INTEGER` value. |
| toString() | Converts an `INTEGER`, `FLOAT`, `BOOLEAN`, `STRING`, `POINT`, `DURATION`, `DATE`, `ZONED TIME`, `LOCAL TIME`, `LOCAL DATETIME`, or `ZONED DATETIME` value to a `STRING` value. |
| toStringList() | Converts a `LIST<ANY>` and returns a `LIST<STRING>` values. |
| toStringOrNull() | Converts an `INTEGER`, `FLOAT`, `BOOLEAN`, `STRING`, `POINT`, `DURATION`, `DATE`, `ZONED TIME`, `LOCAL TIME`, `LOCAL DATETIME`, or `ZONED DATETIME` value to a `STRING`. |

More information about these, and many other functions, can be found in the section on .

## Examples

The following graph is used for the examples below:

To recreate it, run the following query against an empty Neo4j database:

```cypher
CREATE (keanu:Person {name:'Keanu Reeves', age: 58, active:true}),
       (carrieAnne:Person  {name:'Carrie-Anne Moss', age: 55, active:true}),
       (keanu)-[r:KNOWS {since:1999}]->(carrieAnne)
```

### Returning converted values

In the below query, the function `toFloat` is used to cast two `STRING` values.
It shows that `null` is returned if the data casting is not possible.

```cypher
MATCH (keanu:Person {name:'Keanu Reeves'})
RETURN toFloat(keanu.age), toInteger(keanu.name)
```

If the function `toFloat` is passed an unsupported value (such as a `DATE` value), it will throw an error:

However, if the same value is passed to the function `toFloatOrNull`, `null` will be returned.

It is also possible to return casted values as a list.
The below query uses the `toStringList` to cast all passed values into `STRING` values, and return them in as a `LIST<STRING>`:

### Updating property value types

The functions to cast data values can be used to update property values on nodes and relationships.
The below query casts the `age` (`INTEGER`), `active` (`BOOLEAN`), and `since`(`INTEGER`) properties to `STRING` values:

---

# Property, structural, and constructed values
## Property types

A property type value is one that can be stored as a node or relationship property.

Property types are the most primitive types in Cypher and include the following: `BOOLEAN`, `DATE`, `DURATION`, `FLOAT`, `INTEGER`, `LIST`, `LOCAL DATETIME`, `LOCAL TIME`, `POINT`, `STRING`, `VECTOR`, `ZONED DATETIME`, and `ZONED TIME`.

* Property types can be returned from Cypher queries.
* Property types can be used as parameters.
* Property types can be stored as properties.
* Property types can be constructed with Cypher literals.

Homogeneous lists of simple types can be stored as properties (with the exeption of `VECTOR` types, which cannot be stored in lists), although lists in general (see Constructed types) cannot be stored as properties.
Lists stored as properties cannot contain `null` values.

Storing `VECTOR` type values as properties is only supported in the Neo4j Enterprise Edition using block format or on Aura instances. This functionality is not available in Neo4j Community Edition.

Cypher also provides pass-through support for byte arrays, which can be stored as property values.
Byte arrays are supported for performance reasons, since using Cypher's generic data type, `LIST<INTEGER>` (where each `INTEGER` has a 64-bit representation), would be too costly.
However, byte arrays are *not* considered a first class data type by Cypher, so they do not have a literal representation.

## Structural types

The following data types are included in the structural types category: `NODE`, `RELATIONSHIP`, and `PATH`.

* Structural types can be returned from Cypher queries.
* Structural types cannot be used as parameters.
* Structural types cannot be stored as properties.
* Structural types cannot be constructed with Cypher literals.

> **Note**: Content truncated to token budget.
