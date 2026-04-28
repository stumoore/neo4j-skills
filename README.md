# Neo4j Agent Skills

A collection of [Agent Skills](https://agentskills.io/specification) designed to help AI agents work effectively with Neo4j graph databases.

## Installation

```bash
# Install all Neo4j skills
npx skills add https://github.com/neo4j-contrib/neo4j-skills

# Or install individual skills
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-cypher-skill
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-migration-skill
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-cli-tools-skill
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-getting-started-skill
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-agent-memory-skill
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-driver-python-skill
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-driver-javascript-skill
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-driver-java-skill
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-driver-go-skill
npx skills add https://github.com/neo4j-contrib/neo4j-skills --skill neo4j-driver-dotnet-skill
```

Or paste a skill link directly into your coding assistant:
- https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-cypher-skill
- https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-migration-skill
- https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-cli-tools-skill
- https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-getting-started-skill
- https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-agent-memory-skill
- https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-driver-python-skill
- https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-driver-javascript-skill
- https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-driver-java-skill
- https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-driver-go-skill
- https://github.com/neo4j-contrib/neo4j-skills/tree/main/neo4j-driver-dotnet-skill

## Available Skills

### neo4j-cypher-skill

Generates, optimizes, and validates Cypher 25 queries for Neo4j 2025.x and 2026.x.

**Use this skill when:**
- Writing or optimizing Cypher queries (reads, writes, subqueries, batch, LOAD CSV)
- Using vector/fulltext search, quantified path patterns, or `CALL IN TRANSACTIONS`
- Reviewing EXPLAIN/PROFILE plans or recovering from query errors

Includes schema-first inspection, parameterized output, 50+ anti-pattern checks, and version gates for 2026.x features. Requires Neo4j >= 2025.01.

### neo4j-getting-started-skill

Guides an agent from zero to a running Neo4j application across 8 stages: prerequisites → provision → model → load → explore → query → build. Works interactively or fully autonomously.

**Use this skill when:** starting a new Neo4j project, provisioning Aura or Docker, or building an end-to-end graph application.

### neo4j-cli-tools-skill

Guidance for Neo4j CLI tools: neo4j-admin, cypher-shell, aura-cli, and neo4j-mcp.

**Use this skill when:** configuring databases via command line, running admin tasks, managing Aura instances, or setting up the Neo4j MCP server.

### neo4j-migration-skill

Assists with upgrading Neo4j drivers (.NET, Go, Java, JavaScript, Python) to new major versions.

### neo4j-agent-memory-skill

Graph-native agent memory with three layers: short-term (conversations), long-term (knowledge graph via the POLE+O entity model), and reasoning traces. Covers the `neo4j-agent-memory` Python package, the hosted NAMS service at memory.neo4jlabs.com, the MCP server, and integrations for LangChain, PydanticAI, CrewAI, AWS Strands, Google ADK, OpenAI Agents, LlamaIndex, and Microsoft Agent Framework.

**Use this skill when:** building or documenting agent memory with Neo4j, using the `neo4j-agent-memory` package or NAMS, or writing framework integrations and positioning content about graph-native memory.

### neo4j-driver-python-skill

Best practices for the official Neo4j Python Driver v6: execute_query, sessions, transactions, async via AsyncGraphDatabase, data types, UNWIND batching, and causal consistency.

**Use this skill when:** writing or reviewing Python code that connects to Neo4j, or debugging sessions, transactions, or async patterns.

### neo4j-driver-javascript-skill

Best practices for the official Neo4j JavaScript/TypeScript Driver v6: executeQuery, Integer handling, temporal types, async/Promise patterns, TypeScript, and browser/WebSocket support.

**Use this skill when:** writing or reviewing JavaScript or TypeScript code that connects to Neo4j, or debugging Integer types or browser vs Node.js targeting.

### neo4j-driver-java-skill

Best practices for the official Neo4j Java Driver v6: Maven/Gradle setup, executableQuery, managed transactions, async/reactive patterns, data types, and Spring integration.

**Use this skill when:** writing or reviewing Java code that connects to Neo4j, or debugging sessions, transactions, or Spring Data Neo4j configuration.

### neo4j-driver-go-skill

Best practices for the official Neo4j Go Driver v6: ExecuteQuery, managed and explicit transactions, error handling, data types, and connection configuration.

**Use this skill when:** writing or reviewing Go code that connects to Neo4j, or debugging sessions, transactions, or driver configuration.

### neo4j-driver-dotnet-skill

Best practices for the official Neo4j .NET Driver v6 for .NET 8/9/10: ExecutableQuery fluent API, DI registration, ExecuteReadAsync/ExecuteWriteAsync, IResultCursor, temporal types, and async patterns.

**Use this skill when:** writing or reviewing C# or .NET code that connects to Neo4j, or debugging sessions, transactions, or IResultCursor consumption.

## What are Agent Skills?

Agent Skills are a standardized format for providing AI agents with domain-specific knowledge and capabilities. They enable agents to perform specialized tasks more effectively by bundling:

- **Instructions** - Step-by-step guidance for accomplishing specific tasks
- **References** - Detailed documentation that agents can access when needed
- **Scripts** - Executable code for automation

Skills follow a progressive disclosure pattern, loading only what's needed to minimize context usage while maximizing effectiveness. For the complete specification, visit [agentskills.io/specification](https://agentskills.io/specification).

## Contributing

Contributions are welcome! Please feel free to submit pull requests with new skills or improvements to existing ones.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
