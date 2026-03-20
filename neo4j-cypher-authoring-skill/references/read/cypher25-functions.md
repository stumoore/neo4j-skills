> Source: git@github.com:neo4j/docs-cypher.git + git@github.com:neo4j/docs-cheat-sheet.git@238ab12a / e11fe2f2
> Generated: 2026-03-20T00:11:34Z
> Files: functions/aggregating.adoc (cypher), functions/list.adoc (cypher), functions/string.adoc (cypher), functions/scalar.adoc (cypher), functions/predicate.adoc (cypher), functions/vector.adoc (cypher), functions/mathematical-numeric.adoc (cypher)

# Aggregating functions
## Example graph

The following graph is used for the examples below:

To recreate the graph, run the following query against an empty Neo4j database:

## avg()

| Any `null` values are excluded from the calculation. |
| --- |
| `avg(null)` returns `null`. |

.+avg() - numerical values+

```cypher
MATCH (p:Person)
RETURN avg(p.age)
```

The average of all the values in the property `age` is returned:

.+avg() - duration values+

```cypher
UNWIND [duration('P2DT3H'), duration('PT1H45S')] AS dur
RETURN avg(dur)
```

The average of the two supplied `DURATION` values is returned:

## collect()

| **Syntax** 3+ | `collect(input)` |  |
| --- | --- | --- |
| **Description** 3+ | Returns a list containing the values returned by an expression. |  |
| `input` | `ANY` | A value aggregated into a list. |
| **Returns** 3+ | `LIST<ANY>` |  |

| Any `null` values are ignored and will not be added to the list. |
| --- |
| `collect(null)` returns an empty list. |

.+collect()+

All the values are collected and returned in a single list:

## count()

| **Syntax** 3+ | `count(input)` |  |
| --- | --- | --- |
| **Description** 3+ | Returns the number of values or rows. |  |
| `input` | `ANY` | A value to be aggregated. |
| **Returns** 3+ | `INTEGER` |  |

| `count(*)` includes rows returning `null`. |
| --- |
| `count(input)` ignores `null` values. |
| `count(null)` returns `0`. |

Neo4j maintains a transactional count store for holding count metadata, which can significantly increase the speed of queries using the `count()` function.
For more information about the count store, refer to Neo4j Knowledge Base -> Fast counts using the count store.

### Using `count(*)` to return the number of nodes

The function `count(*)` can be used to return the number of nodes; for example, the number of nodes connected to a node `n`.

.+count()+

The labels and `age` property of the start node `Keanu Reeves` and the number of nodes related to it are returned:

### Using `count(*)` to group and count relationship types

The function `count(*)` can be used to group the type of matched relationships and return the number of types.

.+count()+

The type of matched relationships are grouped and the group count of relationship types is returned:

### Counting non-`null` values

Instead of simply returning the number of rows with `count(*)`, the function `count(expression)` can be used to return the number of non-`null` values returned by the expression.

.+count()+

The number of nodes with the label `Person` and a property `age` is returned:
(To calculate the sum, use `sum(n.age)`)

### Counting with and without duplicates

The default behavior of the `count` function is to count all matching results, including duplicates.
To avoid counting duplicates, use the `DISTINCT` keyword.

It is also possible to use the `ALL` keyword with aggregating functions.
This will count all results, including duplicates, and is functionally the same as not using the `DISTINCT` keyword.
The `ALL` keyword was introduced as part of Cypher's .

This example tries to find all friends of friends of `Keanu Reeves` and count them.
It shows the behavior of using both the `ALL` and the `DISTINCT` keywords:

.+count()+

The nodes `Carrie Anne Moss` and `Liam Neeson` both have an outgoing `KNOWS` relationship to `Guy Pearce`.
The `Guy Pearce` node will, therefore, get counted twice when not using `DISTINCT`.

## max()

| **Syntax** 3+ | `max(input)` |  |
| --- | --- | --- |
| **Description** 3+ | Returns the maximum value in a set of values. |  |
| `input` | `ANY` | A value to be aggregated. |
| **Returns** 3+ | `ANY` |  |

