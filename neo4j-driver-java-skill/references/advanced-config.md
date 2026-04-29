# Advanced Configuration — Neo4j Java Driver

## Full `Config.builder()` options

```java
import org.neo4j.driver.Config;
import org.neo4j.driver.Logging;
import org.neo4j.driver.net.ServerAddress;
import org.neo4j.driver.NotificationConfig;
import org.neo4j.driver.NotificationSeverity;
import java.util.concurrent.TimeUnit;

var driver = GraphDatabase.driver(uri, auth,
    Config.builder()
        // Connection pool
        .withMaxConnectionPoolSize(50)                           // default: 100
        .withConnectionAcquisitionTimeout(30, TimeUnit.SECONDS) // wait for free conn
        .withMaxConnectionLifetime(1, TimeUnit.HOURS)
        .withConnectionLivenessCheckTimeout(30, TimeUnit.MINUTES)

        // Custom resolver — useful for local dev against a cluster
        .withResolver(address -> Set.of(ServerAddress.of("localhost", 7687)))

        // TLS
        .withEncryption()
        .withTrustStrategy(Config.TrustStrategy.trustAllCertificates()) // dev ONLY

        // Notification filtering — reduce noise in logs
        .withNotificationConfig(NotificationConfig.defaultConfig()
            .enableMinimumSeverity(NotificationSeverity.WARNING))

        // Logging
        .withLogging(Logging.slf4j())           // production
        // .withLogging(Logging.console(Level.DEBUG))  // debug

        // Record fetch size (controls Bolt batching)
        .withFetchSize(1000)                    // default: 1000

        .build());
```

## Session-level auth (multi-tenant)

Cheaper than creating a new `Driver` per tenant — reuses the connection pool:

```java
var session = driver.session(SessionConfig.builder()
    .withDatabase("tenant_db")
    .withAuthToken(AuthTokens.basic("tenant-user", "pass"))
    .build());
```

## User impersonation

Executing user must have the `IMPERSONATE` privilege:

```java
var session = driver.session(SessionConfig.builder()
    .withDatabase("neo4j")
    .withImpersonatedUser("jane")
    .build());
```

## Connection pool diagnosis

| Error message | Cause | Fix |
|---|---|---|
| `Unable to acquire connection from the pool within configured maximum time` | Pool exhausted | Increase `maxConnectionPoolSize` or fix session leaks |
| `Connection to the database terminated` / `ServiceUnavailableException` | Network/server issue | Check server health, firewall, TLS |
| Session hangs with no error | Session leak — connection never returned | Add try-with-resources; audit all code paths |

## Causal consistency — cross-session bookmarks

Within a single session: automatic, nothing to do.
Across parallel sessions, pass bookmarks explicitly:

```java
import org.neo4j.driver.Bookmark;

List<Bookmark> bookmarks = new ArrayList<>();

try (var sessionA = driver.session(SessionConfig.builder().withDatabase("neo4j").build())) {
    sessionA.executeWriteWithoutResult(tx -> createPerson(tx, "Alice"));
    bookmarks.addAll(sessionA.lastBookmarks());
}
try (var sessionB = driver.session(SessionConfig.builder().withDatabase("neo4j").build())) {
    sessionB.executeWriteWithoutResult(tx -> createPerson(tx, "Bob"));
    bookmarks.addAll(sessionB.lastBookmarks());
}

// sessionC waits until both Alice and Bob exist
try (var sessionC = driver.session(SessionConfig.builder()
        .withDatabase("neo4j")
        .withBookmarks(bookmarks)
        .build())) {
    sessionC.executeWriteWithoutResult(tx -> connectPeople(tx, "Alice", "Bob"));
}
```

`executableQuery` shares a `BookmarkManager` automatically — prefer it; only drop to explicit bookmarks for complex cross-session coordination.
