# Failover and Recovery

## 1. The Problem

Imagine an application running with one primary database and two read replicas.

The primary handles all write operations, while replicas serve read traffic.

Everything works until the primary database suddenly becomes unavailable.

For example:

- The database server crashes.
- The underlying machine fails.
- A network issue makes the primary unreachable.
- The database process stops unexpectedly.
- Storage failure prevents new writes.

Now the application cannot process write operations.

Read replicas may still be running, but they cannot automatically accept writes just because the primary is unavailable.

The system needs a way to promote an eligible replica and make it the new primary.

This process is called **database failover**.

## 2. What Is Database Failover?

Failover is the process of switching database responsibilities from a failed primary to another available database node.

In a primary-replica architecture:

- The primary accepts writes.
- Replicas receive changes from the primary.
- If the primary fails, an eligible replica can be promoted.
- Applications are redirected to the new primary.

### Before Failover

```text
              Application
                   |
                   v
               Primary
                /    \
               v      v
          Replica 1  Replica 2

          Primary handles writes
          Replicas handle reads
```

### After Failover

```text
              Application
                   |
                   v
              Replica 1
              (New Primary)
                |
                v
             Replica 2

          Replica 1 handles writes
          Replica 2 receives changes
```

The important point is that failover changes the role of a database node.

It is not simply redirecting traffic to any available replica.

## 3. Manual vs Automatic Failover

There are two common approaches.

### Manual Failover

An administrator or database operator identifies the failure and promotes a replica.

Typical steps:

1. Detect that the primary is unavailable.
2. Check the replication status of available replicas.
3. Select an eligible replica.
4. Promote it to primary.
5. Update application routing.
6. Reconfigure remaining replicas to follow the new primary.

Manual failover provides control but usually takes longer.

It may be appropriate for smaller systems where occasional downtime is acceptable.

### Automatic Failover

A monitoring or orchestration system detects primary failure and performs the failover process.

A simplified flow:

```text
Primary Database
       |
       v
Health Monitoring
       |
       v
Primary Unavailable?
       |
       v
Select Eligible Replica
       |
       v
Promote Replica
       |
       v
Update Database Routing
       |
       v
Application Resumes Writes
```

Automatic failover can reduce recovery time, but it introduces more operational complexity.

A health check alone is not enough to safely promote a replica. The system must also ensure that the old primary cannot continue accepting writes.

## 4. Choosing the Right Replica

This is one of the most important parts of failover.

Suppose we have three database nodes:

| Node | Last replicated position |
|---|---:|
| Primary | 1050 |
| Replica 1 | 1048 |
| Replica 2 | 1020 |

The primary fails.

Which replica should become the new primary?

Replica 1 is the better candidate because it has received more of the primary's changes.

If we promote Replica 2, some transactions that Replica 1 already has may be lost from the new primary's history.

In a real database, replication positions represent engine-specific transaction-log progress, such as PostgreSQL WAL positions or MySQL GTIDs/binlog positions.

A simple integer is enough for our learning simulation, but production systems need database-aware position comparison.

**Important:** The most up-to-date replica is not automatically safe to promote. The system must also verify that it is healthy, eligible, and not part of a conflicting history.

## 5. The Risk of Data Loss

Failover behavior depends heavily on the replication mode.

### Synchronous Replication

If the configured synchronous acknowledgment policy was satisfied before a transaction was acknowledged, an eligible replica may already have the required transaction.

However, the exact guarantee depends on what the database acknowledges:

- Receiving the transaction log.
- Persisting the log to durable storage.
- Applying the transaction.

These are different conditions.

### Asynchronous Replication

With asynchronous replication, the primary can acknowledge a write before replicas receive it.

Consider this sequence:

```text
1. Application sends a write.
2. Primary commits the transaction.
3. Primary returns success.
4. Replica has not received the transaction.
5. Primary crashes.
6. Replica is promoted.
```

