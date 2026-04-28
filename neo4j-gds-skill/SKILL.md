---
name: neo4j-gds-skill
description: Comprehensive guide to Neo4j Graph Data Science (GDS) — covering graph
  projection (native and Cypher), all algorithm categories (centrality, community
  detection, similarity, path finding, node embeddings), execution modes
  (stream/stats/mutate/write), the GDS Python client (graphdatascience), memory
  estimation, ML pipelines, and the graph catalog. Use when running GDS algorithms
  via Cypher procedures or the Python client, projecting in-memory graphs, chaining
  algorithms with mutate mode, computing node embeddings for ML, or building
  recommendation systems. Also triggers on gds.pageRank, gds.louvain, gds.fastRP,
  gds.wcc, gds.knn, GraphDataScience, graph.project, gds.graph.drop, or any
  gds.* procedure call.
  Does NOT cover Aura Graph Analytics or Snowflake Graph Analytics — those are
  separate skills. Does NOT handle Cypher authoring — use neo4j-cypher-skill.
  Does NOT handle driver setup — use a neo4j-driver-*-skill.
version: 1.0.0
allowed-tools: Bash, WebFetch
---

# Neo4j Graph Data Science (GDS)

**Plugin**: `graph-data-science` (self-managed) or built into Aura Pro
**Python client**: `graphdatascience` (PyPI) — mirrors the Cypher procedure API in Python
**Docs**: https://neo4j.com/docs/graph-data-science/current/
**Python client docs**: https://neo4j.com/docs/graph-data-science-client/current/
**Current client**: v1.21 — `pip install graphdatascience`

---

## When to Use

- Projecting an in-memory named graph for algorithm execution
- Running GDS algorithms: centrality, community detection, similarity, path finding, node embeddings
- Chaining algorithms using `mutate` mode without round-tripping through the database
- Computing node embeddings (FastRP, Node2Vec, GraphSAGE, HashGNN) as ML features
- Building recommendation systems using KNN + FastRP embeddings
- Using the GDS Python client (`graphdatascience`) for data science workflows
- Estimating memory requirements before running on large graphs

## When NOT to Use

- **Writing or optimizing Cypher queries** → use `neo4j-cypher-skill`
- **Driver/application connection setup** → use `neo4j-driver-python-skill` (or other driver skill)
- **GraphRAG retrieval pipelines** → use `neo4j-graphrag-skill`
- **Aura Graph Analytics** (serverless, no Neo4j DB required) → use `neo4j-aura-graph-analytics-skill`
- **Snowflake Graph Analytics** → use `neo4j-snowflake-graph-analytics-skill`
- **GDS on Aura Free** — GDS is unavailable; the user must upgrade to Aura Pro

---

## GDS Availability

| Deployment | GDS Available |
|---|---|
| Aura Free | ❌ No |
| Aura Pro | ✅ Yes |
| Aura Business Critical (BC) | ✅ Yes (verify with your account team) |
| Aura Virtual Dedicated Cloud (VDC) | ✅ Yes (verify with your account team) |
| Self-managed (Community) | ✅ With GDS plugin installed |
| Self-managed (Enterprise) | ✅ With GDS plugin installed |

**Pre-flight check** — run this before any GDS operation:
```cypher
RETURN gds.version() AS gds_version
```
If this fails with `Unknown function 'gds.version'`, GDS is not installed or not available on this tier. Stop and inform the user.

---

## Installation & Setup

### GDS Python Client

```bash
pip install graphdatascience                   # core
pip install graphdatascience[rust_ext]         # 3–10× faster serialization
pip install graphdatascience[networkx]         # NetworkX integration
pip install graphdatascience[ogb]              # OGB dataset loading
```

**Compatibility** (client v1.21): GDS >= 2.6, Python >= 3.10, Neo4j Driver >= 4.4.12

### Connection

```python
from graphdatascience import GraphDataScience

# Local / self-managed
gds = GraphDataScience("bolt://localhost:7687", auth=("neo4j", "password"))

# Aura DS (AuraDS instance)
gds = GraphDataScience(
    "neo4j+s://mydbid.databases.neo4j.io:7687",
    auth=("neo4j", "my-password"),
    aura_ds=True
)

print(gds.server_version())   # verify connection
```

---

## Graph Projection

