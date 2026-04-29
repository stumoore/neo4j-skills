# Codex Review of `SKILL.md`

Scope: this review covers only `neo4j-cypher-skill/SKILL.md` and assesses whether it is sufficient for a coding agent to generate correct current Cypher queries.

## Verdict

No. The file is strong as a broad Cypher reference, but it is not sufficient as a sole authority for generating correct current Cypher queries. The main issue is not lack of coverage; it is that several sections are stale, internally contradictory, or wrong in ways that would lead an agent to generate invalid syntax, reject valid syntax, or choose the wrong feature family.

## Findings

### 1. High: the draft-query fallback still authorizes schema hallucination

Lines `34-43` provide a "draft" query that assumes `:Person`, `:KNOWS`, and `email`, while the same section says to never invent schema names and line `52` says schema should be inspected first.

Relevant lines:

- `SKILL.md:34-41`
- `SKILL.md:43`
- `SKILL.md:52`

Why this matters:

When schema is unknown, this is exactly the point where an agent is most likely to hallucinate labels, relationships, and properties. The file forbids that behavior in one place and then demonstrates it in another.

### 2. High: the stated safe baseline conflicts with later match-mode guidance

Line `9` and the version-gate table at lines `157-166` present `2025.01` as the safe baseline. But line `56` and the match-mode guidance at lines `716-734` treat `REPEATABLE ELEMENTS` and `DIFFERENT RELATIONSHIPS` as standard guidance.

Relevant lines:

- `SKILL.md:9`
- `SKILL.md:56`
- `SKILL.md:157-166`
- `SKILL.md:716-734`

Why this matters:

Those match modes were introduced later than `2025.01`. So under unknown-version fallback, the skill can still cause an agent to emit unsupported syntax while believing it is staying within the documented safe baseline.

### 3. High: SEARCH guidance is stale and factually wrong for current Cypher

The SEARCH section says relationship vector indexes must always use procedures because SEARCH is node-only.

Relevant lines:

- `SKILL.md:796-816`
- especially `SKILL.md:808`

Why this matters:

Current Cypher supports SEARCH with both node and relationship binding variables. An agent following this skill literally would generate the wrong query form for relationship vector search.

### 4. High: the file conflates path selectors with match modes

The skill says `ANY` and `ALL` are deprecated aliases for `REPEATABLE ELEMENTS` and `DIFFERENT RELATIONSHIPS`.

Relevant lines:

- `SKILL.md:719`
- `SKILL.md:898`

Why this matters:

`ANY` and `ALL` are path-selector concepts, not aliases for match modes. This will cause an agent to "correct" valid path-selector syntax into the wrong construct, which is a direct correctness problem rather than a stylistic one.

### 5. High: text indexes and full-text indexes are treated as if they were interchangeable

The performance guidance says the fix for `CONTAINS` / `ENDS WITH` is `db.index.fulltext.queryNodes(...)`, while nearby guidance also refers to planner-backed text indexes with `USING TEXT INDEX`.

Relevant lines:

- `SKILL.md:923-934`

Why this matters:

Text indexes and full-text indexes are different index families with different semantics. Current Cypher uses text indexes for planner-backed `CONTAINS` / `ENDS WITH` on string properties. Full-text indexes are a separate semantic-index surface. As written, the skill is internally inconsistent and would push an agent toward the wrong feature family.

### 6. Medium: the parallel-runtime example appears syntactically wrong

The file shows two separate `CYPHER` prefixes:

```cypher
CYPHER 25
CYPHER runtime=parallel
MATCH (n:Article)
RETURN count(n), avg(n.sentiment)
```

Relevant lines:

- `SKILL.md:938-944`

Why this matters:

Cypher query options are prepended with a single `CYPHER` prefix followed by one or more options. An agent copying this example is likely to emit invalid syntax.

### 7. Medium: the claimed version coverage is broader than the actual guidance

The description claims support for Neo4j `2025.x` and `2026.x`, but the version-gate table stops at `2026.02.1`, and there is no guidance for later current Cypher additions such as path modes.

Relevant lines:

- `SKILL.md:2-6`
- `SKILL.md:157-166`

Why this matters:

The file positions itself as current enough for `2026.x`, but it does not actually model important later-2026 syntax and semantics. That creates false confidence for an agent relying on it.

## Bottom Line

This skill is useful, but not yet trustworthy as a single source of truth for current Cypher generation. Before I would rely on it as an agent, I would want at least these fixes:

1. Remove or rewrite the draft-query fallback so it never invents schema.
2. Make version gates internally consistent with every example that uses gated syntax.
3. Correct SEARCH guidance to match current support for relationship vector search.
4. Separate path selectors from match modes.
5. Separate text-index guidance from full-text-index guidance.
6. Fix the query-options examples so they reflect valid current syntax.