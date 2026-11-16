# 05. Asynchronous Replication

## 1. Introduction

Asynchronous replication is a replication strategy where the primary database does not wait for replicas to apply a change before acknowledging a write request.

The primary processes and commits the write, then makes the change available to the replication process.

Replicas receive and apply those changes independently.

This allows the primary to respond to applications without waiting for replica processing and acknowledgment.

The main advantages are:

- Lower write latency.
- Better write availability when replicas are temporarily unavailable.
- Less dependency on replica response time.
- More flexibility when replicas are geographically distributed.

However, asynchronous replication introduces a risk: replicas may temporarily contain stale data.

## 2. How Asynchronous Replication Works

Consider an application with one primary database and two replicas.

```text id="a9m3kx"
                  Application
                       |
                       | Write Request
                       v
                    Primary
                       |
                       | Commit Write
                       |
                       +----------------> Application
                       |
                       | Replication Event
                       v
                 Replication Queue
                       |
                +------+------+
                |             |
                v             v
             Replica 1     Replica 2
```

The flow is:

1. Application sends a write request to the primary.
2. Primary processes and commits the write.
3. Primary acknowledges the request to the application.
4. The replication process delivers the change to replicas.
5. Replicas apply the change when they receive it.

The important difference is that the application does not wait for replicas to finish applying the change.

## 3. Example: Updating a User Profile

Imagine Alice updates her city from Mumbai to Pune.

Initially, all three database nodes contain:

```python id="y2q9wl"
{
    "user_id": 101,
    "name": "Alice",
    "city": "Mumbai"
}
```

The application sends an update request to the primary.

### Step 1: Primary Receives the Update

```text id="r3p8ka"
UPDATE users
SET city = 'Pune'
WHERE user_id = 101;
```

### Step 2: Primary Commits the Change

The primary now contains:

```python id="q7v5nm"
{
    "user_id": 101,
    "name": "Alice",
    "city": "Pune"
}
```

### Step 3: Application Receives Success

The primary acknowledges the write.

It does not need to wait for every replica to apply the update.

### Step 4: Replicas Catch Up

The replication process sends the change to the replicas.

After they apply it, all nodes contain the updated record.

```text id="h4w8ps"
Immediately after primary commit:

Primary:   Pune
Replica 1: Mumbai
Replica 2: Mumbai


After replication:

Primary:   Pune
Replica 1: Pune
Replica 2: Pune
```

This temporary difference is expected in asynchronous replication.

## 4. Understanding the Replication Queue

In a simplified replication system, changes can be placed into a queue before being applied to replicas.

For example, the primary processes three operations:

```text id="k3n9vf"
Operation 1: Create User 101
Operation 2: Update User 101
Operation 3: Create User 102
```

The replication process can deliver these operations to replicas.

```text id="m6x2jb"
Primary
   |
   v
Replication Queue
   |
   +---- Operation 1
   |
   +---- Operation 2
   |
   +---- Operation 3
   |
   v
Replica Workers
   |
   +---- Replica 1
   |
   +---- Replica 2
```

A real database does not necessarily use an application-level queue like this.

Many database systems use transaction logs, log shipping, streaming replication, or other database-specific mechanisms.

Our Python example will use a queue because it makes the replication flow easier to understand.

## 5. Why Asynchronous Replication Is Faster

Consider a write operation with these illustrative timings:

| Operation | Time |
|---|---:|
| Application to primary | 5 ms |
| Primary processing and commit | 8 ms |
| Primary response to application | 5 ms |
| Replica processing | 15 ms |

With synchronous replication, the primary may need to wait for the required replica acknowledgment before responding.

With asynchronous replication, the application can receive a response after the primary commit, while replica processing continues separately.

The replica processing time does not have to be part of the application's write-response latency.

This can improve write throughput, especially when replicas are geographically distant.

The trade-off is that the replicas may not have the latest data immediately.

## 6. The Problem: Replication Lag

Replication lag is the delay between a change becoming committed on the primary and that change becoming available on a replica.

For example:

```text id="b7z4qx"
Time 10:00:00

Primary:
  Order 5001 -> confirmed

Replica 1:
  Order 5001 -> not available yet

Replica 2:
  Order 5001 -> not available yet
```

A few milliseconds or seconds later, replicas may catch up.

Replication lag can happen because of:

- Network delays.
- High write volume.
- Slow replica storage.
- Replica CPU pressure.
- Large transactions.
- Replication worker bottlenecks.

A replica with significant lag can return outdated information.

We'll study this problem in detail in the next documentation file.

## 7. Read-After-Write Problem

One of the most common problems with asynchronous replication is stale reads immediately after a write.

Consider this sequence:

1. Alice updates her profile city to Pune.
2. The primary commits the update.
3. The application receives success.
4. Alice immediately opens her profile.
5. The application sends the read request to Replica 1.
6. Replica 1 has not received the update yet.

The application returns Mumbai even though the update was successful.

```text id="v8k2wr"
Application
    |
    | Update City = Pune
    v
Primary
    |
    | Commit
    v
Success Response
    |
    | Immediate Read
    v
Replica 1
    |
    | Still has old value
    v
Mumbai
```

From the application's perspective, this can look like the update failed.

But the primary contains the correct value. The replica is simply behind.

Possible application-level solutions include:

- Route read-after-write requests to the primary.
- Use session-based consistency rules.
- Wait until a replica reaches a known replication position.
- Use a database-supported consistency mechanism.

The correct approach depends on the application's requirements and database capabilities.

