---
name: neo4j-text2cypher-skill
description: Use when generating Cypher from a natural-language question against a Neo4j graph (text2cypher / LLM-driven querying). Covers schema-first prompting, the dozen silent-wrong-answer gotchas that LLM-generated Cypher routinely hits, and picking between Cypher 5 and Cypher 25.
allowed-tools: WebFetch
---

# Neo4j text2cypher skill

Generating Cypher from a natural-language question is easy; generating Cypher that returns the **right** answer is not. Most text2cypher failures are not syntax errors — they are queries that run fine and quietly return wrong or empty results. This skill lists the gotchas that cause silent-wrong-answer bugs, based on patterns observed on real graphs.

## When to use

Use this skill when:
- building an LLM → Cypher pipeline (RAG over a graph, a "chat with your graph" feature, text2cypher fine-tuning data, an agent that queries Neo4j)
- reviewing LLM-generated Cypher before it runs against production
- debugging a query that "works" but returns the wrong number of rows
- deciding whether to target Cypher 5 or Cypher 25 in the generator

## Ground rules for the generator

1. **Give the LLM the schema, not the data.** Use `CALL apoc.meta.schema()` (node labels, rel types, properties + types + indexed flag) and inject it verbatim. The two most valuable hints are **property types** (prevents date/string mismatches) and **indexed flag** (steers the LLM toward the cheap lookup path).
2. **Show few-shot examples with intent + Cypher.** Three examples covering aggregation, multi-hop traversal, and a negation pattern remove 80% of mistakes. Include at least one example that uses an undirected relationship.
3. **Parameterize, don't interpolate.** User input goes in `$params`, never `f"...{value}..."`. Cypher injection is real and query-plan caching depends on stable query text.
4. **Add `LIMIT` by default.** LLMs omit it; a 5-hop pattern with no limit on a moderately dense graph is a production outage. If the question is "top N", make the generator emit `ORDER BY … LIMIT N` explicitly.
5. **Validate with `EXPLAIN`, not `PROFILE`.** `EXPLAIN` compiles without running; `PROFILE` runs the query. For an LLM loop, `EXPLAIN` is the safe syntactic gate.
6. **Tell the generator which Cypher version to target.** Cypher 5 and Cypher 25 diverge on `SET n = r`, dynamic labels, vector type, and several function names. See [cypher-5-vs-25.md](references/cypher-5-vs-25.md). Emit `CYPHER 5` or `CYPHER 25` as the first token so the query is deterministic across databases.

## The gotchas that silently return wrong answers

Each of these was observed on a real ~76k-org graph. They do not raise errors; they return the wrong number of rows.

