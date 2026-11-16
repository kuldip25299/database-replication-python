# 04. Synchronous Replication

## 1. Introduction

Synchronous replication is a replication strategy where the primary waits for acknowledgment from one or more replicas before confirming a write operation to the application.

The main idea is that a write should not be considered complete until the configured replication acknowledgment condition has been satisfied.

This can provide stronger durability guarantees than asynchronous replication.

However, it also introduces additional latency because the primary must wait for replica communication.

Let's understand the complete write flow.

## 2. How Synchronous Replication Works

Consider an application with one primary and two replicas.

```text id="s9gq2f"
                Application
                     |
                     | Write Request
                     v
                  Primary
                     |
             +-------+-------+
             |               |
             v               v
          Replica 1       Replica 2
             |               |
             +-------+-------+
                     |
                 Acknowledgment
                     |
                     v
                  Primary
                     |
                     v
              Application
```

The flow is:

1. Application sends a write request to the primary.
2. Primary processes and records the write.
3. Primary sends the change to replicas.
4. Replicas acknowledge according to the configured replication policy.
5. Primary confirms the write after the required acknowledgment condition is met.

The exact acknowledgment condition depends on the database and its configuration.

For example, a system may wait for:

- Every configured replica.
- At least one replica.
- A quorum of replicas.

These are different durability and availability policies. Synchronous replication does not always mean waiting for every replica.

## 3. Example: Creating an Order

Imagine a customer places an order worth ₹5,000.

The application sends:

```python id="y8xk5a"
{
    "order_id": 5001,
    "user_id": 101,
    "amount": 5000,
    "status": "confirmed"
}
```

The primary receives the request and records the order.

Before acknowledging the write, it waits for the required replica confirmation.

```text id="z4p9xu"
Application
    |
    | Create Order
    v
Primary
    |
    | Record Order
    |
    +-----------> Replica 1
    |                  |
    |                  | Apply Change
    |                  |
    |<-----------------+
    |
    +-----------> Replica 2
    |                  |
    |                  | Apply Change
    |                  |
    |<-----------------+
    |
    | Required acknowledgments received
    |
    v
Application receives success
```

Once the configured condition is satisfied, the primary responds successfully.

This reduces the window in which an acknowledged write exists only on the primary.

However, the guarantee depends on what the replica acknowledgment actually means. Some systems acknowledge receipt or durable log storage rather than full application of the change.

## 4. Why Synchronous Replication Matters

Consider a payment application.

A customer completes a payment, and the application records the transaction.

If the primary crashes immediately afterward, losing that transaction could create serious problems.

Synchronous replication can reduce this risk by requiring another database node to acknowledge the change before the application receives success.

For example:

```text id="x8j3vw"
Primary:
  Payment 9001 -> SUCCESS

Replica 1:
  Payment 9001 -> SUCCESS

Replica 2:
  Payment 9001 -> SUCCESS
```

If the primary fails after the required acknowledgment, another sufficiently up-to-date node may be able to take over without losing that acknowledged change.

This is particularly useful for workloads where losing acknowledged writes is unacceptable.

Still, synchronous replication alone does not guarantee zero data loss during every possible failure. The durability policy, storage guarantees, acknowledgment semantics, and failover process all matter.

## 5. Synchronous Replication vs. Write Latency

The main cost of synchronous replication is additional write latency.

Without waiting for a replica, the primary can acknowledge a write after its own commit conditions are satisfied.

With synchronous replication, it must also wait for the required replica acknowledgment.

Consider an illustrative scenario:

| Operation | Time |
|---|---:|
| Application to primary | 5 ms |
| Primary processing and commit | 8 ms |
| Primary to replica | 10 ms |
| Replica acknowledgment | 7 ms |
| Response to application | 5 ms |

The application may wait approximately 35 ms, assuming sequential stages and no overlapping work.

This is only an illustrative calculation. Actual latency depends on network distance, storage durability, database implementation, and whether replication work overlaps with other operations.

For geographically distributed replicas, network round-trip time can become a significant part of write latency.

## 6. What Happens If a Replica Is Slow?

Suppose the primary has two synchronous replicas.

Replica 1 responds quickly, but Replica 2 is slow.

```text id="g1d5tx"
               Primary
                  |
          +-------+-------+
          |               |
          v               v
       Replica 1       Replica 2
          |               |
          v               |
       ACK: 8 ms       Waiting...
                          |
                          |
                     ACK: 200 ms
```

If the policy requires both replicas, the primary must wait for the slower one.

This can increase write latency.

In a busy application, slow replicas can affect the overall write throughput and response time.

Possible approaches include:

- Waiting for fewer replicas.
- Using a quorum-based acknowledgment policy.
- Investigating network and storage bottlenecks.
- Removing an unhealthy replica from the synchronous acknowledgment configuration when the database supports it.

Each option changes the system's guarantees.

## 7. What Happens If a Replica Goes Down?

Assume the primary requires acknowledgments from both replicas.

Replica 2 becomes unavailable.

```text id="x2v9kg"
               Primary
                  |
          +-------+-------+
          |               |
          v               X
       Replica 1       Replica 2
          |               |
          v               X
          ACK           DOWN
```

