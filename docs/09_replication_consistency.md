# Replication Consistency

## 1. The Problem

Imagine an e-commerce application running with one primary database and two read replicas.

A user updates their delivery address.

The primary database commits the update successfully. However, the replicas may take some time to receive and apply that change.

Now consider what happens when the application reads the user's address:

- The primary returns the updated address.
- Replica 1 may return the updated address.
- Replica 2 may still return the old address.

All three databases are operational, but they do not return the same result.

This happens because replication is not always instantaneous.

The application needs to understand what consistency guarantees it can expect when reading data from different database nodes.

## 2. What Is Replication Consistency?

Replication consistency describes how database nodes maintain and expose the same data as changes are replicated across them.

In a primary-replica architecture:

- Writes are accepted by the primary.
- Changes are propagated to replicas.
- Replicas may temporarily contain older data.
- The consistency guarantee depends on the replication mechanism and configuration.

The important distinction is that **having multiple copies of data does not mean every copy is immediately identical.**

## 3. Strong Consistency vs Eventual Consistency

Two useful consistency models to understand are strong consistency and eventual consistency.

### Strong Consistency

Under a strong consistency guarantee, a read observes the latest committed write according to the system's consistency rules.

Consider this sequence:

```text
1. User updates their address.
2. Primary commits the update.
3. Application receives success.
4. User reads the address.
5. Application returns the updated address.
```

The application should not return an older value after the write has been acknowledged.

Strong consistency is useful for operations where stale data can cause serious problems.

Examples:

- Account balance checks.
- Inventory reservation.
- Payment status.
- Critical user profile updates.

The exact guarantee depends on the database's transaction and replication configuration. Reading from the primary alone does not automatically guarantee every possible consistency property if the system has other failure or transaction concerns.

### Eventual Consistency

Under eventual consistency, replicas may temporarily return older data, but if updates stop and replication continues successfully, the replicas are expected to converge.

Example:

```text
Time 1:
Primary:   Product price = 1500
Replica 1: Product price = 1500
Replica 2: Product price = 1500

Time 2:
Primary:   Product price = 1800
Replica 1: Product price = 1500
Replica 2: Product price = 1500

Time 3:
Primary:   Product price = 1800
Replica 1: Product price = 1800
Replica 2: Product price = 1500

Time 4:
Primary:   Product price = 1800
Replica 1: Product price = 1800
Replica 2: Product price = 1800
```

The replicas temporarily disagree but eventually converge.

This model can work well for:

- Product catalog browsing.
- Analytics dashboards.
- Activity feeds.
- Reporting systems.
- Non-critical read operations.

Eventual consistency is not a promise that replicas will always catch up. Replication failures, conflicting writes, or operational problems can prevent convergence until they are resolved.

## 4. Read Consistency Problems

Let's look at common problems that appear when applications read from replicas.

### Problem 1: Read-After-Write Inconsistency

A user updates their profile and immediately reads it again.

```text
Application
    |
    v
Write to Primary
    |
    v
Primary commits update
    |
    v
Application returns success
    |
    v
Read from Replica
    |
    v
Old profile data returned
```

The user sees the old data even though the update succeeded.

**Possible solution:** Route subsequent reads to the primary or wait until the selected replica has applied the required transaction.

### Problem 2: Non-Monotonic Reads

A user reads the same record twice but sees an older version the second time.

Example:

```text
First read:
Replica 1 returns version 10.

Second read:
Replica 2 returns version 8.
```

This can happen when replicas are at different replication positions.

From the user's perspective, the data appears to move backwards.

**Possible solution:** Use session-level routing, or ensure reads use replicas that have reached at least the previously observed replication position.

### Problem 3: Inconsistent Reads Across Multiple Records

Suppose an application transfers money between two accounts.

The transaction updates both records:

```text
Account A: 5000 -> 3000
Account B: 1000 -> 3000
```

If the application reads Account A from one replica and Account B from another replica at different replication positions, it might observe a combination of old and new values.

The resulting view may not represent any valid committed transaction state.

**Possible solution:** Read related data from the same consistent database snapshot or use a database and transaction model that provides the required consistency guarantee.

## 5. Consistency Strategies

There is no single routing strategy that works for every application.

The correct choice depends on how fresh the data needs to be.

### Strategy 1: Always Read from Primary

Send all reads and writes to the primary.

Advantages:
- Simple application behavior.
- Avoids replica lag for reads against the primary.
- Easier to reason about read-after-write behavior.