GDS algorithms operate on **named in-memory graphs** projected from the Neo4j database. The graph catalog persists only for the lifetime of the Neo4j instance — restart wipes it.

### Native Projection

**Cypher:**
```cypher
CALL gds.graph.project(
  'myGraph',               -- graph name
  ['Person', 'City'],      -- node labels (or '*' for all)
  {
    KNOWS: { orientation: 'UNDIRECTED' },
    LIVES_IN: {}
  }
)
YIELD graphName, nodeCount, relationshipCount
```

**Python client:**
```python
# Simple: single label + relationship type
G, result = gds.graph.project("myGraph", "Person", "KNOWS")

# Multi-label, multi-relationship, with properties
G, result = gds.graph.project(
    "myGraph",
    {"Person": {"properties": ["age", "score"]},
     "City":   {}},
    {"KNOWS":   {"orientation": "UNDIRECTED"},
     "LIVES_IN": {"properties": ["since"]}}
)

print(f"Projected {G.node_count()} nodes, {G.relationship_count()} relationships")
```

### Cypher Projection

Use when native projection can't express the filtering or transformation you need:

```python
G, result = gds.graph.cypher.project(
    """
    MATCH (source:Person)-[r:KNOWS]->(target:Person)
    WHERE source.active = true AND target.active = true
    RETURN gds.graph.project($graph_name, source, target, {
        sourceNodeProperties: source { .score },
        targetNodeProperties: target { .score },
        relationshipType: 'KNOWS'
    })
    """,
    database="neo4j",
    graph_name="activeGraph"
)
```

### Graph Object API

```python
G.name()                        # "myGraph"
G.node_count()                  # 12_043
G.relationship_count()          # 87_211
G.node_labels()                 # ["Person", "City"]
G.relationship_types()          # ["KNOWS", "LIVES_IN"]
G.node_properties("Person")     # ["age", "score"]  — lists mutated/projected properties
G.exists()                      # True
G.memory_usage()                # "45 MiB"
G.density()                     # 0.0032
G.drop()                        # remove from catalog

# Re-attach to an existing projected graph by name
G = gds.graph.get("myGraph")

# Context manager — auto-drops on exit
with gds.graph.project("tmpGraph", "Person", "KNOWS")[0] as G:
    results = gds.pageRank.stream(G)
# G is dropped here automatically
```

### Memory Estimation

Always estimate before projecting or running algorithms on large graphs:

```cypher
CALL gds.graph.project.estimate(['Person'], 'KNOWS')
YIELD requiredMemory, bytesMin, bytesMax, nodeCount, relationshipCount
```

```python
est = gds.graph.project.estimate("Person", "KNOWS")
print(est["requiredMemory"])   # e.g. "1234 MiB"
```

---

## Execution Modes

Every algorithm supports four modes — choose deliberately:

| Mode | Side effect | Returns | When to use |
|---|---|---|---|
| `stream` | None | One row per node/pair with result | Inspect results; top-N queries |
| `stats` | None | Single row with aggregate metrics | Summary statistics, convergence check |
| `mutate` | Adds property to **in-memory graph only** | Stats row | Chain algorithms without writing to DB |
| `write` | Persists property to **Neo4j database** | Stats row | Final step — make results queryable |

**Pattern**: `stream` first to verify → `mutate` to chain → `write` to persist.

The `mutateProperty` must **not** already exist in the in-memory graph.
After `write`, a new projection is needed to use written properties in subsequent GDS algorithms (the in-memory graph does not see DB writes).

---

## Algorithm Reference

### Centrality

#### PageRank

Measures node influence via incoming relationships and their sources' influence.

```cypher
-- Stream
CALL gds.pageRank.stream('myGraph', {
  dampingFactor: 0.85,     -- probability of following a link (default 0.85)
  maxIterations: 20,
  tolerance: 0.0000001
})
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name AS name, score
ORDER BY score DESC LIMIT 10

-- Write
CALL gds.pageRank.write('myGraph', {
  writeProperty: 'pagerank',
  dampingFactor: 0.85
})
YIELD nodePropertiesWritten, ranIterations, didConverge
```

```python
# Python client
pr_df = gds.pageRank.stream(G, dampingFactor=0.85, maxIterations=20)
gds.pageRank.write(G, writeProperty="pagerank", dampingFactor=0.85)
gds.pageRank.mutate(G, mutateProperty="pagerank", dampingFactor=0.85)
```

