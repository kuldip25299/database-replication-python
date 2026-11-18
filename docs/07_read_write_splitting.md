# Read/Write Splitting

## 1. The Problem

As an application grows, database traffic usually becomes read-heavy.

Consider an e-commerce application:

- Users browse products.
- Users search and filter products.
- Users view product details.
- Users check order history.
- Users place orders and update their profiles.

Most of these operations are reads. Only a smaller portion of requests modify data.

If every request goes to the primary database, the primary handles both reads and writes. This can become a bottleneck even when the application has multiple read replicas available.

We can distribute read traffic across replicas while keeping writes on the primary.

This approach is called **read/write splitting**.

## 2. What Is Read/Write Splitting?

Read/write splitting is a database routing strategy where:

- Write operations are sent to the primary database.
- Read operations are sent to one of the available replicas.
- The primary continues to coordinate writes and replication.

Instead of sending every query to one database node, the application chooses the destination based on the operation.

### Architecture

```text
                 Application
                      |
                Query Router
                 /        \
                /          \
           WRITE            READ
             |                |
             v                v
        Primary DB       Replica Selector
             |             /        \
             |            /          \
             v           v            v
          Changes     Replica 1    Replica 2
             |
             +-------- Replication -------->
```

The primary handles writes. Replicas serve read traffic using the data they have received from the primary.

## 3. How Request Routing Works

Let's walk through a practical example.

### Write request

A user places an order.

```sql
INSERT INTO orders (user_id, amount)
VALUES (101, 2500);
```

The application sends this query to the primary database.

```text
Application
    |
    v
Query Router
    |
    v
Primary DB
    |
    v
Commit transaction
    |
    v
Replicate changes
```

The write must go to the primary because it is responsible for accepting and coordinating writes.

### Read request

A user opens the product listing page.

```sql
SELECT * FROM products;
```

The application can send this query to a replica.

```text
Application
    |
    v
Query Router
    |
    v
Replica Selector
    |
    +------> Replica 1
    |
    +------> Replica 2
```

This distributes read traffic across multiple database nodes.

## 4. Why Not Send Every Read to a Replica?

This is where read/write splitting becomes more interesting.

Replicas may not contain the latest committed data because replication can take time.

Consider this sequence:

```text
1. User places an order.
2. Primary commits the order.
3. Application returns success.
4. User opens order history immediately.
5. Application routes the read to a replica.
6. Replica has not received the latest order yet.
7. User sees an outdated order history.
```

The write succeeded, but the following read returned stale data.

This is a replication-lag problem, not necessarily a routing bug.

A routing strategy must account for this behavior.

## 5. Handling Read-After-Write Consistency

There are several ways to avoid stale reads immediately after a write.

### Strategy 1: Read from the primary after a write

After a user performs a write, route subsequent reads to the primary for a short period or for the remainder of the session.

Example:

```text
User places order
       |
       v
Write to primary
       |
       v
Mark session as recently written
       |
       v
Next read goes to primary
```

This is straightforward and useful for operations where users expect to see their latest changes.

The trade-off is that some read traffic returns to the primary.

### Strategy 2: Wait for replication

The application can wait until a replica has received and applied the relevant transaction before reading from it.

This requires a reliable way to identify the transaction position and check replica progress.

It can preserve replica-based reads, but adds latency and complexity.

### Strategy 3: Use replicas with acceptable lag

For some applications, slightly stale data is acceptable.

For example:

- Product catalog browsing.
- Public dashboards.
- Analytics pages.
- Non-critical reporting.

The application can select a replica whose replication lag is within an acceptable threshold.

This should not be used for operations that require the latest committed data.

## 6. Replica Selection Strategies

When multiple replicas are available, the application needs a selection strategy.

Common approaches include:

| Strategy | How it works | Trade-off |
|---|---|---|
| Round robin | Distributes reads in sequence | Does not account for replica load |
| Random selection | Selects a replica randomly | Simple, but load can be uneven |
| Least connections | Selects the replica with fewer active connections | Requires connection information |
| Least load | Selects a replica with lower measured load | Requires monitoring and reliable metrics |
| Lag-aware routing | Avoids replicas with excessive lag | Requires replication-lag information |

For a learning implementation, round robin is a good starting point.

For production, selection should also account for replica health, connection limits, lag, and query workload.

## 7. Python Implementation

Let's implement a small read/write router.

The example uses in-memory database nodes to demonstrate routing behavior.

It does not implement a real database connection pool or network replication.

### Database Node

```python
class DatabaseNode:
    def __init__(self, name):
        self.name = name
        self.data = {}

    def write(self, key, value):
        self.data[key] = value
        print(f"[{self.name}] WRITE: {key} = {value}")

    def read(self, key):
        value = self.data.get(key)
        print(f"[{self.name}] READ: {key} = {value}")
        return value

    def replicate_from(self, primary):
        self.data = primary.data.copy()
        print(f"[{self.name}] Replicated data from primary")
```

