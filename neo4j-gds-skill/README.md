# neo4j-gds-skill

Guides agents through the full Neo4j Graph Data Science (GDS) workflow — from projecting in-memory graphs to running algorithms, chaining results across execution modes, and persisting outputs back to the database.

## What this skill covers

**Graph Projection**
- Native projection (node labels + relationship types, with properties and orientation)
- Cypher projection for filtered or transformed subgraphs
- Graph Object API: inspect node/relationship counts, labels, properties, memory usage
- Memory estimation before projecting large graphs
- Context manager pattern for automatic graph cleanup

**Execution Modes**
- `stream` — inspect per-node results without writing anything
- `stats` — aggregate summary metrics only
- `mutate` — write results into the in-memory graph to chain algorithms
- `write` — persist results to the Neo4j database
- When to use each mode and the correct chaining pattern (`stream → mutate → write`)

**Algorithm Reference**
- **Centrality**: PageRank, Betweenness, Degree, ArticleRank, Eigenvector, Closeness, HITS
- **Community Detection**: Louvain, Leiden, WCC, Label Propagation, K-Means, HDBSCAN, K-Core, Triangle Count, SCC
- **Similarity**: K-Nearest Neighbors (KNN), Node Similarity
- **Path Finding**: Dijkstra, A*, Yen's k-shortest paths, Bellman-Ford, BFS/DFS, Random Walk
- **Node Embeddings**: FastRP (production), GraphSAGE, Node2Vec, HashGNN (beta)

**ML Pipelines**
- Node classification and link prediction pipelines
- Feature engineering (addNodeProperty), train/test splits, model training, prediction

**GDS Python Client** (`graphdatascience`)
- Connection setup for local Neo4j and AuraDS (`aura_ds=True`)
- Python-idiomatic API mirroring every Cypher procedure
- Built-in test datasets (Cora, Karate Club, IMDB, LastFM)
- Full FastRP → KNN recommendation pipeline example

**Utilities**
- Algorithm decision tree (which algorithm for which question)
- Pre-flight checklist (GDS installed, memory estimated, graph dropped after use)
- MCP tool mapping (`read-cypher` vs `write-cypher` for each operation)

## Availability

| Deployment | GDS Available |
|---|---|
| Aura Free | ❌ No |
| Aura Pro | ✅ Yes |
| Aura Business Critical / VDC | ✅ Yes (verify with account team) |
| Self-managed (Community or Enterprise) | ✅ With GDS plugin installed |

## What this skill does NOT cover

- **Aura Graph Analytics** (serverless, no Neo4j DB required) → use `neo4j-aura-graph-analytics-skill`
- **Snowflake Graph Analytics** → use `neo4j-snowflake-graph-analytics-skill`
- **Cypher query authoring** → use `neo4j-cypher-skill`
- **Driver/connection setup** → use a `neo4j-driver-*-skill`

## Install

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-gds-skill
```

Or paste this link into your coding assistant:
https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-gds-skill