The primary cannot satisfy the configured acknowledgment requirement.

Depending on the database configuration, writes may:

- Wait until a timeout.
- Fail.
- Continue with a reduced acknowledgment requirement if automatic fallback is configured.

This is an important trade-off.

A strict synchronous policy can protect acknowledged writes, but it can also reduce write availability when required replicas are unavailable.

## 8. Synchronous Replication and Availability

Synchronous replication introduces a dependency on replica health and communication.

Consider these two policies.

### Policy A: Wait for All Replicas

The primary waits for every configured synchronous replica.

Advantages:

- More replicas have confirmed the write.
- Stronger protection against losing an acknowledged write if one node fails.

Disadvantages:

- One slow or unavailable replica can block writes.
- Higher latency.
- Reduced write availability.

### Policy B: Wait for a Required Number of Replicas

The primary waits for a configured number of acknowledgments.

For example, with three replicas, it may require acknowledgment from at least two.

Advantages:

- Can tolerate some replica failures.
- Avoids waiting for every replica.
- Offers a configurable balance between latency and durability.

Disadvantages:

- Not every replica is guaranteed to have the latest write.
- Failover must select a node that contains the required committed history.
- The exact guarantees depend on the database's quorum and commit rules.

A quorum is not automatically a guarantee of strong consistency. The write and read quorum rules, membership changes, and leader-election protocol also matter.

## 9. Synchronous Replication vs. Asynchronous Replication

| Area | Synchronous | Asynchronous |
|---|---|---|
| Primary acknowledgment | Waits for required replica acknowledgment | Does not wait for replica application |
| Write latency | Usually higher | Usually lower |
| Replica lag | Acknowledged changes have met the configured condition | Replicas may lag behind |
| Write availability | Can depend on replica availability | Primary can often continue without replicas |
| Data-loss risk on primary failure | Lower for acknowledged writes, subject to policy | Higher if changes have not reached a surviving node |
| Common use | Workloads needing stronger write durability | Workloads prioritizing write throughput and availability |

Neither approach is universally better.

The right choice depends on the application's requirements.

## 10. Simple Python Simulation

We will simulate synchronous replication using separate in-memory database nodes.

The primary will:

1. Receive a write.
2. Update its local data.
3. Send the change to replicas.
4. Wait for the configured replicas to acknowledge.
5. Return success only when the acknowledgment requirement is met.

For this educational example, replica operations will execute immediately.

We will introduce delayed replication in the asynchronous replication example.

```python id="s4p6qy"
class DatabaseNode:
    def __init__(self, name):
        self.name = name
        self.data = {}

    def insert(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)


class SynchronousReplication:
    def __init__(self, primary, replicas, required_acks=None):
        self.primary = primary
        self.replicas = replicas

        if required_acks is None:
            required_acks = len(replicas)

        if not 1 <= required_acks <= len(replicas):
            raise ValueError("Invalid required acknowledgment count")

        self.required_acks = required_acks

    def write(self, key, value):
        # Step 1: Write to primary.
        self.primary.insert(key, value)

        # Step 2: Replicate to available replicas.
        acknowledgments = 0

        for replica in self.replicas:
            replica.insert(key, value)
            acknowledgments += 1

            if acknowledgments >= self.required_acks:
                return True

        return False


primary = DatabaseNode("primary")

replicas = [
    DatabaseNode("replica_1"),
    DatabaseNode("replica_2"),
]

replication = SynchronousReplication(
    primary,
    replicas,
    required_acks=2,
)

success = replication.write(
    101,
    {
        "user_id": 101,
        "name": "Alice",
    },
)

print("Write successful:", success)
print("Primary:", primary.get(101))
print("Replica 1:", replicas[0].get(101))
print("Replica 2:", replicas[1].get(101))
```

This is a simplified simulation, not a production synchronous replication implementation.

It does not simulate network failures, timeouts, durable transaction logs, or partial failures. It also writes to the primary before checking replica acknowledgments, so a failed acknowledgment does not automatically roll back the primary write.

We will address failure behavior and recovery in later examples.

## 11. When Should We Use Synchronous Replication?

Consider synchronous replication when:

- Losing acknowledged writes is unacceptable.
- The application has strict durability requirements.
- The network between database nodes has predictable latency.
- The application can tolerate additional write latency.
- Replica acknowledgment policies are carefully configured.

Examples may include financial transaction systems, payment processing, and systems where acknowledged data loss has serious consequences.

However, the database architecture must be designed around the required guarantees. Simply enabling synchronous replication is not enough.

## 12. Key Takeaways

- Synchronous replication waits for configured replica acknowledgments before confirming a write.
- It can reduce the risk of losing acknowledged writes.
- Write latency increases because the primary waits for replica communication.
- Waiting for every replica can make writes dependent on the slowest replica.
- Quorum-based acknowledgment policies can provide a balance between durability and availability.
- Replica failure behavior depends on the configured acknowledgment policy.
- Synchronous replication does not eliminate the need for backups and a safe failover process.

**Next:** [Asynchronous Replication](05_asynchronous_replication.md)
