> Source: git@github.com:neo4j/docs-cypher.git + git@github.com:neo4j/docs-cheat-sheet.git@238ab12a / e11fe2f2
> Generated: 2026-03-19T22:58:50Z
> Files: patterns/variable-length-patterns.adoc (cypher), patterns/shortest-paths.adoc (cypher), patterns/non-linear-patterns.adoc (cypher), patterns/match-modes.adoc (cypher), quantified-path-patterns.adoc (cheat), path-pattern-expressions.adoc (cheat)

# Variable-length patterns

Cypher can be used to match patterns of a variable or an unknown length.
Such patterns can be found using quantified path patterns and quantified relationships.
This page also discusses how variables work when declared in quantified path patterns (group variables), and how to use predicates in quantified path patterns.

## Quantified path patterns 

This section considers how to match paths of *varying* length by using *quantified path patterns*, allowing you to search for paths whose lengths are unknown or within a specific range.

Quantified path patterns can be useful when, for example, searching for all nodes that can be reached from an anchor node, finding all paths connecting two nodes, or when traversing a hierarchy that may have differing depths.

This example uses a new graph:

To recreate the graph, run the following query against an empty Neo4j database:

```cypher
CREATE (pmr:Station {name: 'Peckham Rye'}),
  (dmk:Station {name: 'Denmark Hill'}),
  (clp:Station {name: 'Clapham High Street'}),
  (wwr:Station {name: 'Wandsworth Road'}),
  (clj:Station {name: 'Clapham Junction'}),
  (s1:Stop {arrives: time('17:19'), departs: time('17:20')}),
  (s2:Stop {arrives: time('17:12'), departs: time('17:13')}),
  (s3:Stop {arrives: time('17:10'), departs: time('17:11')}),
  (s4:Stop {arrives: time('17:06'), departs: time('17:07')}),
  (s5:Stop {arrives: time('16:58'), departs: time('17:01')}),
  (s6:Stop {arrives: time('17:17'), departs: time('17:20')}),
  (s7:Stop {arrives: time('17:08'), departs: time('17:10')}),
  (clj)<-[:CALLS_AT]-(s1), (wwr)<-[:CALLS_AT]-(s2),
  (clp)<-[:CALLS_AT]-(s3), (dmk)<-[:CALLS_AT]-(s4),
  (pmr)<-[:CALLS_AT]-(s5), (clj)<-[:CALLS_AT]-(s6),
  (dmk)<-[:CALLS_AT]-(s7),
  (s5)-[:NEXT {distance: 1.2}]->(s4),(s4)-[:NEXT {distance: 0.34}]->(s3),
  (s3)-[:NEXT {distance: 0.76}]->(s2), (s2)-[:NEXT {distance: 0.3}]->(s1),
  (s7)-[:NEXT {distance: 1.4}]->(s6)
```

Each `Stop` on a service `CALLS_AT` one `Station`.
Each `Stop` has the properties `arrives` and `departs` that give the times the train is at the `Station`.
Following the `NEXT` relationship of a `Stop` will give the next `Stop` of the service.

For this example, a path pattern is constructed to match each of the services that allow passengers to travel from `Denmark Hill` to `Clapham Junction`.
The following shows the two paths that the path pattern should match:

The following motif represents a fixed-length path pattern that matches the service that departs from `Denmark Hill` station at `17:07`:

To match the second train service, leaving `Denmark Hill` at `17:10`, a shorter path pattern is needed:

Translating the motifs into Cypher, and adding predicates to match the origin and destination `Stations`, yields the following two path patterns respectively:

```
(:Station { name: 'Denmark Hill' })<-[:CALLS_AT]-(:Stop)
  -[:NEXT]->(:Stop)
  -[:NEXT]->(:Stop)
  -[:NEXT]->(:Stop)-[:CALLS_AT]->
(:Station { name: 'Clapham Junction' })
```

```
(:Station { name: 'Denmark Hill' })<-[:CALLS_AT]-(:Stop)
  -[:NEXT]->(:Stop)-[:CALLS_AT]->
(:Station { name: 'Clapham Junction' })
```

To return both solutions in the same query using these fixed-length path patterns, a UNION of two `MATCH` statements would be needed.
For example, the following query returns the `departure` of the two services:

