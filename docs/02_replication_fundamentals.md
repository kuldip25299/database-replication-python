# 02. What Is Database Replication?

## 1. Introduction

Database replication is the process of maintaining copies of data across multiple database servers.

Instead of depending on a single database server, an application can use multiple database nodes that contain the same data.

One node may handle writes, while other nodes maintain copies and serve read requests.

The main goals of replication are:

- Improve read scalability.
- Increase database availability.
- Maintain additional copies of data.
- Support recovery when a database node fails.
- Serve geographically distributed users more efficiently.

Replication is commonly used in applications where database availability and read performance are important.

## 2. Understanding Database Nodes

Before looking at replication architecture, let's understand what a database node means.

A database node is an individual database server participating in a database system.

For example, an application may have three database nodes:

```text
Database Node 1
Database Node 2
Database Node 3
```

Each node can run its own database instance and maintain its own copy of data.

In a replicated architecture, these nodes communicate with each other to synchronize changes.

## 3. Primary-Replica Architecture

One of the most common replication models is primary-replica replication.

It has two main roles.

### Primary

The primary database is responsible for accepting write operations.

Examples:

- Creating a user.
- Updating an order.
- Placing a payment record.
- Updating product inventory.

When a write operation happens, the primary records the change and sends it to the replicas.

### Replica

A replica maintains a copy of the primary database's data.

Depending on the architecture, replicas can handle read requests.

For example:

- Product listings.
- User profile reads.
- Order history.
- Reporting queries.

A basic architecture looks like this:

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
              |               ^
              |               |
              +------------ Replica 2
                Replication
```

The important distinction is that the primary is responsible for writes, while replicas receive and apply changes from the primary.

## 4. How Does Replication Work?

Let's walk through a simple example.

Imagine an e-commerce application with the following user record:

```python
{
    "user_id": 101,
    "name": "Alice",
    "city": "Mumbai"
}
```

Initially, the record exists on the primary database.

Now Alice updates her city to Pune.

### Step 1: Application Sends a Write

The application sends the update request to the primary.

```text
UPDATE users
SET city = 'Pune'
WHERE user_id = 101;
```

### Step 2: Primary Applies the Change

The primary updates its local data.

```python
{
    "user_id": 101,
    "name": "Alice",
    "city": "Pune"
}
```

### Step 3: Primary Sends the Change to Replicas

The primary makes the change available to the replication mechanism.

The replicas receive and apply the change according to the configured replication strategy.

### Step 4: Replicas Update Their Copies

After applying the change, the replicas contain the updated record.

```text
Primary:
Alice -> Pune

Replica 1:
Alice -> Pune

Replica 2:
Alice -> Pune
```

The important point is that replicas do not necessarily update at exactly the same time as the primary.

That depends on whether replication is synchronous or asynchronous.

We will explore that difference in later sections.

## 5. What Actually Gets Replicated?

Replication systems need a way to communicate database changes.

A common mechanism is a database transaction log.

For example, relational databases maintain logs that record changes made by transactions.

The replication process can read these changes and send them to replica nodes.

A simplified flow:

```text
Application Write
       |
       v
Primary Database
       |
       v
Transaction Log
       |
       v
Replication Process
       |
       +---------> Replica 1
       |
       +---------> Replica 2
       |
       +---------> Replica 3
```

Depending on the database, replication may transfer:

- Transaction log records.
- Write-ahead log (WAL) records.
- Binary log events.
- Logical changes.
- Database-specific replication events.

The exact mechanism depends on the database engine and replication configuration.

Our Python implementation will simulate this process using operations and in-memory data structures.

## 6. Replication vs. Sharding

Replication and sharding are often discussed together, but they solve different problems.

### Replication

Replication maintains copies of the same data across multiple nodes.

For example:

```text
Primary
  |
  +---- Replica 1
  |
  +---- Replica 2