1. **Names are not unique.** `MATCH (o:Organization {name: 'Google'})` returned three entities (Google LLC + two others). Prefer `uri` / `id` / `elementId()` for single-entity lookup and use `name` only for discovery (with `LIMIT` + display).
2. **Relationship direction is rarely symmetric in data.** `(Apple)-[:HAS_COMPETITOR]->()` = 26 rows; `()-[:HAS_COMPETITOR]->(Apple)` = 386. The *meaning* feels symmetric ("competitor of") but the graph stores one direction per source. For semantically-symmetric predicates, use an undirected pattern: `(a)-[:HAS_COMPETITOR]-(b)`.
3. **Equality against a list silently returns zero.** `WHERE t.name = 'Programming Languages'` returns `[]` when the property is a `LIST<STRING>`. Use `'Programming Languages' IN t.categories` or `any(x IN t.categories WHERE …)`. Check the schema's property type before emitting `=`.
4. **String compared to date/datetime silently returns zero.** `WHERE a.date > '2024-01-01'` on a `DATE_TIME` property returned **0** rows; `WHERE a.date > datetime('2024-01-01')` returned 4551. Always cast the literal with `date()`, `datetime()`, or `localdatetime()` to match the property type.
5. **`NOT x = true` drops NULLs.** "Companies that are not public" → `WHERE NOT o.isPublic = true` missed 66,457 rows where `isPublic IS NULL` (only `isPublic = false` came back). Use `coalesce(o.isPublic, false) = false` or `o.isPublic IS NULL OR o.isPublic = false`.
6. **Aggregations skip NULLs.** `avg(o.revenueValue)` silently averaged over only 7,904 of 76,102 orgs. The answer looks precise but is about 10% of the corpus. Always return `count(prop)` next to `count(*)` so the user sees the coverage.
7. **Units/currencies are not normalized.** `revenueValue` coexists in USD, EUR, INR, CNY, GBP, JPY, KRW, RUB… Summing or ranking without grouping by `revenueCurrency` is wrong. Either filter to one currency or normalize client-side.
8. **Denormalized list properties hide matches.** `allNames` contains translations, marketing aliases, unrelated multilingual tokens. `'Apple' IN o.allNames` matched an HSBC node because a Chinese blurb contained the word "Apple". Prefer `name` / `fullName` unless you truly want aliases, and `LIMIT` + human review.
9. **List-of-string "records" need parsing.** `yearlyRevenues = ["2024: 391035000000.0 USD", ...]` looks queryable but isn't aggregate-friendly. Flag these at schema-inspection time and either join on a dedicated relationship instead, or `UNWIND` + `split()` client-side.
10. **Hierarchies double-count.** `IndustryCategory` has `level` 1/2/3; an org is attached to all levels it fits. `COUNT(*)` of `Org-[:HAS_CATEGORY]->Cat` grouped by category without filtering on `level` double-counts. Filter `WHERE c.level = 1` for top-level buckets.
11. **Variable-length / multi-hop paths explode.** `(a)-[:HAS_CUSTOMER]->(b)-[:HAS_CUSTOMER]->(c)` from a single Apple node returned 686 paths. 3-hops on a dense graph is easily 6-figure rows. Always `LIMIT` and aggregate early with `count(DISTINCT c)` — not `count(*)` of the path.
12. **Relationships have properties too.** `IN_CITY` carries `isCurrent`, `isPrimary`, `address`, `street`. LLMs pattern-match on `(:Organization)-[:IN_CITY]->(:City)` and forget `WHERE r.isCurrent = true`, silently counting historical addresses. Include rel-properties in the schema handed to the LLM.
13. **`id()` is deprecated.** Use `elementId()` for node/relationship identity. Old LLM training data leans on `id()`; patch prompts and fine-tunes accordingly.
14. **Fuzzy match is not `=`.** "Companies called Apple" under `=` returns just the literal "Apple" nodes. For discovery use `CONTAINS` / `=~` / full-text index (`db.index.fulltext.queryNodes`). Know which is indexed on your graph.

Full-length reference with copy-paste fixes: [gotchas.md](references/gotchas.md).

## Cypher version for generated queries

- **Target Cypher 25** if the database is on Neo4j 2025.06+ and has `DEFAULT LANGUAGE CYPHER 25`, or if you want access to the vector type, `$(…)` dynamic labels, or `WHEN/THEN` conditional subqueries.
- **Target Cypher 5** if the database defaults to Cypher 5 and you need stability, or your training data / prompt library is Cypher-5-shaped.
- **Always emit the prefix**: put `CYPHER 5` or `CYPHER 25` as the first token of generated queries so the same query gives the same result on any database regardless of its default.

Detailed language diff: [cypher-5-vs-25.md](references/cypher-5-vs-25.md).

## Instructions

When invoked:

1. Run `CALL apoc.meta.schema()` (or the MCP `get_neo4j_schema` equivalent). Inject the result into the LLM prompt as plain text — do not summarize. Include property **types** and the **indexed** flag.
2. Before emitting the final Cypher, pass it through an `EXPLAIN` call. If that errors, feed the error back to the LLM and retry once.
3. On every generated query, audit it against the 14 gotchas above. The highest-hit three in practice: string/date mismatch (#4), list equality (#3), and directionality (#2).
4. Always append `LIMIT` to any non-aggregating `RETURN`, and `count(*)` + `count(prop)` to any aggregation.
5. Emit `CYPHER 5` / `CYPHER 25` as the first token of the query, matching the target database.

## Resources

- [APOC schema inspection](https://neo4j.com/docs/apoc/current/overview/apoc.meta/apoc.meta.schema/)
- [Cypher `EXPLAIN` and `PROFILE`](https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/execution-plans/)
- [Neo4j MCP server](https://neo4j.com/docs/mcp/current/) — ready-made read/write/schema tools for an LLM
- [Cypher version selection](https://neo4j.com/docs/cypher-manual/current/queries/select-version/)
- [Cypher additions, deprecations, removals](https://neo4j.com/docs/cypher-manual/current/deprecations-additions-removals-compatibility/)
