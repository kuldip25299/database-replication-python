# 06. Understanding Replication Lag

## 1. Introduction

Replication lag is the delay between a change being committed on the primary database and that change becoming available on a replica.

In an asynchronous replication architecture, the primary can acknowledge a write before replicas have applied it.

This means the primary and replicas may temporarily contain different versions of the data.

For example:

```text
Primary:
  user_id: 101
  city: Pune

Replica 1:
  user_id: 101
  city: Mumbai
```

The primary has the latest value, but Replica 1 still has the old value.

This is replication lag.

It is expected in asynchronous replication, but excessive lag can create application problems.

## 2. How Replication Lag Happens

Consider an application that receives 1,000 write operations per second.

The primary processes these writes and makes the changes available to replicas.

However, replicas may process changes more slowly.

For example:

- Primary generates 1,000 changes per second.
- Replica applies only 700 changes per second.

The replica cannot keep up with the incoming changes.

As a result, pending replication work continues to accumulate.

```text
Primary
  |
  | 1000 changes/second
  v
Replication Stream
  |
  v
Replica
  |
  | 700 changes/second
  v
Pending changes accumulate
```

The longer this continues, the further behind the replica becomes.

## 3. Common Causes of Replication Lag

Replication lag can happen for several reasons.

### 3.1 High Write Traffic

The primary may generate changes faster than replicas can apply them.

For example:

- Bulk imports.
- Large order-processing workloads.
- High-volume user activity.
- Large batches of updates.

If replicas cannot process incoming changes at the same rate, lag increases.

### 3.2 Network Latency

Replication requires communication between database nodes.

If the primary and replica are geographically distant, network latency can increase the time required to transfer changes.

Network congestion or packet loss can make the situation worse.

### 3.3 Slow Replica Hardware

A replica with insufficient CPU, memory, or disk I/O may struggle to apply changes at the required rate.

For example, the primary may use high-performance storage while the replica runs on slower storage.

This creates an imbalance between write generation and replication processing.

### 3.4 Long-Running Queries

Read queries running on a replica can compete with replication workers for CPU, memory, and disk resources.

For example, a large analytical query may consume significant resources while the replica is applying incoming changes.

This can delay replication.

### 3.5 Large Transactions

A transaction that updates millions of records can take considerable time to transfer and apply.

Depending on the database engine, a replica may not make the transaction's changes visible until the transaction has been applied and committed.

This can create a noticeable increase in lag.

### 3.6 Replication Worker Bottlenecks

Some database systems can apply independent transactions in parallel.

However, ordering requirements, conflicts, dependencies, and database configuration may limit parallel processing.

If replication workers cannot keep up, pending changes accumulate.

## 4. Understanding Replication Lag with an Example

Imagine an e-commerce application.

A customer places an order:

```python
{
    "order_id": 5001,
    "user_id": 101,
    "amount": 5000,
    "status": "confirmed"
}
```

The primary commits this order at 10:00:00.

Replica 1 applies the change at 10:00:02.

Replica 2 applies it at 10:00:05.

The approximate application delays are:

| Database node | Change applied | Delay |
|---|---|---:|
| Primary | 10:00:00 | 0 seconds |
| Replica 1 | 10:00:02 | 2 seconds |
| Replica 2 | 10:00:05 | 5 seconds |

If the application reads from Replica 2 at 10:00:03, the order may not be visible yet.

This is why replication lag matters at the application level.

## 5. The Read-After-Write Problem

One of the most common consequences of replication lag is stale data.

Consider this user flow:

1. User updates their profile city to Pune.
2. Primary commits the update.
3. Application returns success.
4. User immediately opens the profile page.
5. Application reads from a replica.
6. Replica still contains Mumbai.

```text
User
 |
 | Update city to Pune
 v
Application
 |
 v
Primary
 |
 | Commit successful
 v
Application returns success
 |
 | Read profile
 v
Replica
 |
 | Old data
 v
Mumbai
```