**Gotchas**: Spider traps (closed groups with no outlinks) inflate scores — increase `dampingFactor`. Negative relationship weights are silently ignored.

#### Other Centrality Algorithms

| Algorithm | Procedure | Best for |
|---|---|---|
| Betweenness Centrality | `gds.betweenness` | Bottleneck/bridge nodes |
| Degree Centrality | `gds.degree` | Most-connected nodes (fast) |
| Article Rank | `gds.articleRank` | PageRank variant dampening high-degree nodes |
| Eigenvector | `gds.eigenvector` | Influence via well-connected neighbors |
| Closeness | `gds.closeness` | Average distance to all other nodes |
| HITS | `gds.hits` | Authority/hub scores (web-like graphs) |

---

### Community Detection

#### Louvain

Maximizes modularity by hierarchically merging communities. Best general-purpose choice for large graphs.

```cypher
CALL gds.louvain.stream('myGraph', {
  relationshipWeightProperty: 'weight',   -- optional
  includeIntermediateCommunities: false
})
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).name AS name, communityId

CALL gds.louvain.write('myGraph', { writeProperty: 'community' })
YIELD communityCount, modularity
```

```python
louvain_df = gds.louvain.stream(G)
gds.louvain.write(G, writeProperty="community")
gds.louvain.mutate(G, mutateProperty="community")
```

**Louvain vs Leiden**: Leiden is a refinement of Louvain that avoids poorly connected communities; prefer Leiden when community quality matters more than raw speed.

#### Weakly Connected Components (WCC)

Identifies disconnected subgraphs (ignoring relationship direction). Run this early to understand graph structure.

```cypher
CALL gds.wcc.stream('myGraph', {
  threshold: 0.5,          -- optional: only traverse rels with weight above threshold
  minComponentSize: 10     -- optional: only return nodes in components >= 10 nodes
})
YIELD nodeId, componentId

CALL gds.wcc.write('myGraph', { writeProperty: 'componentId' })
YIELD nodePropertiesWritten, componentCount
```

```python
wcc_df = gds.wcc.stream(G)
gds.wcc.write(G, writeProperty="componentId")
```

**When to use WCC first**: Before running expensive algorithms, partition the graph by component and run per-component to avoid wasting computation on disconnected subgraphs.

#### Other Community Algorithms

| Algorithm | Procedure | Notes |
|---|---|---|
| Leiden | `gds.leiden` | Higher quality than Louvain; slower |
| Label Propagation | `gds.labelPropagation` | Fast, good for large graphs; non-deterministic |
| K-Means | `gds.kmeans` | Requires node embedding properties as input |
| HDBSCAN | `gds.hdbscan` | Density-based; finds variable-density communities |
| K-Core Decomposition | `gds.kcore` | Finds dense subgraphs by degree threshold |
| Triangle Count | `gds.triangleCount` | Counts triangles per node; use before LCC |
| Local Clustering Coefficient | `gds.localClusteringCoefficient` | Ratio of closed triangles |
| Strongly Connected Components | `gds.scc` | Directed graphs only |

---

### Similarity

#### K-Nearest Neighbors (KNN)

Finds the k most similar nodes to each node based on node properties (typically embeddings).

```cypher
CALL gds.knn.stream('myGraph', {
  nodeProperties: ['embedding'],   -- Float[] property (e.g. from FastRP)
  topK: 10,
  sampleRate: 0.5,                 -- accuracy vs speed trade-off (default 0.5)
  similarityCutoff: 0.7            -- only return pairs above this threshold
})
YIELD node1, node2, similarity
RETURN gds.util.asNode(node1).name, gds.util.asNode(node2).name, similarity
ORDER BY similarity DESC

CALL gds.knn.write('myGraph', {
  nodeProperties: ['embedding'],
  topK: 10,
  writeRelationshipType: 'SIMILAR',
  writeProperty: 'score'
})
YIELD relationshipsWritten
```

```python
knn_df = gds.knn.stream(G, nodeProperties=["embedding"], topK=10)
gds.knn.write(G, nodeProperties=["embedding"], topK=10,
              writeRelationshipType="SIMILAR", writeProperty="score")
```

**Similarity metrics** (auto-selected by property type):
- `Float[]` → cosine, Euclidean, or Pearson
- `Integer[]` → Jaccard or Overlap
- Scalar → inverse distance

