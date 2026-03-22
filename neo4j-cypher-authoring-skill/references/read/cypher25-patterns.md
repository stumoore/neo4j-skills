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

# Variable-length patterns
## Quantified path patterns 

This section considers how to match paths of *varying* length by using *quantified path patterns*, allowing you to search for paths whose lengths are unknown or within a specific range.

Quantified path patterns can be useful when, for example, searching for all nodes that can be reached from an anchor node, finding all paths connecting two nodes, or when traversing a hierarchy that may have differing depths.

This example uses a new graph:

To recreate the graph, run the following query against an empty Neo4j database:

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

The problem with this solution is that not only is it verbose, it can only be used where the lengths of the target paths are known in advance.
Quantified path patterns solve this problem by extracting repeating parts of a path pattern into parentheses and applying a **quantifier**.
That quantifier specifies a range of possible repetitions of the extracted pattern to match on.
For the current example, the first step is identifying the repeating pattern, which in this case is the sequence of alternating `Stop` nodes and `NEXT` relationships, representing one segment of a `Service`:

The shortest path has one instance of this pattern, the longest three.
So the quantifier applied to the wrapper parentheses is the range one to three, expressed as `{1,3}`:

This also includes repetitions of two, but in this case this repetition will not return matches.
To understand the semantics of this pattern, it helps to work through the expansion of the repetitions.
Here are the three repetitions specified by the quantifier, combined into a union of path patterns:

The union operator (`|`) and placing node patterns next to each other are used here for illustration only; using it this way is not part of Cypher syntax.
Where two node patterns are next to each other in the expansion above, they must necessarily match the same node: the next segment of a `Service` starts where the previous segment ends.
As such they can be rewritten as a single node pattern with any filtering condition combined conjunctively.
In this example this is trivial, because the filtering applied to those nodes is just the label `Stop`:

With this, the union of path patterns simplifies to:

The segments of the original path pattern that connect the `Stations` to the `Stops` can also be rewritten.
Here is what those segments look like when concatenated with the first repetition:

The original `MATCH` clause now has the following three parts:

Translating the union of fixed-length path patterns into a quantified path pattern results in a pattern that will return the correct paths.
The following query adds a `RETURN` clause that yields the departure and arrival times of the two services:

## Quantified relationships

Quantified relationships allow some simple quantified path patterns to be re-written in a more succinct way.
Continuing with the example of `Stations` and `Stops` from the previous section, consider the following query:

If the relationship `NEXT` only connects `Stop` nodes, the `:Stop` label expressions can be removed:

When the quantified path pattern has one relationship pattern, it can be abbreviated to a *quantified relationship*.
A quantified relationship is a relationship pattern with a postfix quantifier.
Below is the previous query rewritten with a quantified relationship:

The scope of the quantifier `{1,10}` is the relationship pattern `-[:NEXT]\->` and not the node patterns abutting it.
More generally, where a path pattern contained in a quantified path pattern has the following form:

then it can be re-written as follows:

Prior to the introduction of quantified path patterns and quantified relationships, the only method in Cypher to match paths of a variable length was through variable-length relationships.
This syntax is still available but it is not GQL conformant.
It is very similar to the syntax for quantified relationships, with the following differences:

* Position and syntax of quantifier.
* Semantics of the asterisk symbol.
* Type expressions are limited to the disjunction operator.
* The WHERE clause is not allowed.

For more information, see the reference section on variable-length relationships.

## Group variables

This section uses the example of `Stations` and `Stops` used in the previous section, but with an additional property `distance` added to the `NEXT` relationships:

As the name suggests, this property represents the distance between two `Stops`.
To return the total distance for each service connecting a pair of `Stations`, a variable referencing each of the relationships traversed is needed.
Similarly, to extract the `departs` and `arrives` properties of each `Stop`, variables referencing each of the nodes traversed is required.
In this example of matching services between `Denmark Hill` and `Clapham Junction`, the variables `l` and `m` are declared to match the `Stops` and `r` is declared to match the relationships.
The variable origin only matches the first `Stop` in the path:

> **Note**: Content truncated to token budget.