The application received a successful response, but the promoted replica may not contain that transaction.

This is a real data-loss risk.

The amount of potentially lost data depends on replication lag and the failure timing.

## 6. The Split-Brain Problem

Failover can introduce a more dangerous problem than temporary unavailability.

Imagine the primary becomes unreachable because of a network partition.

The monitoring system assumes the primary has failed and promotes Replica 1.

But the old primary is still running and can accept writes from applications that can reach it.

Now two nodes believe they are primary.

```text
           Application A
                |
                v
          Old Primary
                |
             Writes A


           Application B
                |
                v
          New Primary
                |
             Writes B
```

Both databases may accept different writes.

This is called **split brain**.

When connectivity returns, the two database histories may conflict.

Simply restarting replication does not safely resolve those conflicting writes.

### Preventing Split Brain

Production systems use techniques such as:

- Leader election with a coordination mechanism.
- Fencing to prevent the old primary from accepting writes.
- Quorum-based decisions where supported by the architecture.
- Database-aware promotion and recovery procedures.
- Network and storage controls that prevent stale leaders from operating.

The critical requirement is that only one node should be authorized to accept writes at a time.

A timeout or failed health check alone cannot prove that the old primary is permanently dead.

## 7. Recovery Time and Recovery Point

Two important measurements help evaluate a failover strategy.

### Recovery Time Objective (RTO)

RTO is the maximum acceptable time required to restore service after a failure.

For example:

If the application must resume writes within 60 seconds, the failover process should be designed and tested against that target.

### Recovery Point Objective (RPO)

RPO is the maximum acceptable amount of data loss, measured in time.

For example:

If the RPO is 5 seconds, the system should be designed so that a failure does not cause more than approximately 5 seconds of acknowledged data to be lost.

These targets influence the choice of replication mode, infrastructure, and failover strategy.

A system with strict RPO and RTO requirements needs stronger guarantees and more careful coordination.

## 8. Python Implementation

Let's simulate a basic primary failure and replica promotion.

This implementation demonstrates:

- One primary database.
- Multiple replicas.
- Replication positions.
- Selecting the most up-to-date eligible replica.
- Promoting a replica.
- Redirecting writes to the new primary.

This is an educational simulation. It does not implement real failure detection, durable transaction logs, distributed consensus, fencing, or network communication.

### Database Node

```python
class DatabaseNode:
    def __init__(self, name, role="replica"):
        self.name = name
        self.role = role
        self.data = {}
        self.replication_position = 0
        self.available = True

    def write(self, key, value):
        if not self.available:
            raise RuntimeError(
                f"{self.name} is unavailable"
            )

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

    def replicate_from(self, primary):
        if not self.available:
            return

        self.data = primary.data.copy()
        self.replication_position = (
            primary.replication_position
        )

        print(
            f"[{self.name}] Replicated up to position "
            f"{self.replication_position}"
        )

    def promote(self):
        if not self.available:
            raise RuntimeError(
                f"Cannot promote unavailable node: {self.name}"
            )

        self.role = "primary"

        print(
            f"[{self.name}] Promoted to PRIMARY"
        )
```

### Failover Manager