| Any `null` values are excluded from the calculation. |
| --- |
| In a mixed set, any numeric value is always considered to be higher than any `STRING` value, and any `STRING` value is always considered to be higher than any `LIST<ANY>``. |
| Lists are compared in dictionary order, i.e. list elements are compared pairwise in ascending order from the start of the list to the end. |
| `max(null)` returns `null`. |

.+max()+

The highest of all the values in the mixed set -- in this case, the numeric value `1` -- is returned:

The value `'99'` (a `STRING`), is considered to be a lower value than `1` (an `INTEGER`), because `'99'` is a `STRING`.

.+max()+

The highest of all the lists in the set -- in this case, the list `[1, 2]` -- is returned, as the number `2` is considered to be a higher value than the `STRING` `'a'`, even though the list `[1, 'a', 89]` contains more elements.

.+max()+

The highest of all the values in the property `age` is returned:

## min()

| **Syntax** 3+ | `min(input)` |  |
| --- | --- | --- |
| **Description** 3+ | Returns the minimum value in a set of values. |  |
| `input` | `ANY` | A value to be aggregated. |
| **Returns** 3+ | `ANY` |  |

| Any `null` values are excluded from the calculation. |
| --- |
| In a mixed set, any `STRING` value is always considered to be lower than any numeric value, and any `LIST<ANY>` is always considered to be lower than any `STRING`. |
| Lists are compared in dictionary order, i.e. list elements are compared pairwise in ascending order from the start of the list to the end. |
| `min(null)` returns `null`. |

.+min()+

The lowest of all the values in the mixed set -- in this case, the `STRING` value `"1"` -- is returned.
Note that the (numeric) value `0.2`, which may *appear* at first glance to be the lowest value in the list, is considered to be a higher value than `"1"` as the latter is a `STRING`.

.+min()+

The lowest of all the values in the set -- in this case, the list `['a', 'c', 23]` -- is returned, as (i) the two lists are considered to be lower values than the `STRING` `"d"`, and (ii) the `STRING` `"a"` is considered to be a lower value than the numerical value `1`.

.+min()+

The lowest of all the values in the property `age` is returned:

## percentileCont()

| **Syntax** 3+ | `percentileCont(input, percentile)` |  |
| --- | --- | --- |
| **Description** 3+ | Returns the percentile of a value over a group using linear interpolation. |  |
| `input` | `FLOAT` | A value to be aggregated. |
| `percentile` | `FLOAT` | A percentile between 0.0 and 1.0. |
| **Returns** 3+ | `FLOAT` |  |

| Any `null` values are excluded from the calculation. |
| --- |
| `percentileCont(null, percentile)` returns `null`. |

.+percentileCont()+

The 40th percentile of the values in the property `age` is returned, calculated with a weighted average:

## percentileDisc()

| **Syntax** 3+ | `percentileDisc(input, percentile)` |  |  |
| --- | --- | --- | --- |
| **Description** 3+ | Returns the nearest `INTEGER` or `FLOAT` value to the given percentile over a group using a rounding method. |  |  |
| `input` | `INTEGER \ | FLOAT` | A value to be aggregated. |
| `percentile` | `FLOAT` | A percentile between 0.0 and 1.0. |  |
| **Returns** 3+ | `INTEGER \ | FLOAT` |  |

| Any `null` values are excluded from the calculation. |
| --- |
| `percentileDisc(null, percentile)` returns `null`. |

.+percentileDisc()+

The 50th percentile of the values in the property `age` is returned:

## stDev()

| **Syntax** 3+ | `stDev(input)` |  |
| --- | --- | --- |
| **Description** 3+ | Returns the standard deviation for the given value over a group for a sample of a population. |  |
| `input` | `FLOAT` | The value to calculate the standard deviation of. |
| **Returns** 3+ | `FLOAT` |  |

> **Note**: Content truncated to token budget.
