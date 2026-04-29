# Performance — Connection Pool, Streaming, CancellationToken

## Always Specify the Database

Omitting database causes an extra network round-trip on every call:

```csharp
// ExecutableQuery:
.WithConfig(new QueryConfig(database: "neo4j"))

// Session:
driver.AsyncSession(conf => conf.WithDatabase("neo4j"))
```

## Route Reads to Replicas

```csharp
// ExecutableQuery:
.WithConfig(new QueryConfig(database: "neo4j", routing: RoutingControl.Readers))

// Managed transaction — ExecuteReadAsync routes automatically
await session.ExecuteReadAsync(async tx => { ... });
```

## Large Results — Lazy Streaming

`ExecutableQuery` is always eager — fine for moderate result sets.

For large results, stream lazily inside `ExecuteReadAsync`:

```csharp
await using var session = driver.AsyncSession(conf => conf.WithDatabase("neo4j"));
await session.ExecuteReadAsync(async tx =>
{
    var cursor = await tx.RunAsync("MATCH (p:Person) RETURN p.name AS name");
    while (await cursor.FetchAsync())
    {
        ProcessRecord(cursor.Current.Get<string>("name"));
    }
});
```

## Connection Pool Tuning

```csharp
await using var driver = GraphDatabase.Driver(uri, auth, conf => conf
    .WithMaxConnectionPoolSize(50)
    .WithConnectionAcquisitionTimeout(TimeSpan.FromSeconds(30))
    .WithMaxConnectionLifetime(TimeSpan.FromHours(1))
    .WithConnectionIdleTimeout(TimeSpan.FromMinutes(10)));
```

Default pool size: 100. Reduce if running many app instances to avoid overwhelming the server.

## CancellationToken — Propagate End-to-End

In web apps, always propagate the request cancellation token. Without it, abandoned requests keep running on the server, exhausting the connection pool under load.

```csharp
// ASP.NET Core controller
[HttpGet("people")]
public async Task<IActionResult> GetPeople(CancellationToken cancellationToken)
{
    var (records, _, _) = await driver
        .ExecutableQuery("MATCH (p:Person) RETURN p.name AS name")
        .WithConfig(new QueryConfig(database: "neo4j"))
        .ExecuteAsync(cancellationToken);
    return Ok(records.Select(r => r.Get<string>("name")));
}

// Session-based
return await session.ExecuteReadAsync(async tx =>
{
    var cursor = await tx.RunAsync(
        "MATCH (p:Person) RETURN p.name AS name",
        cancellationToken: cancellationToken);
    return await cursor.ToListAsync(r => r.Get<string>("name"), cancellationToken);
}, cancellationToken: cancellationToken);

// Explicit transaction
await using var tx = await session.BeginTransactionAsync(cancellationToken);
await tx.RunAsync("CREATE (p:Person {name: $name})", new { name }, cancellationToken);
await tx.CommitAsync(cancellationToken);
```