```cypher
MATCH (:Station { name: 'Denmark Hill' })<-[:CALLS_AT]-(d:Stop)
        -[:NEXT]->(:Stop)
        -[:NEXT]->(:Stop)
        -[:NEXT]->(a:Stop)-[:CALLS_AT]->
      (:Station { name: 'Clapham Junction' })
RETURN d.departs AS departureTime, a.arrives AS arrivalTime
UNION
MATCH (:Station { name: 'Denmark Hill' })<-[:CALLS_AT]-(d:Stop)
        -[:NEXT]->(a:Stop)-[:CALLS_AT]->
      (:Station { name: 'Clapham Junction' })
RETURN d.departs AS departureTime, a.arrives AS arrivalTime
```

| departureTime | arrivalTime |
| --- | --- |
| "17:07:00Z" | "17:19:00Z" |
| "17:10:00Z" | "17:17:00Z" |

The problem with this solution is that not only is it verbose, it can only be used where the lengths of the target paths are known in advance.
Quantified path patterns solve this problem by extracting repeating parts of a path pattern into parentheses and applying a **quantifier**.
That quantifier specifies a range of possible repetitions of the extracted pattern to match on.
For the current example, the first step is identifying the repeating pattern, which in this case is the sequence of alternating `Stop` nodes and `NEXT` relationships, representing one segment of a `Service`:

```
(:Stop)-[:NEXT]->(:Stop)
```

The shortest path has one instance of this pattern, the longest three.
So the quantifier applied to the wrapper parentheses is the range one to three, expressed as `{1,3}`:

```
((:Stop)-[:NEXT]->(:Stop)){1,3}
```

This also includes repetitions of two, but in this case this repetition will not return matches.
To understand the semantics of this pattern, it helps to work through the expansion of the repetitions.
Here are the three repetitions specified by the quantifier, combined into a union of path patterns:

```
(:Stop)-[:NEXT]->(:Stop) |
(:Stop)-[:NEXT]->(:Stop)(:Stop)-[:NEXT]->(:Stop) |
(:Stop)-[:NEXT]->(:Stop)(:Stop)-[:NEXT]->(:Stop)(:Stop)-[:NEXT]->(:Stop)
```

The union operator (`|`) and placing node patterns next to each other are used here for illustration only; using it this way is not part of Cypher syntax.
Where two node patterns are next to each other in the expansion above, they must necessarily match the same node: the next segment of a `Service` starts where the previous segment ends.
As such they can be rewritten as a single node pattern with any filtering condition combined conjunctively.
In this example this is trivial, because the filtering applied to those nodes is just the label `Stop`:

With this, the union of path patterns simplifies to:

```
(:Stop)-[:NEXT]->(:Stop) |
(:Stop)-[:NEXT]->(:Stop)-[:NEXT]->(:Stop) |
(:Stop)-[:NEXT]->(:Stop)-[:NEXT]->(:Stop)-[:NEXT]->(:Stop)
```

The segments of the original path pattern that connect the `Stations` to the `Stops` can also be rewritten.
Here is what those segments look like when concatenated with the first repetition:

```
(:Station { name: 'Denmark Hill' })<-[:CALLS_AT]-(:Stop)
(:Stop)-[:NEXT]->(:Stop)
(:Stop)-[:CALLS_AT]->(:Station { name: 'Clapham Junction' })
```

The original `MATCH` clause now has the following three parts:

Translating the union of fixed-length path patterns into a quantified path pattern results in a pattern that will return the correct paths.
The following query adds a `RETURN` clause that yields the departure and arrival times of the two services:

// tag::patterns*variable*length*patterns*qpp[]
```cypher
MATCH (:Station { name: 'Denmark Hill' })<-[:CALLS_AT]-(d:Stop)
      ((:Stop)-[:NEXT]->(:Stop)){1,3}
      (a:Stop)-[:CALLS_AT]->(:Station { name: 'Clapham Junction' })
RETURN d.departs AS departureTime, a.arrives AS arrivalTime
```
// end::patterns*variable*length*patterns*qpp[]

| departureTime | arrivalTime |
| --- | --- |
| "17:10Z" | "17:17Z" |
| "17:07Z" | "17:19Z" |

## Quantified relationships

Quantified relationships allow some simple quantified path patterns to be re-written in a more succinct way.
Continuing with the example of `Stations` and `Stops` from the previous section, consider the following query:

> **Note**: Content truncated to token budget.