From the user's perspective, the update appears to have failed.

But the primary contains the correct value.

The problem is that the read was routed to a replica that had not caught up.

## 6. Strategies to Handle Stale Reads

There are several ways to handle this problem.

### 6.1 Read from the Primary After a Write

The simplest approach is to route read-after-write requests to the primary.

For example:

```text
Normal Read:
Application -> Replica

Write:
Application -> Primary

Read Immediately After Write:
Application -> Primary
```

This avoids reading stale data from replicas for that request.

The trade-off is that more reads go to the primary, reducing the benefit of read scaling.

### 6.2 Session-Based Read Routing

An application can remember that a user has recently performed a write.

For a short period, subsequent reads from that user are routed to the primary.

Other users can continue reading from replicas.

This is useful when the application needs read-your-writes behavior without routing every read to the primary.

The implementation needs a clear expiration policy and must account for multiple application servers.

### 6.3 Wait Until the Replica Catches Up

Some database systems expose replication positions or log sequence numbers.

The application can record the position associated with a write and wait until the selected replica has reached that position.

Only then does it route the read to that replica.

This can provide a stronger read-after-write guarantee, but it requires database-specific support and timeout handling.

### 6.4 Route to a Less-Lagged Replica

If multiple replicas are available, the application can choose one with lower measured lag.

This helps reduce stale reads, but low measured lag does not guarantee that a specific write has already been applied.

For strict read-after-write behavior, a known replication position is more reliable than simply choosing the replica with the smallest lag.

## 7. Measuring Replication Lag

Replication lag should be measured and monitored rather than assumed to be zero.

There are different ways to measure it.

### Time-Based Lag

Measures the time difference between when a change was committed on the primary and when it became available on a replica.

Example:

```text
Primary commit: 10:00:00
Replica apply:  10:00:03

Replication lag: 3 seconds
```

### Position-Based Lag

Database systems often use log positions, offsets, or sequence numbers to track replication progress.

For example:

```text
Primary log position: 10500
Replica log position: 10200

Replica is behind by 300 log positions.
```

This shows how far the replica has progressed through the primary's change stream.

However, log positions are not necessarily equivalent to a fixed amount of time or a fixed number of transactions.

### Queue-Based Lag

In a simplified replication system, we can measure the number of pending events waiting to be applied.

```text
Pending replication events: 250
```

This is useful for our Python simulation.

It tells us how much replication work remains, although it does not directly tell us how many seconds behind the replica is.

## 8. Why Replication Lag Is Not Always a Problem

A small amount of lag may be acceptable for many applications.

For example:

- Product catalog browsing.
- Analytics dashboards.
- Historical reports.
- User activity summaries.
- Non-critical search results.

These operations may not require every read to return the latest committed value.

However, other operations need more careful handling:

- Payment status checks.
- Order confirmation.
- Account balance reads.
- Inventory availability.
- User profile updates followed by immediate reads.

The required consistency level should determine where the application reads data.

Not every read needs strong consistency, but critical reads should not depend on an assumption that replicas are always current.

## 9. Replication Lag and Failover

Replication lag also matters during primary failure.

Imagine:

```text
Primary:
  Latest log position = 10500

Replica 1:
  Log position = 10500

Replica 2:
  Log position = 10200
```

The primary fails.

Replica 1 has received the latest changes, while Replica 2 is behind.

Promoting Replica 2 could result in losing changes that were committed on the old primary but not received by Replica 2.

A failover process should consider replica freshness and the database's durability guarantees before promoting a node.

This is particularly important in asynchronous replication.

## 10. Python Simulation: Replication Lag

Let's simulate replication lag using an in-memory queue.

The primary will accept writes and add replication events to a queue.

The replica will process only a limited number of events at a time.

This lets us observe how pending replication work accumulates.