```python
class FailoverManager:
    def __init__(self, primary, replicas):
        self.primary = primary
        self.replicas = replicas

    def detect_primary_failure(self):
        if not self.primary.available:
            print(
                f"[FAILOVER] Primary "
                f"{self.primary.name} is unavailable"
            )
            return True

        return False

    def select_replica(self):
        healthy_replicas = [
            replica
            for replica in self.replicas
            if replica.available
        ]

        if not healthy_replicas:
            raise RuntimeError(
                "No healthy replica available for promotion"
            )

        # Select the healthy replica with the highest
        # replication position.
        candidate = max(
            healthy_replicas,
            key=lambda replica: replica.replication_position
        )

        print(
            f"[FAILOVER] Selected {candidate.name} "
            f"at position {candidate.replication_position}"
        )

        return candidate

    def promote_replica(self):
        if not self.detect_primary_failure():
            print("[FAILOVER] Primary is still available")
            return self.primary

        new_primary = self.select_replica()

        new_primary.promote()

        self.primary = new_primary

        # Remaining replicas must follow the new primary.
        self.replicas = [
            replica
            for replica in self.replicas
            if replica is not new_primary
        ]

        print(
            f"[FAILOVER] New primary: {self.primary.name}"
        )

        return self.primary
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

    replicas = [replica_1, replica_2]

    # Initial writes.
    primary.write("user_1", "Kuldip")
    primary.write("user_2", "Rahul")
    primary.write("user_3", "Amit")

    # Replicate all changes to Replica 1.
    replica_1.replicate_from(primary)

    # Replica 2 is intentionally behind.
    replica_2.data = {
        "user_1": "Kuldip"
    }
    replica_2.replication_position = 1

    print("\n--- Before Failure ---")

    print(
        f"Primary position: "
        f"{primary.replication_position}"
    )

    print(
        f"Replica 1 position: "
        f"{replica_1.replication_position}"
    )

    print(
        f"Replica 2 position: "
        f"{replica_2.replication_position}"
    )

    # Simulate primary failure.
    print("\n--- Primary Failure ---")

    primary.available = False

    # Perform failover.
    failover_manager = FailoverManager(
        primary,
        replicas
    )

    new_primary = failover_manager.promote_replica()

    # Application now writes to the new primary.
    print("\n--- Write After Failover ---")

    new_primary.write(
        "user_4",
        "Priya"
    )

    print("\n--- New Primary Data ---")
    print(new_primary.data)
```

### Expected Output

```text
[Primary] WRITE: user_1 = Kuldip, position = 1
[Primary] WRITE: user_2 = Rahul, position = 2
[Primary] WRITE: user_3 = Amit, position = 3
[Replica-1] Replicated up to position 3

--- Before Failure ---
Primary position: 3
Replica 1 position: 3
Replica 2 position: 1

--- Primary Failure ---
[FAILOVER] Primary Primary is unavailable
[FAILOVER] Selected Replica-1 at position 3
[Replica-1] Promoted to PRIMARY
[FAILOVER] New primary: Replica-1

--- Write After Failover ---
[Replica-1] WRITE: user_4 = Priya, position = 4

--- New Primary Data ---
{
    'user_1': 'Kuldip',
    'user_2': 'Rahul',
    'user_3': 'Amit',
    'user_4': 'Priya'
}
```

## 9. What This Implementation Does Not Handle

The example deliberately keeps failover simple.

A production system needs additional safeguards:

| Concern | Production requirement |
|---|---|
| Failure detection | Reliable monitoring and failure detection |
| Replica selection | Database-aware transaction-position comparison |
| Split brain | Leader election and fencing |
| Data loss | Explicit replication and durability guarantees |
| Application routing | Update connections to the new primary |
| Old primary recovery | Rejoin safely as a replica or rebuild it |
| Concurrent failover | Prevent multiple promotion attempts |
| Recovery | Validate data and replication state before resuming normal operation |

One particularly important detail: after promotion, the old primary must not simply reconnect and start accepting writes again. It needs a controlled recovery process.

## 10. Key Takeaways

- Failover promotes an eligible replica when the primary becomes unavailable.
- Replica selection should consider replication progress and node health.
- Asynchronous replication can lose acknowledged writes during failover.
- Split brain can create conflicting database histories.
- RTO and RPO define important recovery requirements.
- Promoting a replica is only one part of failover; application routing and old-primary recovery matter too.

A database architecture should be evaluated not only by how it handles normal traffic, but also by what happens when its most important node disappears.

## Next

Continue to [Replication Consistency](09_replication_consistency.md) to understand the consistency guarantees applications can expect when data is replicated across multiple database nodes.
