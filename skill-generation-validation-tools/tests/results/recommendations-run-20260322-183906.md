# Cypher Skill Test Report — `run-20260322T173906`

**Skill**: `neo4j-cypher-authoring-skill`  
**Started**: 2026-03-22 17:39:06 UTC  
**Completed**: 2026-03-22 17:41:55 UTC  

## Overall Results

| Metric | Value |
|--------|-------|
| Total cases | 31 |
| PASS | 30 |
| WARN | 0 |
| FAIL | 1 |
| Pass rate | 96.8% |

## Per-Difficulty Pass Rates

| Difficulty | Total | PASS | WARN | FAIL | Pass Rate |
|------------|------:|-----:|-----:|-----:|----------:|
| Basic | 8 | 7 | 0 | 1 | 87.5% |
| Intermediate | 8 | 8 | 0 | 0 | 100.0% |
| Advanced | 6 | 6 | 0 | 0 | 100.0% |
| Complex | 4 | 4 | 0 | 0 | 100.0% |
| Expert | 5 | 5 | 0 | 0 | 100.0% |

## DB-Hits Summary (per Difficulty)

Only cases that completed Gate 4 (PROFILE) are included.

| Difficulty | n | Min | Median | Max |
|------------|--:|----:|-------:|----:|
| — | — | — | — | — |

## Test Case Results

| ID | Difficulty | Verdict | Gate | DB Hits | Duration (s) | Question |
|----|------------|---------|-----:|--------:|-------------:|----------|
| `rec-basic-001` | basic | PASS | — | — | 8.1 | Show me a sample of movies in our catalogue — just give me … |
| `rec-basic-002` | basic | PASS | — | — | 8.1 | How many movies are in our catalogue in total? |
| `rec-basic-003` | basic | **FAIL** | 2 | — | 13.9 | What are the 10 most recently released movies in our catalo… |
| `rec-basic-004` | basic | PASS | — | — | 8.5 | What genres are available in our movie catalogue? |
| `rec-basic-005` | basic | PASS | — | — | 13.3 | Who were the actors in The Matrix? |
| `rec-basic-006` | basic | PASS | — | — | 5.8 | How many movie ratings have been submitted by users in tota… |
| `rec-intermediate-001` | intermediate | PASS | — | — | 15.5 | What are the top 10 highest-rated movies, among those that … |
| `rec-intermediate-002` | intermediate | PASS | — | — | 10.1 | Which genres have more than 20 movies? Show the genre name … |
| `rec-intermediate-003` | intermediate | PASS | — | — | 9.2 | What movies has Tom Hanks appeared in? Show titles and rele… |
| `rec-intermediate-004` | intermediate | PASS | — | — | 9.6 | Which users have been the most active reviewers — rating mo… |
| `rec-intermediate-005` | intermediate | PASS | — | — | 11.8 | Which genres tend to receive the highest IMDb ratings on av… |
| `rec-intermediate-006` | intermediate | PASS | — | — | 9.8 | Which directors have the most films in our catalogue? Show … |
| `rec-advanced-001` | advanced | PASS | — | — | 31.8 | For active users who have rated at least 3 movies, which fi… |
| `rec-advanced-002` | advanced | PASS | — | — | 18.8 | Show all movies alongside their average user rating. Movies… |
| `rec-advanced-003` | advanced | PASS | — | — | 38.3 | What movies would you recommend to User 1 based on what sim… |
| `rec-advanced-004` | advanced | PASS | — | — | 19.0 | For each genre, what are the five best-reviewed movies base… |
| `rec-advanced-005` | advanced | PASS | — | — | 20.7 | Which actors have worked with cast members from The Matrix,… |
| `rec-advanced-006` | advanced | PASS | — | — | 25.8 | Search for movies with 'star wars' in the title. What are t… |
| `rec-complex-001` | complex | PASS | — | — | 32.4 | What are the top 5 movies I should recommend to User 534? B… |
| `rec-complex-002` | complex | PASS | — | — | 13.6 | Which people in our database have both acted in and directe… |
| `rec-complex-003` | complex | PASS | — | — | 29.5 | Which genres have the most consistent audience ratings — me… |
| `rec-complex-004` | complex | PASS | — | — | 19.6 | For the 10 most-rated movies in our catalogue, what genres … |
| `rec-expert-001` | expert | PASS | — | — | 44.3 | What is the shortest connection between Tom Hanks and Kevin… |
| `rec-expert-002` | expert | PASS | — | — | 74.3 | Starting from The Matrix, what other movies can you reach b… |
| `rec-expert-003` | expert | PASS | — | — | 20.5 | Which 5 movies in our catalogue have the most similar story… |
| `rec-expert-004` | expert | PASS | — | — | 87.0 | What are the top 10 movies to recommend to User 1, factorin… |
| `rec-expert-005` | expert | PASS | — | — | 32.3 | Which users have the broadest influence in our community — … |
| `rec-casual-001` | intermediate | PASS | — | — | 28.8 | What are some well-reviewed action films in our catalogue? … |
| `rec-casual-002` | basic | PASS | — | — | 20.8 | Show me movies that came out in the nineties — films from t… |
| `rec-casual-003` | intermediate | PASS | — | — | 24.4 | Which movies were genuine box office hits — films where the… |
| `rec-casual-004` | basic | PASS | — | — | 12.9 | How many sci-fi films are in our catalogue? |

## Failure Analysis

### FAIL (1 cases)

#### Gate 2 (1 case(s))

**`rec-basic-003`** — What are the 10 most recently released movies in our catalogue from after the year 2000?

> **Gate 2 FAIL**: Query returned 0 rows, expected ≥ 10

```cypher
CYPHER 25
MATCH (m:Movie)
WHERE m.released > 2000
RETURN m.title, m.released, m.imdbRating
ORDER BY m.released DESC
LIMIT 10
```

_Metrics_: elapsed=430 ms


---

_Report generated 2026-03-22T17:43:46Z by `tests/harness/reporter.py`_