```python
from collections import deque
from copy import deepcopy


class DatabaseNode:
    def __init__(self, name):
        self.name = name
        self.data = {}

    def insert(self, key, value):
        self.data[key] = deepcopy(value)

    def get(self, key):
        return deepcopy(self.data.get(key))


class ReplicationSystem:
    def __init__(self):
        self.primary = DatabaseNode("primary")
        self.replica = DatabaseNode("replica")
        self.replication_queue = deque()

        self.primary_position = 0
        self.replica_position = 0

    def write(self, key, value):
        self.primary.insert(key, value)

        self.primary_position += 1

        self.replication_queue.append({
            "position": self.primary_position,
            "key": key,
            "value": deepcopy(value),
        })

    def process_replication(self, max_events):
        processed = 0

        while self.replication_queue and processed < max_events:
            event = self.replication_queue.popleft()

            self.replica.insert(
                event["key"],
                event["value"],
            )

            self.replica_position = event["position"]
            processed += 1

        return processed

    def get_lag(self):
        return self.primary_position - self.replica_position

    def get_pending_events(self):
        return len(self.replication_queue)


system = ReplicationSystem()

# Primary receives 10 writes.
for user_id in range(1, 11):
    system.write(
        user_id,
        {
            "user_id": user_id,
            "name": f"User {user_id}",
        },
    )

print("Primary position:", system.primary_position)
print("Replica position:", system.replica_position)
print("Pending events:", system.get_pending_events())
print("Replication lag:", system.get_lag())

# Replica processes only 4 events.
system.process_replication(max_events=4)

print("\nAfter processing 4 events:")

print("Primary position:", system.primary_position)
print("Replica position:", system.replica_position)
print("Pending events:", system.get_pending_events())
print("Replication lag:", system.get_lag())

# Replica processes the remaining events.
system.process_replication(max_events=10)

print("\nAfter processing remaining events:")

print("Primary position:", system.primary_position)
print("Replica position:", system.replica_position)
print("Pending events:", system.get_pending_events())
print("Replication lag:", system.get_lag())
```

Expected output:

```text
Primary position: 10
Replica position: 0
Pending events: 10
Replication lag: 10

After processing 4 events:
Primary position: 10
Replica position: 4
Pending events: 6
Replication lag: 6

After processing remaining events:
Primary position: 10
Replica position: 10
Pending events: 0
Replication lag: 0
```

This simulation demonstrates a simple position-based lag measurement.

The position difference is not a measurement in seconds. It represents how many sequential replication events the replica has not yet applied.

Real database systems use database-specific replication positions and monitoring mechanisms.

## 11. Monitoring Replication Lag in Production

A production system should monitor more than whether a replica is online.

Useful metrics include:

| Metric | Why it matters |
|---|---|
| Replication lag | Shows how far a replica is behind |
| Pending replication events | Shows whether work is accumulating |
| Replica apply rate | Measures how quickly changes are processed |
| Primary write rate | Helps identify incoming workload |
| Network throughput | Identifies communication bottlenecks |
| Replica CPU and disk I/O | Helps identify resource limitations |
| Replica availability | Detects failed or disconnected replicas |

A particularly useful signal is whether lag is increasing continuously.

A replica that is consistently 100 milliseconds behind may be healthy for a particular workload.

A replica whose lag grows from 100 milliseconds to 30 seconds over several minutes may indicate that it cannot keep up with the incoming workload.

Alert thresholds should be based on application requirements rather than choosing an arbitrary universal number.

## 12. Key Takeaways

- Replication lag is the delay between primary commits and replica availability.
- High write volume, network latency, slow storage, and long-running queries can increase lag.
- Replication lag can cause read-after-write problems.
- Routing critical reads to the primary is a simple way to avoid stale replica reads.
- Position-based tracking can help determine whether a replica has applied a particular change.
- Replica freshness is important during failover.
- Monitoring lag trends is more useful than checking only whether replicas are online.

**Next:** [Read/Write Splitting](07_read_write_splitting.md)