Disadvantages:
- The primary handles all read traffic.
- Read replicas provide no benefit for application reads.
- The primary can become a performance bottleneck.

This is often a reasonable choice for small applications or critical operations.

### Strategy 2: Read from Replicas

Distribute read traffic across replicas.

Advantages:
- Reduces read pressure on the primary.
- Allows read traffic to scale across multiple nodes.
- Useful for workloads that tolerate some staleness.

Disadvantages:
- Replicas may return stale data.
- Different replicas may have different replication positions.
- Application logic must account for consistency requirements.

### Strategy 3: Session-Based Consistency

After a user performs a write, route that user's subsequent reads to the primary for a defined period or until a consistency condition is satisfied.

Example:

```text
User Session
     |
     v
Write to Primary
     |
     v
Mark Session as Recently Written
     |
     v
Next Reads Go to Primary
     |
     v
Resume Replica Reads
```

This improves the user experience without forcing every user to read from the primary.

However, a fixed time window is only a heuristic. It does not guarantee that a replica has caught up. A replication-position check provides a stronger guarantee when supported by the database.

### Strategy 4: Position-Based Consistency

Some databases expose transaction-log positions that can be used to determine replication progress.

A simplified approach:

1. The primary commits a transaction.
2. The application captures the transaction's commit position.
3. The application selects a replica.
4. It checks whether the replica has applied at least that position.
5. The read is sent to that replica only when the condition is satisfied.

If the replica has not caught up, the application can wait, choose another replica, or read from the primary.

This is more precise than waiting for an arbitrary number of seconds, but it requires database-specific support and careful handling of timeouts.

## 6. Python Implementation

Let's simulate how different replicas can return different versions of the same record.

The implementation demonstrates:

- Writes on the primary.
- Replicas receiving updates at different times.
- Stale reads.
- Read-after-write protection by routing to the primary.
- Waiting for a replica to reach a required position.

This is an in-memory educational model. The replication position is a simple integer, not a real WAL LSN, GTID, or transaction-log identifier.

### Database Node

```python
class DatabaseNode:
    def __init__(self, name, role="replica"):
        self.name = name
        self.role = role
        self.data = {}
        self.replication_position = 0

    def write(self, key, value):
        if self.role != "primary":
            raise RuntimeError(
                f"{self.name} is not the primary"
            )

        self.replication_position += 1
        self.data[key] = value

        print(
            f"[{self.name}] WRITE: "
            f"{key} = {value}, "
            f"position = {self.replication_position}"
        )

        return self.replication_position

    def replicate_from(self, primary):
        if self.replication_position >= primary.replication_position:
            return

        self.data = primary.data.copy()
        self.replication_position = primary.replication_position

        print(
            f"[{self.name}] Replicated up to "
            f"position {self.replication_position}"
        )

    def read(self, key):
        value = self.data.get(key)

        print(
            f"[{self.name}] READ: "
            f"{key} = {value}, "
            f"position = {self.replication_position}"
        )

        return value
```

### Consistency-Aware Router

```python
class ConsistencyRouter:
    def __init__(self, primary, replicas):
        self.primary = primary
        self.replicas = replicas
        self.replica_index = 0

    def write(self, key, value):
        # Writes always go to the primary.
        position = self.primary.write(key, value)

        return position

    def read(self, key, required_position=None):
        # No replicas available: use primary.
        if not self.replicas:
            return self.primary.read(key)

        # If a required position is provided,
        # select only a replica that has applied it.
        if required_position is not None:
            eligible_replicas = [
                replica
                for replica in self.replicas
                if replica.replication_position >= required_position
            ]

            if not eligible_replicas:
                print(
                    "[ROUTER] No replica has reached "
                    "the required position. Reading from primary."
                )

                return self.primary.read(key)

            replica = eligible_replicas[
                self.replica_index % len(eligible_replicas)
            ]

            self.replica_index += 1

            return replica.read(key)

        # Without a consistency requirement,
        # distribute reads using round robin.
        replica = self.replicas[
            self.replica_index % len(self.replicas)
        ]

        self.replica_index += 1

        return replica.read(key)
```

### Running the Example