**Classic pattern**: FastRP `mutate` → KNN `write` → query `SIMILAR` relationships for recommendations.

#### Node Similarity

Computes Jaccard similarity based on common neighbors (no property needed):

```python
gds.nodeSimilarity.stream(G, similarityCutoff=0.1, topK=10)
gds.nodeSimilarity.write(G, writeRelationshipType="SIMILAR", writeProperty="score")
```

---

### Path Finding

| Algorithm | Procedure | Use case |
|---|---|---|
| Dijkstra (single source) | `gds.shortestPath.dijkstra` | Shortest path between two nodes |
| Dijkstra (all sources) | `gds.allShortestPaths.dijkstra` | All shortest paths from one source |
| A* | `gds.shortestPath.astar` | Spatial graphs with lat/lon heuristic |
| Yen's k-Shortest Paths | `gds.shortestPath.yens` | k alternative shortest paths |
| Bellman-Ford | `gds.bellmanFord` | Graphs with negative weights |
| Random Walk | `gds.randomWalk` | Sampling graph neighborhoods |
| BFS / DFS | `gds.bfs` / `gds.dfs` | Traversal order, reachability |

```cypher
-- Dijkstra: shortest path between two nodes
MATCH (source:Location {name: 'A'}), (target:Location {name: 'B'})
CALL gds.shortestPath.dijkstra.stream('myGraph', {
  sourceNode: source,
  targetNode: target,
  relationshipWeightProperty: 'distance'
})
YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path
RETURN totalCost, [nodeId IN nodeIds | gds.util.asNode(nodeId).name] AS nodes
```

---

### Node Embeddings

Compute low-dimensional vector representations of nodes for use in ML pipelines.

| Algorithm | Tier | Inductive? | Best for |
|---|---|---|---|
| **FastRP** | Production | Yes (with `propertyRatio=1.0` + `randomSeed`) | Fast, scalable, production ML pipelines |
| **GraphSAGE** | Beta | Yes | Feature-rich nodes; generalizes to unseen nodes |
| **Node2Vec** | Beta | No (transductive) | Structural similarity; same graph train+predict |
| **HashGNN** | Beta | Yes (with `featureProperties` + `randomSeed`) | Fast, GNN-style with limited compute |

#### FastRP

```cypher
CALL gds.fastRP.mutate('myGraph', {
  embeddingDimension: 256,        -- vector length; 128–512 typical
  iterationWeights: [0.0, 1.0, 1.0],  -- [self, 1-hop, 2-hop] neighborhood weights
  propertyRatio: 0.5,             -- fraction of dims for node properties (requires featureProperties)
  featureProperties: ['score'],   -- node properties to incorporate
  normalizationStrength: -0.5,    -- negative: downplay high-degree hubs
  randomSeed: 42,                 -- set for reproducibility
  mutateProperty: 'embedding'
})
YIELD nodePropertiesWritten
```

```python
gds.fastRP.mutate(G,
    embeddingDimension=256,
    iterationWeights=[0.0, 1.0, 1.0],
    randomSeed=42,
    mutateProperty="embedding"
)
gds.fastRP.write(G, embeddingDimension=256, writeProperty="embedding", randomSeed=42)
```

**FastRP → KNN pipeline** (recommendation / similarity):
```python
# 1. Project
G, _ = gds.graph.project("myGraph", "Product", {"BOUGHT_TOGETHER": {"orientation": "UNDIRECTED"}})

# 2. Embed
gds.fastRP.mutate(G, embeddingDimension=128, randomSeed=42, mutateProperty="emb")

# 3. Find similar nodes
gds.knn.write(G,
    nodeProperties=["emb"],
    topK=10,
    writeRelationshipType="SIMILAR",
    writeProperty="score"
)

# 4. Cleanup
G.drop()
```

---

## ML Pipelines

GDS supports end-to-end ML pipelines for **node classification** and **link prediction**. These manage feature engineering, train/test splits, model training, and prediction in one workflow.

```python
# Node classification pipeline (abbreviated)
pipe, _ = gds.nc_pipe("myPipeline")
pipe.addNodeProperty("fastRP", mutateProperty="emb", embeddingDimension=128, randomSeed=42)
pipe.selectFeatures("emb")
pipe.addLogisticRegression(maxEpochs=100)

model, train_result = pipe.train(G, targetProperty="label", metrics=["ACCURACY"])
print(train_result["modelInfo"]["metrics"])

predictions = model.predict_stream(G)
```

