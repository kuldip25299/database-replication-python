# 03. Primary-Replica Architecture

## 1. Introduction

Primary-replica architecture is one of the most common approaches to database replication.

The idea is straightforward:

- One database node acts as the primary.
- Other database nodes act as replicas.
- The primary handles write operations.
- Replicas receive and apply changes from the primary.
- Applications can distribute eligible read operations across replicas.

This architecture helps reduce read pressure on the primary and provides additional database nodes that can be used during failure recovery.

Let's understand how the architecture works before implementing it.

## 2. Basic Architecture

Consider an application with one primary database and two replicas.

```text
                    Application
                         |
                 +-------+-------+
                 |               |
                 v               v
               Writes           Reads
                 |               |
                 v               v
              Primary         Replica 1
                 |
                 |
          Replication Stream
                 |
                 v
              Replica 2
```

The primary is responsible for accepting writes.

When a write is committed, the change is propagated to the replicas.

The replicas maintain their own copies of the data and can serve read requests according to the application's consistency requirements.

## 3. Responsibilities of Each Node

### Primary Database

The primary is the main write node.

Its responsibilities include:

- Accepting insert, update, and delete operations.
- Validating and committing transactions.
- Recording changes in its transaction log.
- Making changes available to the replication process.
- Managing replication metadata and progress.

For a simple example, imagine a user updating their profile.

```python
{
    "user_id": 101,
    "name": "Alice",
    "city": "Pune"
}
```

The update is first committed on the primary.

### Replica Database

A replica maintains a copy of the primary's data.

Its responsibilities include:

- Receiving replicated changes.
- Applying changes in the correct order.
- Maintaining replication progress.
- Serving eligible read requests.
- Reporting its replication health and lag.

A replica is not automatically guaranteed to have the latest committed data.

That depends on the replication strategy and whether it has applied the latest changes.

## 4. Write Request Flow

Let's follow an order creation request.

Assume a user places an order worth ₹5,000.

### Step 1: Application Receives the Request

The application receives the order request and sends it to the primary database.

### Step 2: Primary Processes the Write

The primary creates the order record.

```python
{
    "order_id": 5001,
    "user_id": 101,
    "amount": 5000,
    "status": "confirmed"
}
```

### Step 3: Primary Commits the Transaction

The primary commits the transaction and records the corresponding changes.

### Step 4: Replication Begins

The replication process transfers the committed changes to the replicas.

### Step 5: Replicas Apply the Changes

Each replica applies the changes to its local database.

The exact point at which the application receives a successful response depends on the replication mode.

With asynchronous replication, the primary can respond before replicas apply the change.

With synchronous replication, the primary waits for the configured acknowledgment condition.

This difference is important and will be covered in the next documentation files.

## 5. Read Request Flow

One of the main reasons to introduce replicas is to distribute read traffic.

Suppose the application receives:

- 1,000 write requests.
- 20,000 read requests.

Sending every read to the primary can create unnecessary pressure.

Instead, the application can route eligible reads to replicas.

```text
                    Application
                         |
                 +-------+-------+
                 |               |
                 v               v
               Writes           Reads
                 |               |
                 v               |
              Primary            |
                 |               |
           Replication           |
             /     \             |
            v       v            |
        Replica 1  Replica 2 <---+
```

For example:

| Operation | Database node |
|---|---|
| Create order | Primary |
| Update profile | Primary |
| Read product catalog | Replica 1 |
| Read order history | Replica 2 |
| Generate report | Replica 1 or 2 |

This is commonly called read/write splitting.

However, not every read should automatically go to a replica.

If a user updates their profile and immediately reads it, a lagging replica may return the previous value.

Applications need to account for this behavior.

## 6. Why Replicas Need Their Own Storage

Each replica maintains its own local copy of the data.

For example:

```text
Primary
  users:
    101 -> Alice
    102 -> Bob

Replica 1
  users:
    101 -> Alice
    102 -> Bob

Replica 2
  users:
    101 -> Alice
    102 -> Bob
```

These are separate database instances.

Replication keeps them synchronized, but they do not share one common memory space.