```python
if __name__ == "__main__":

    primary = DatabaseNode(
        "Primary",
        role="primary"
    )

    replica_1 = DatabaseNode("Replica-1")
    replica_2 = DatabaseNode("Replica-2")

    router = ConsistencyRouter(
        primary=primary,
        replicas=[replica_1, replica_2]
    )

    # Initial write.
    router.write("product_price", 1500)

    # Both replicas receive the initial data.
    replica_1.replicate_from(primary)
    replica_2.replicate_from(primary)

    print("\n--- Update Product Price ---")

    # Update the price on primary.
    required_position = router.write(
        "product_price",
        1800
    )

    print("\n--- Read Without Consistency Requirement ---")

    # Replica 1 and Replica 2 are both behind.
    router.read("product_price")
    router.read("product_price")

    print("\n--- Replicate Only to Replica 1 ---")

    replica_1.replicate_from(primary)

    print("\n--- Read With Required Position ---")

    # Router should choose Replica 1 because it has
    # applied the required transaction position.
    router.read(
        "product_price",
        required_position=required_position
    )

    print("\n--- Read From Replica That Is Still Behind ---")

    # Replica 2 is still behind. No eligible replica
    # is available for this required position.
    router.replicas = [replica_2]

    router.read(
        "product_price",
        required_position=required_position
    )
```

### Expected Output

```text
[Primary] WRITE: product_price = 1500, position = 1
[Replica-1] Replicated up to position 1
[Replica-2] Replicated up to position 1

--- Update Product Price ---
[Primary] WRITE: product_price = 1800, position = 2

--- Read Without Consistency Requirement ---
[Replica-1] READ: product_price = 1500, position = 1
[Replica-2] READ: product_price = 1500, position = 1

--- Replicate Only to Replica 1 ---
[Replica-1] Replicated up to position 2

--- Read With Required Position ---
[Replica-1] READ: product_price = 1800, position = 2

--- Read From Replica That Is Still Behind ---
[ROUTER] No replica has reached the required position. Reading from primary.
[Primary] READ: product_price = 1800, position = 2
```

The example demonstrates an important routing decision.

A replica should not serve a read that requires a newer transaction position than the replica has applied.

Instead, the router can choose another eligible replica or fall back to the primary.

In production, this decision also needs a timeout. Waiting indefinitely for a lagging replica can make the application unavailable even when the primary is healthy.

## 7. Production Considerations

### Define Consistency Requirements Per Operation

Not every read needs the same freshness guarantee.

For example:

| Operation | Suggested consistency |
|---|---|
| Product browsing | Eventual consistency may be acceptable |
| User profile immediately after update | Read-after-write consistency |
| Payment status | Stronger consistency requirement |
| Analytics dashboard | Eventual consistency may be acceptable |
| Inventory reservation | Transactional consistency |
| Order confirmation | Read the authoritative committed state |

The application should make these decisions explicitly.

### Avoid Fixed Replication-Lag Assumptions

A common shortcut is to route reads to the primary for five seconds after a write.

This may work under normal conditions, but replication lag can exceed five seconds during heavy load or network problems.

A fixed delay does not prove that a replica has caught up.

### Handle Replica Timeouts

If the application waits for a replica to reach a required position, it needs a timeout and fallback policy.

Possible actions:

- Try another eligible replica.
- Read from the primary.
- Return a temporary error if the primary cannot serve the request.

The correct choice depends on the operation's consistency requirement and latency budget.

### Be Careful With Transactions

A transaction that reads related records should not casually switch between different replicas.

Doing so can produce a view assembled from different replication states.

Use a consistent transaction snapshot and a database-supported consistency model where required.

### Understand the Database's Guarantees

PostgreSQL, MySQL, and distributed databases expose different replication and consistency mechanisms.

Do not assume that a generic replication position or acknowledgment means the same thing across database engines.

Understand whether the database has received, persisted, or applied a transaction before treating a replica as current.

## 8. Key Takeaways

- Replicas can temporarily return stale data.
- Strong consistency and eventual consistency provide different guarantees.
- Read-after-write inconsistency is a common application-level problem.
- Non-monotonic reads can occur when requests move between replicas at different positions.
- Session-based and position-based routing can improve read consistency.
- A fixed waiting period does not guarantee replication completion.
- Consistency requirements should be defined per operation, not applied blindly to every query.

Replication improves read scalability and can support availability, but it also changes how applications observe data.

The database architecture and application routing strategy must agree on the consistency guarantees the system actually provides.

## Next

Continue to [Production Trade-offs](10_production_tradeoffs.md) to bring together replication modes, read/write routing, failover, consistency, and the operational decisions involved in running a replicated database system.
