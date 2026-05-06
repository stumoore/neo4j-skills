# Neo4j Graph Analytics for Snowflake Skill

An [Agent Skill](https://agentskills.io/specification) that helps AI agents work with [Neo4j Graph Analytics for Snowflake](https://neo4j.com/docs/snowflake-graph-analytics/current/) — a Snowflake Native Application that brings graph algorithms directly into Snowflake via SQL procedures.

## What this skill covers

- Installing Neo4j Graph Analytics from the Snowflake Marketplace
- Setting up the required privileges and roles
- The **project → compute → write** pattern for running algorithms
- SQL syntax for all available graph algorithms
- Projection configuration (node tables, relationship tables, orientation)
- Chaining algorithms together
- Working with views when column names don't match requirements
- Troubleshooting common errors

## Use this skill when

- Writing SQL to run graph algorithms on Snowflake tables
- Setting up Neo4j Graph Analytics for the first time
- Choosing the right algorithm for a business problem (fraud detection, recommendations, entity resolution, etc.)
- Configuring compute pool sizes for jobs
- Troubleshooting privilege or projection errors

## Available algorithms

| Category | Algorithms |
|---|---|
| Community Detection | WCC, Louvain, Leiden, K-Means, Triangle Count |
| Centrality | PageRank, Article Rank, Betweenness, Degree |
| Pathfinding | Dijkstra, Delta-Stepping, BFS, Yen's, Max Flow, FastPath |
| Similarity | Node Similarity, Filtered Node Similarity, KNN, Filtered KNN |
| Node Embeddings | FastRP, Node2Vec, HashGNN |
| Graph ML | GraphSAGE (node classification & embeddings, train & predict) |

## Quick example
Peer-to-Peer (P2P) Payment 
- USER_VW contains the NODEIDs of the users in P2P payment network
- AGG_TRANSACTIONS_VW contains the aggregated transactions made between SOURCEID and TARGETID users within that network

```sql
CALL Neo4j_Graph_Analytics.graph.wcc('CPU_X64_XS', {
    'project': {
        'nodeTables': ['P2P.PUBLIC.USERS'],
        'relationshipTables': {
            'P2P.PUBLIC.AGG_TRANSACTIONS_VW': {
                'sourceTable': 'P2P.PUBLIC.USER_VW',
                'targetTable': ''P2P.PUBLIC.USER_VW',
                'orientation': 'NATURAL'
            }
        }
    },
    'compute': { 'consecutiveIds': true },
    'write': [{
        'nodeLabel': 'NODES',
        'outputTable': 'P2P.PUBLIC.USER_COMPONENTS'
    }]
});
```

## Resources

- [Neo4j Graph Analytics for Snowflake documentation](https://neo4j.com/docs/snowflake-graph-analytics/current/)
- [Snowflake Marketplace listing](https://app.snowflake.com/marketplace/listing/GZTDZH40CN/neo4j-neo4j-graph-analytics)
- [Example: Basket analysis on TPC-H data](https://github.com/neo4j-product-examples/snowflake-graph-analytics/tree/main/basket-analysis)