---

## Algorithm Decision Tree

```
Centrality (who is important?)
  ├── Influence via network links    → PageRank / ArticleRank
  ├── Bottleneck / bridge nodes      → Betweenness Centrality
  └── Direct connections only        → Degree Centrality

Community Detection (who clusters together?)
  ├── General purpose, fast          → Louvain
  ├── Higher quality communities     → Leiden
  ├── Fast, non-deterministic        → Label Propagation
  └── Is the graph connected?        → WCC (run first to partition)

Similarity / Recommendations
  ├── Node properties / embeddings   → KNN
  └── Common neighbors               → Node Similarity

Path Finding
  ├── Shortest path (positive weights)  → Dijkstra / A*
  ├── k alternative paths              → Yen's
  └── Negative weights                 → Bellman-Ford

Node Embeddings (ML features)
  ├── Production, fast, scalable     → FastRP
  ├── Feature-rich nodes             → GraphSAGE
  ├── Same graph train+predict       → Node2Vec
  └── GNN-style, limited compute     → HashGNN
```

---

## Common Patterns & Checklist

### Full workflow

```python
# 0. Verify GDS
print(gds.server_version())

# 1. Estimate memory
est = gds.graph.project.estimate("Person", "KNOWS")
print(est["requiredMemory"])

# 2. Project
G, _ = gds.graph.project("myGraph", "Person",
                          {"KNOWS": {"orientation": "UNDIRECTED"}})

# 3. Inspect graph
print(G.node_count(), G.relationship_count())

# 4. Stream first to verify algorithm output
df = gds.pageRank.stream(G)
print(df.sort_values("score", ascending=False).head(10))

# 5. Write to DB when satisfied
gds.pageRank.write(G, writeProperty="pagerank", dampingFactor=0.85)

# 6. Always drop to free memory
G.drop()
```

### Built-in test datasets

```python
G = gds.graph.load_cora()          # 2,708 Paper nodes, 5,429 CITES edges
G = gds.graph.load_karate_club()   # 34 Person nodes, 78 KNOWS edges
G = gds.graph.load_imdb()          # 12,772 nodes, heterogeneous
G = gds.graph.load_lastfm()        # 19,914 nodes, user-artist graph
```

### Checklist

- [ ] `gds.version()` returns a version (GDS available and licensed)
- [ ] Memory estimated for large projections before running
- [ ] Named graph dropped (`G.drop()`) after use — or context manager used
- [ ] Algorithm mode chosen: `stream` (inspect) → `mutate` (chain) → `write` (persist)
- [ ] `writeProperty` / `mutateProperty` checked for collision with existing properties
- [ ] `randomSeed` set for reproducible embeddings
- [ ] WCC run first on disconnected graphs to partition before expensive algorithms

---

## MCP Tool Mapping

When the Neo4j MCP server is available:

| Operation | MCP tool |
|---|---|
| `RETURN gds.version()` | `read-cypher` |
| `gds.pageRank.stream(...)` | `read-cypher` |
| `gds.pageRank.write(...)` | `write-cypher` |
| `gds.graph.drop(...)` | `write-cypher` |
| List available procedures: `CALL gds.list()` | `read-cypher` |
| List GDS procedures via MCP | `mcp__neo4j__list-gds-procedures` (if available) |

---

## Resources

- [GDS Library Manual](https://neo4j.com/docs/graph-data-science/current/)
- [GDS Python Client Docs](https://neo4j.com/docs/graph-data-science-client/current/)
- [Algorithm Reference](https://neo4j.com/docs/graph-data-science/current/algorithms/)
- [Python Client Tutorials](https://neo4j.com/docs/graph-data-science-client/current/tutorials/tutorials/)
- [GraphAcademy: GDS Fundamentals](https://graphacademy.neo4j.com/courses/gds-fundamentals/) — 3–4 hrs; projections, algorithm categories, execution modes
- [GDS GitHub](https://github.com/neo4j/graph-data-science-client)
- [Supported Neo4j versions](https://neo4j.com/docs/graph-data-science/current/installation/supported-neo4j-versions/)
