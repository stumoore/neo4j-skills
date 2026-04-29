# Neo4j Agent Skills

Agent skills for [Neo4j](https://neo4j.com) — Cypher queries, graph modeling, drivers, imports, GraphRAG, GDS, vector indexes, and Aura provisioning.

Browse and install at **[skills.sh/neo4j-contrib/neo4j-skills](https://skills.sh/neo4j-contrib/neo4j-skills)**.

## Configuration

Set these before or during installation:

| Variable | Description |
|---|---|
| `NEO4J_URI` | `neo4j+s://<dbid>.databases.neo4j.io` (Aura) or `neo4j://localhost:7687` (local) |
| `NEO4J_USERNAME` | Database username (default: `neo4j`) |
| `NEO4J_PASSWORD` | Database password |
| `NEO4J_DATABASE` | Target database (default: `neo4j`) |

## Installation

<details open>
<summary>Gemini CLI</summary>

```bash
gemini extensions install https://github.com/neo4j-contrib/neo4j-skills
```

Enter your env vars when prompted. Then run `gemini` and use `/extensions list` to verify.

</details>

<details>
<summary>Claude Code</summary>

```bash
claude
```

```
/plugin marketplace add https://github.com/neo4j-contrib/neo4j-skills.git
/plugin install neo4j-skills@neo4j-skills-marketplace
```

Use `/plugin list` to verify, or `/reload-plugins` after installation.

</details>

<details>
<summary>Codex</summary>

```bash
git clone https://github.com/neo4j-contrib/neo4j-skills.git
mkdir -p ~/.codex/plugins
cp -R neo4j-skills ~/.codex/plugins/neo4j-skills
```

Add to `~/.agents/plugins/marketplace.json`:

```json
{
  "name": "neo4j-marketplace",
  "interface": { "displayName": "Neo4j Skills" },
  "plugins": [
    {
      "name": "neo4j-skills",
      "source": { "source": "local", "path": "./plugins/neo4j-skills" },
      "policy": { "installation": "AVAILABLE" },
      "category": "Database"
    }
  ]
}
```

</details>

<details>
<summary>Skills CLI</summary>

```bash
npx skills add https://github.com/neo4j-contrib/neo4j-skills
```

</details>

## Available Skills

<details>
<summary>Show all 21 skills</summary>

| Skill | Use when... |
|---|---|
| [`neo4j-cypher-skill`](./neo4j-cypher-skill) | Writing, optimizing, or debugging Cypher queries |
| [`neo4j-modeling-skill`](./neo4j-modeling-skill) | Designing or reviewing graph data models |
| [`neo4j-vector-index-skill`](./neo4j-vector-index-skill) | Creating vector indexes, running similarity search |
| [`neo4j-graphrag-skill`](./neo4j-graphrag-skill) | Building GraphRAG pipelines with `neo4j-graphrag` |
| [`neo4j-import-skill`](./neo4j-import-skill) | Loading structured data (CSV, JSON) into Neo4j |
| [`neo4j-document-import-skill`](./neo4j-document-import-skill) | Extracting knowledge graphs from documents/PDFs |
| [`neo4j-gds-skill`](./neo4j-gds-skill) | Running graph algorithms (PageRank, Louvain, etc.) |
| [`neo4j-aura-graph-analytics-skill`](./neo4j-aura-graph-analytics-skill) | Graph algorithms on Neo4j Aura |
| [`neo4j-aura-provisioning-skill`](./neo4j-aura-provisioning-skill) | Creating/managing Aura instances via CLI or API |
| [`neo4j-migration-skill`](./neo4j-migration-skill) | Upgrading drivers or Cypher from 4.x/5.x to 2025.x |
| [`neo4j-graphql-skill`](./neo4j-graphql-skill) | Building GraphQL APIs backed by Neo4j |
| [`neo4j-spring-data-skill`](./neo4j-spring-data-skill) | Spring Boot + Neo4j (SDN, @Node, @Relationship) |
| [`neo4j-driver-python-skill`](./neo4j-driver-python-skill) | Python driver (`neo4j` package) |
| [`neo4j-driver-javascript-skill`](./neo4j-driver-javascript-skill) | JavaScript/TypeScript driver |
| [`neo4j-driver-java-skill`](./neo4j-driver-java-skill) | Java driver |
| [`neo4j-driver-dotnet-skill`](./neo4j-driver-dotnet-skill) | .NET/C# driver |
| [`neo4j-driver-go-skill`](./neo4j-driver-go-skill) | Go driver |
| [`neo4j-cli-tools-skill`](./neo4j-cli-tools-skill) | DB admin: `neo4j-admin`, `cypher-shell`, Aura CLI |
| [`neo4j-getting-started-skill`](./neo4j-getting-started-skill) | Zero-to-app: provision → model → load → query |
| [`neo4j-mcp-skill`](./neo4j-mcp-skill) | Neo4j MCP server setup and usage |
| [`neo4j-agent-memory-skill`](./neo4j-agent-memory-skill) | Persistent agent memory backed by Neo4j |

</details>

## What are Agent Skills?

Agent Skills are a standardized format for domain-specific AI agent knowledge. Each skill bundles step-by-step instructions, on-demand reference docs, and executable scripts — loaded progressively to keep context lean. See [agentskills.io/specification](https://agentskills.io/specification).

## Contributing

Pull requests welcome — new skills or improvements to existing ones.

## License

MIT — see the [LICENSE](LICENSE) file for details.