### Read/Write Router

```python
class ReadWriteRouter:
    def __init__(self, primary, replicas):
        self.primary = primary
        self.replicas = replicas
        self.replica_index = 0

    def write(self, key, value):
        # All writes go to the primary.
        self.primary.write(key, value)

    def read(self, key, read_from_primary=False):
        # Some reads must use the primary to avoid stale data.
        if read_from_primary or not self.replicas:
            return self.primary.read(key)

        # Round-robin replica selection.
        replica = self.replicas[self.replica_index]

        self.replica_index = (
            self.replica_index + 1
        ) % len(self.replicas)

        return replica.read(key)
```

### Running the Example

```python
if __name__ == "__main__":
    primary = DatabaseNode("Primary")

    replica_1 = DatabaseNode("Replica-1")
    replica_2 = DatabaseNode("Replica-2")

    replicas = [replica_1, replica_2]

    router = ReadWriteRouter(
        primary=primary,
        replicas=replicas
    )

    # Write goes to primary.
    router.write("product_1", "Laptop")

    # Simulate asynchronous replication.
    # Before replication, replicas may return stale data.
    print("\n--- Reads before replication ---")

    router.read("product_1")
    router.read("product_1")

    # Replicate primary data to replicas.
    print("\n--- Replication ---")

    replica_1.replicate_from(primary)
    replica_2.replicate_from(primary)

    # Reads now return replicated data.
    print("\n--- Reads after replication ---")

    router.read("product_1")
    router.read("product_1")

    # A read that requires the latest primary data.
    print("\n--- Read from primary ---")

    router.read(
        "product_1",
        read_from_primary=True
    )
```

### Expected Output

```text
[Primary] WRITE: product_1 = Laptop

--- Reads before replication ---
[Replica-1] READ: product_1 = None
[Replica-2] READ: product_1 = None

--- Replication ---
[Replica-1] Replicated data from primary
[Replica-2] Replicated data from primary

--- Reads after replication ---
[Replica-1] READ: product_1 = Laptop
[Replica-2] READ: product_1 = Laptop

--- Read from primary ---
[Primary] READ: product_1 = Laptop
```

The example demonstrates three important behaviors:

1. Writes always go to the primary.
2. Reads are distributed across replicas using round robin.
3. A read can explicitly use the primary when freshness matters.

Notice that replication is triggered manually in this example. A real database has its own replication mechanism, and the application router should not copy database contents directly.

## 8. Production Considerations

The basic router is easy to understand, but production routing needs more care.

### Replica health checks

Never route traffic to a replica that is unavailable or unhealthy.

The router should maintain a healthy replica list and remove failed replicas from selection.

### Replication lag

A replica can be online but significantly behind the primary.

Health checks alone are not enough. Routing decisions may also need replication-lag information.

### Connection pooling

Creating a new database connection for every request is expensive.

Applications generally use connection pools, often with separate pools or configurations for primary and replica connections.

### Query classification

Not every SQL statement can safely be classified by simply checking whether it starts with `SELECT`.

For example, some database operations can modify data while returning rows. Transactions can also contain both reads and writes.

A production router should use explicit application-level read/write boundaries or database-aware routing rather than relying on simplistic SQL string checks.

### Transactions

A transaction should generally remain connected to the primary when it performs writes.

Mixing reads from replicas with writes on the primary can create inconsistent transaction behavior.

### Failover

If the primary fails, the application needs a failover process that promotes an eligible replica and updates routing.

The router must not continue sending writes to an old primary after a new primary has been elected.

## 9. When Should You Use Read/Write Splitting?

Read/write splitting is useful when:

- The application has significantly more reads than writes.
- The primary database is under read pressure.
- Replicas have enough capacity to handle additional traffic.
- Some read operations can tolerate replication lag.
- The application can identify operations that require fresh data.

It may not help much when:

- The application is primarily write-heavy.
- The primary is already the bottleneck for writes.
- Most reads require strongly consistent, latest data.
- Replica infrastructure and operational overhead outweigh the benefit.

Adding replicas does not automatically improve performance. If every request still reads from the primary, the replicas are not reducing its read workload.

## 10. Key Takeaways

- Read/write splitting routes writes to the primary and distributes reads across replicas.
- Round robin is a simple replica-selection strategy.
- Replication lag can cause stale reads.
- Read-after-write operations may need to go to the primary.
- Production routing must consider health, lag, connection pools, transactions, and failover.
- Read replicas improve read capacity, not write capacity.

Read/write splitting is one of the practical ways to scale database reads, but it introduces consistency decisions that the application must handle deliberately.

## Next

Continue to [Failover and Recovery](08_failover_and_recovery.md) to understand what happens when the primary database fails and how a replica can take over.