```

Each node is intended to contain the same logical dataset.

### Sharding

Sharding distributes different parts of the dataset across multiple nodes.

For example:

```text
Shard 1: Users 1 - 1000
Shard 2: Users 1001 - 2000
Shard 3: Users 2001 - 3000
```

Each shard contains only a portion of the overall dataset.

### Comparison

| Area | Replication | Sharding |
|---|---|---|
| Main purpose | Availability and read scalability | Data and write workload distribution |
| Data placement | Copies of the same data | Different portions of data |
| Read scaling | Distribute reads across replicas | Route reads to the correct shard |
| Write handling | Usually writes go to primary | Writes go to the responsible shard |
| Data redundancy | Yes, across replicas | Not necessarily |
| Complexity | Replication and consistency | Partitioning and query routing |

In real systems, both approaches can be combined.

For example, an application may have four shards, with each shard having one primary and two replicas.

## 7. Replication vs. Backup

Replication is not the same as backup.

This is an important distinction.

### Replication

Replication keeps database copies synchronized.

If a record is accidentally deleted on the primary, that deletion may also be replicated to all replicas.

Replication helps with node failure, but it does not automatically protect against logical data loss.

### Backup

A backup is a separate copy of data that can be restored to an earlier point in time.

Backups help recover from situations such as:

- Accidental deletion.
- Corrupted records.
- Incorrect application updates.
- Database corruption.
- Some security incidents.

| Area | Replication | Backup |
|---|---|---|
| Purpose | Maintain copies across nodes | Recover lost or damaged data |
| Synchronization | Usually continuous | Scheduled or continuous backup process |
| Node failure | Can support failover | Usually requires restore |
| Accidental deletion | May propagate deletion | Can restore earlier data |
| Historical recovery | Not inherently provided | Depends on backup retention and point-in-time recovery |

A production system often needs both.

## 8. Different Replication Models

Replication can be implemented in different ways.

The most common approaches we will study are:

### Synchronous Replication

The primary waits for the required replica acknowledgment before confirming a write.

This can provide stronger durability or consistency guarantees, depending on the acknowledgment policy.

However, it can increase write latency and make writes dependent on replica availability.

### Asynchronous Replication

The primary confirms a write without waiting for replicas to apply it.

Replicas catch up later.

This usually provides lower write latency, but replicas can temporarily contain stale data.

### Semi-Synchronous Replication

The primary waits for acknowledgment from at least one replica, rather than every replica.

The exact guarantee depends on what the acknowledgment confirms. Receiving a change is not always the same as having applied it.

We will implement synchronous and asynchronous simulations in this repository.

## 9. A Simple Python Representation

Before implementing complete replication strategies, let's represent the primary and replica nodes using Python dictionaries.

```python
class DatabaseNode:
    def __init__(self, name):
        self.name = name
        self.data = {}

    def insert(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)


primary = DatabaseNode("primary")
replica = DatabaseNode("replica")

primary.insert(
    101,
    {
        "user_id": 101,
        "name": "Alice",
        "city": "Mumbai",
    },
)

# Simulate copying the record to the replica.
replica.insert(101, primary.get(101))

print("Primary:", primary.get(101))
print("Replica:", replica.get(101))
```

This is not a real database replication engine.

It simply demonstrates the idea of maintaining the same record on multiple nodes.

Later examples will introduce a replication manager to handle synchronization, delayed replication, read routing, and failover.

## 10. Important Concepts to Remember

Before moving forward, understand these concepts:

**Primary:** The database node responsible for accepting writes.

**Replica:** A database node maintaining a copy of the primary's data.

**Replication:** The process of transferring and applying data changes across nodes.

**Replication lag:** The delay between a change being committed on the primary and becoming available on a replica.

**Failover:** The process of switching database responsibility to another node after a failure.

**Consistency:** The guarantees that determine what data a read operation can observe.

These concepts will appear throughout the remaining examples.

## 11. Key Takeaways

- Replication maintains copies of data across multiple database nodes.
- Primary-replica architecture is a common replication model.
- The primary generally handles writes, while replicas can serve reads.
- Database transaction logs are commonly used to propagate changes.
- Replication and sharding solve different scaling problems.
- Replication is not a replacement for backups.
- Synchronous and asynchronous replication have different latency and consistency trade-offs.

**Next:** [Primary-Replica Architecture](03_primary_replica_architecture.md)