## 8. What Happens If a Replica Goes Down?

Suppose Replica 1 becomes unavailable.

The primary can often continue accepting writes because it does not wait for that replica.

```text id="j5c8pn"
               Primary
                  |
          +-------+-------+
          |               |
          v               X
       Replica 2       Replica 1
                          DOWN
```

When Replica 1 comes back online, it needs to catch up on the changes it missed.

A database may resume replication from a saved log position if the required log records are still available.

Otherwise, it may need a fresh synchronization process.

Asynchronous replication can therefore provide better write availability during temporary replica failures, but it does not remove the need to monitor and recover failed replicas.

## 9. What Happens If the Primary Goes Down?

This is the most important risk of asynchronous replication.

Imagine the following sequence:

1. Application sends a payment write.
2. Primary commits the payment.
3. Primary acknowledges success.
4. Replicas have not received the change yet.
5. Primary crashes.

```text id="p6x3wd"
Primary:
  Payment 9001 -> SUCCESS

Replica 1:
  Payment 9001 -> NOT RECEIVED

Replica 2:
  Payment 9001 -> NOT RECEIVED
```

If Replica 1 is promoted to primary, the acknowledged payment record may be missing.

This is why asynchronous replication can result in data loss during certain failover scenarios.

The amount of potentially missing data depends on replication lag and which replica is selected for promotion.

A system can reduce this risk by monitoring replica progress and selecting the most up-to-date eligible replica, but asynchronous replication cannot guarantee that every acknowledged write has reached another node before primary failure.

## 10. Asynchronous vs. Synchronous Replication

| Area | Asynchronous | Synchronous |
|---|---|---|
| Primary response | Does not wait for replica application | Waits for configured acknowledgment |
| Write latency | Usually lower | Usually higher |
| Replica freshness | May lag | Acknowledged writes meet configured acknowledgment condition |
| Primary availability | Less dependent on replica response | May depend on required replicas |
| Data-loss risk during failover | Higher if changes have not reached a surviving replica | Lower for acknowledged writes, depending on policy |
| Implementation complexity | Requires lag monitoring and recovery | Requires acknowledgment and failure policies |

Neither strategy is universally better.

A system prioritizing write latency and availability may prefer asynchronous replication.

A system requiring stronger guarantees for acknowledged writes may choose synchronous replication or a carefully designed quorum-based approach.

## 11. Simple Python Simulation

We'll use:

- One primary node.
- Two replica nodes.
- A queue to hold pending replication events.

The primary will commit a write and enqueue the change.

Replicas will not update until the replication worker processes the queue.

```python id="x9m4vf"
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


class AsynchronousReplication:
    def __init__(self, primary, replicas):
        self.primary = primary
        self.replicas = replicas
        self.replication_queue = deque()

    def write(self, key, value):
        # Commit the write on the primary.
        self.primary.insert(key, value)

        # Queue the replication event.
        self.replication_queue.append({
            "key": key,
            "value": deepcopy(value),
        })

        # Return without waiting for replicas.
        return True

    def process_replication(self):
        while self.replication_queue:
            event = self.replication_queue.popleft()

            for replica in self.replicas:
                replica.insert(
                    event["key"],
                    event["value"],
                )


primary = DatabaseNode("primary")

replicas = [
    DatabaseNode("replica_1"),
    DatabaseNode("replica_2"),
]

replication = AsynchronousReplication(primary, replicas)

success = replication.write(
    101,
    {
        "user_id": 101,
        "name": "Alice",
        "city": "Pune",
    },
)

print("Write successful:", success)

print("Primary:", primary.get(101))
print("Replica 1 before sync:", replicas[0].get(101))

# Process pending replication events.
replication.process_replication()

print("Replica 1 after sync:", replicas[0].get(101))
print("Replica 2 after sync:", replicas[1].get(101))
```

Expected behavior:

```text id="m5p8qa"
Write successful: True

Primary: {'user_id': 101, 'name': 'Alice', 'city': 'Pune'}

Replica 1 before sync: None

Replica 1 after sync: {'user_id': 101, 'name': 'Alice', 'city': 'Pune'}

Replica 2 after sync: {'user_id': 101, 'name': 'Alice', 'city': 'Pune'}
```

This is a simplified educational simulation.

It does not implement real network communication, durable queues, transaction logs, concurrent workers, or retry handling. The queue exists only in memory, so a process crash would lose pending events.

Those limitations are intentional. The example demonstrates the fundamental difference between committing a write on the primary and applying it on replicas.

## 12. When Should We Use Asynchronous Replication?

Consider asynchronous replication when:

- Write latency is important.
- The application can tolerate temporary stale reads.
- Replicas are located across distant regions.
- The primary should continue accepting writes during temporary replica outages.
- The system has a defined strategy for handling replication lag and failover.

Common use cases include:

- Product catalog reads.
- User activity feeds.
- Analytics and reporting.
- Search-related read workloads.
- Read-heavy applications.

For critical operations, the application may still need to read from the primary or use stronger consistency guarantees.

## 13. Key Takeaways

- Asynchronous replication allows the primary to acknowledge writes without waiting for replicas to apply them.
- Replication events can be processed independently.
- It usually reduces write latency.
- Replicas may temporarily contain stale data.
- Read-after-write requests can return outdated results.
- A primary failure can cause acknowledged writes to be missing from replicas.
- Replication lag monitoring and safe failover are important parts of the design.

**Next:** [Understanding Replication Lag](06_replication_lag.md)