This is important because each replica can:

- Run independently.
- Handle its own read traffic.
- Experience independent failures.
- Have different replication progress.

## 7. What Happens When a Replica Goes Down?

Suppose Replica 1 becomes unavailable.

```text
              Primary
                 |
          +------+------+
          |             |
          v             X
       Replica 2    Replica 1
                       DOWN
```

The primary can generally continue accepting writes.

The application can route eligible reads to Replica 2 or back to the primary.

When Replica 1 comes back online, it needs to catch up on the changes it missed.

The database's replication mechanism determines whether it can resume from its previous position or needs a new synchronization process.

A replica failure does not necessarily require application downtime.

However, losing replicas reduces redundancy and read capacity.

## 8. What Happens When the Primary Goes Down?

Now consider a more serious situation.

The primary database becomes unavailable.

```text
              Application
                   |
                   X
                Primary
                FAILED
                   |
             +-----+-----+
             |           |
             v           v
          Replica 1   Replica 2
```

The application can no longer send writes to the primary.

A replica may be promoted to become the new primary.

For example:

```text
Before Failure:

Primary
  |
  +---- Replica 1
  |
  +---- Replica 2


After Failover:

Primary (Former Replica 1)
  |
  +---- Replica 2
```

This process is called failover.

But promotion requires careful handling.

Before promoting a replica, the system needs to consider:

- Whether the replica is healthy.
- Whether it has received the latest committed changes.
- Whether another primary is still active.
- Whether the old primary can accidentally continue accepting writes.
- How applications will discover the new primary.

Promoting a stale replica can result in lost acknowledged writes.

Allowing two primaries to accept writes can create split-brain problems.

We will explore failover in a dedicated implementation.

## 9. Primary-Replica Does Not Automatically Mean High Availability

Having multiple replicas does not automatically make a database highly available.

A production system also needs:

- Health checks.
- Failure detection.
- A promotion strategy.
- Primary discovery.
- Connection management.
- Replication monitoring.
- Split-brain protection.
- Recovery procedures.

For example, if the primary fails but the application does not know which replica should become primary, the replicas alone cannot restore write availability.

The architecture needs a mechanism to coordinate these decisions.

## 10. Architecture for This Repository

We'll use a simplified primary-replica architecture throughout the Python examples.

The design will contain:

### DatabaseNode

Represents an individual database node.

It will maintain:

- Node name.
- Local data.
- Basic insert, update, delete, and read operations.
- Node role or availability state where required.

### Primary Database

Responsible for processing write operations.

It will also provide the changes that need to be replicated.

### Replica Database

Maintains a separate copy of the primary's data.

It will apply replicated changes.

### Replication Manager

Coordinates the replication process.

Depending on the example, it will simulate:

- Immediate replication.
- Delayed replication.
- Replica synchronization.
- Replication progress.

### Read/Write Router

Routes write operations to the primary and eligible read operations to replicas.

### Failover Manager

Simulates primary failure and promotes a suitable replica.

We will introduce these components gradually instead of building the entire system in one large implementation.

## 11. Important Design Decisions

A few decisions will guide the examples.

**Separate storage:** Every database node will have its own dictionary. We will not use one shared dictionary for all nodes.

**Explicit replication:** Changes will be copied through a replication mechanism. Updating the primary must not silently update every replica.

**Deterministic behavior:** Examples will use controlled operations so that replication lag and failover can be reproduced.

**No external infrastructure:** The repository will use Python's standard library and in-memory data structures.

These choices keep the examples focused on the mechanics of replication rather than database installation or deployment.

## 12. Key Takeaways

- Primary-replica architecture separates write responsibility from read distribution.
- The primary processes writes and provides changes for replication.
- Replicas maintain independent copies of the data.
- Replicas can serve reads, but may temporarily contain stale data.
- Replica failure and primary failure require different recovery approaches.
- Failover needs coordination to prevent data loss and split-brain.
- Multiple replicas alone do not guarantee high availability.

**Next:** [Synchronous Replication](04_synchronous_replication.md)
