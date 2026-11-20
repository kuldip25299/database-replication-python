# Database Replication: Production Trade-offs

## 1. Introduction

Database replication is often introduced as a way to improve read performance and availability.

The basic architecture looks simple:

- One primary database handles writes.
- Multiple replicas receive changes from the primary.
- Applications distribute read traffic across replicas.
- A replica can potentially take over if the primary fails.

But running this architecture in production introduces several decisions.

For example:

- Should replication be synchronous or asynchronous?
- How much replication lag is acceptable?
- Which reads can tolerate stale data?
- What happens when the primary fails?
- How do we prevent split brain?
- How many replicas should we maintain?
- What happens when a replica falls too far behind?

There is no single configuration that works for every application.

The right design depends on the application's traffic pattern, consistency requirements, recovery objectives, and infrastructure cost.

## 2. Synchronous vs Asynchronous Replication

This is one of the first architectural decisions.

| Factor | Synchronous | Asynchronous |
|---|---|---|
| Write acknowledgment | Waits for configured replica acknowledgment | Does not wait for replica acknowledgment |
| Write latency | Generally higher | Generally lower |
| Replication lag | Depends on acknowledgment and apply behavior | Can accumulate |
| Failure handling | Can improve durability when configured correctly | May lose acknowledged writes during failover |
| Primary availability | Can be affected by unavailable required replicas | Primary can continue accepting writes |
| Common use | Workloads requiring stronger durability guarantees | Read-heavy applications prioritizing write latency |

### When to Choose Synchronous Replication

Consider a financial application where losing acknowledged transactions is unacceptable.

A synchronous configuration can require an appropriate replica acknowledgment before the primary reports a successful commit.

However, the exact guarantee matters.

Acknowledging receipt of a transaction log is not necessarily the same as confirming that the transaction has been applied and is immediately visible to reads.

Synchronous replication also introduces latency and availability trade-offs.

### When to Choose Asynchronous Replication

Consider an e-commerce application with heavy product browsing traffic.

The primary can acknowledge writes without waiting for every replica.

This keeps the write path faster under normal conditions.

The trade-off is that replicas can lag behind, and a primary failure can result in acknowledged writes not being present on the promoted replica.

For many applications, this is an acceptable trade-off if the recovery strategy is designed around it.

## 3. How Many Replicas Should You Maintain?

Adding replicas can improve read capacity, but each replica introduces infrastructure and operational overhead.

Consider three possible configurations.

| Configuration | Benefit | Limitation |
|---|---|---|
| 1 Primary + 1 Replica | Basic redundancy and read distribution | Limited read capacity and failover options |
| 1 Primary + 2 Replicas | More read capacity and candidate choices | Higher infrastructure cost |
| 1 Primary + 4 Replicas | More read capacity for large workloads | More replication traffic and operational complexity |

Adding more replicas does not mean write throughput increases.

Every write still needs to be processed by the primary and propagated to replicas.

A large number of replicas can increase network traffic, storage consumption, and replication management overhead.

Start with the actual read workload and add replicas when the primary's read capacity becomes a measurable constraint.

## 4. Read/Write Splitting Decisions

Read/write splitting is useful only when the application routes queries correctly.

A practical routing policy could look like this:

| Operation | Database destination |
|---|---|
| Create order | Primary |
| Update user profile | Primary |
| Product listing | Replica |
| Product search | Replica |
| Read order immediately after creation | Primary or eligible replica |
| Payment confirmation | Authoritative consistent read |
| Analytics dashboard | Replica |

The important point is that routing should depend on the consistency requirement of the operation, not just whether a query is a `SELECT` or `INSERT`.

A `SELECT` can require fresh data.

For example, reading an updated payment status immediately after a transaction should not blindly go to a lagging replica.

## 5. Replication Lag Management

Replication lag is one of the most important operational signals in a replicated database system.

A replica may be healthy from a connectivity perspective but still be significantly behind the primary.

Consider this situation:

```text
Primary position:   15000
Replica 1 position: 14995
Replica 2 position: 14500
Replica 3 position: 15000
```

Replica 3 has caught up.

Replica 2 is significantly behind.

Sending all read traffic equally to these replicas may produce inconsistent user experiences.

### Practical Handling

A production application can:

1. Monitor replication progress.
2. Exclude unhealthy replicas.
3. Avoid replicas that exceed the acceptable lag threshold.
4. Route consistency-sensitive reads to eligible replicas.
5. Fall back to the primary when necessary.

The application should also define what happens when no replica meets the required freshness level.

Without a fallback policy, a lagging replica can turn a read request into an unnecessary timeout.

## 6. Failover Strategy

A replicated database architecture should define what happens when the primary becomes unavailable.

A practical failover process includes:

```text
Primary Failure
      |
      v
Detect Failure
      |
      v
Identify Healthy Replicas
      |
      v
Compare Replication Progress
      |
      v
Select Eligible Candidate
      |
      v
Prevent Old Primary From Accepting Writes
      |
      v
Promote New Primary
      |
      v
Update Application Routing
      |
      v
Reconfigure Remaining Replicas
```

There are several important details here.

### Replica Selection

The most up-to-date eligible replica should generally be preferred.

For asynchronous replication, this does not guarantee zero data loss because the primary may have acknowledged writes that never reached any replica.

### Split-Brain Prevention

Only one database node should be authorized to accept writes.

A failover process needs coordination and fencing mechanisms to prevent the old primary from continuing to operate as a writer.

### Application Routing

Promoting a replica does not automatically update every application's database connection.

Applications, connection pools, and any database proxies must discover and use the new primary.

### Recovery of the Old Primary

When the old primary becomes available again, it should not simply resume accepting writes.

Its data history must be reconciled with the new primary.

Depending on the database and failure, it may need to be rebuilt or reconfigured as a replica.

## 7. RTO and RPO

Two measurements help define how a system should recover from database failure.

### Recovery Time Objective (RTO)

RTO defines the maximum acceptable time to restore service.

Example:

```text
Application becomes unavailable: 10:00 AM
Application resumes writes:      10:00:40 AM

Recovery time: 40 seconds
```

If the application's RTO is 60 seconds, this recovery meets the target.

### Recovery Point Objective (RPO)

RPO defines the maximum acceptable data loss, measured in time.

Example:

```text
Last acknowledged write: 10:00:10 AM
Failure:                  10:00:13 AM
```

If the promoted replica is missing the last three seconds of acknowledged writes, the potential data loss is approximately three seconds.

For strict RPO requirements, the replication and failover configuration must provide appropriate durability guarantees.

**RTO and RPO should be defined before selecting the replication architecture.**

Otherwise, teams can build a system that appears highly available but cannot meet the application's actual recovery requirements.

## 8. Replication Is Not a Backup

This is an important distinction.

Replication maintains copies of current database changes across multiple nodes.

Backup provides a way to recover historical database states.

Consider this scenario:

```text
Application accidentally deletes 10,000 users.
             |
             v
Primary commits the deletion.
             |
             v
Replication propagates the deletion.
             |
             v
All replicas now reflect the deletion.
```

The replicas are working correctly, but they cannot recover the deleted users.

A production database strategy should include:

- Regular database backups.
- Point-in-time recovery where supported.
- Backup retention policies.
- Off-site or separate failure-domain storage.
- Periodic restore testing.

A backup that has never been restored is not a verified recovery strategy.

## 9. Monitoring and Operational Metrics

A replicated database needs monitoring beyond CPU and memory usage.

Some important metrics include:

| Metric | Why it matters |
|---|---|
| Replication lag | Shows how far replicas are behind |
| Replication errors | Identifies failed or stopped replication |
| Primary availability | Tracks the health of the write node |
| Replica availability | Tracks nodes available for read traffic |
| Active connections | Helps identify connection pressure |
| Query latency | Reveals slow database operations |
| Disk usage | Prevents storage exhaustion |
| Replication queue or log backlog | Shows whether replicas are keeping up |
| Failover duration | Measures recovery performance |

Metrics should lead to actionable alerts.

For example, an alert for replication lag should consider both the lag threshold and how long the replica has remained behind.

A short spike may be harmless. Sustained lag can affect user-visible consistency and failover safety.

## 10. Common Production Mistakes

### Mistake 1: Adding Replicas Without Changing Query Routing

The infrastructure has multiple replicas, but every application query still goes to the primary.

Result: read traffic continues to overload the primary.

### Mistake 2: Assuming Replicas Always Have the Latest Data

Applications read from replicas immediately after writes and return stale results.

Result: confusing user experiences and potentially incorrect business decisions.

### Mistake 3: Treating a Health Check as Proof of Safe Promotion

The old primary is unreachable from one monitoring location, so another node is promoted without proper coordination.

Result: possible split brain.

### Mistake 4: Ignoring Asynchronous Data Loss

The primary acknowledges writes before replicas receive them.

After failure, a replica is promoted without accounting for missing transactions.

Result: acknowledged data may be lost.

### Mistake 5: Treating Replication as a Backup

An accidental deletion or corrupted update is propagated to every replica.

Result: no historical recovery point is available.

### Mistake 6: Adding Too Many Replicas Too Early

Every additional replica introduces storage, network, monitoring, and maintenance overhead.

Result: higher infrastructure cost without a meaningful improvement in the actual bottleneck.

## 11. A Practical Design Example

Consider an e-commerce application with:

- High product browsing traffic.
- Moderate order creation traffic.
- A requirement to keep order and payment operations consistent.
- A preference for fast write acknowledgments.
- A need to recover from primary database failure.

One possible architecture is:

```text
                    Application
                         |
                  Read/Write Router
                    /         \
                   /           \
                WRITE           READ
                  |               |
                  v               v
              Primary DB     Replica Selector
                  |             /       \
                  |            v         v
                  |        Replica 1  Replica 2
                  |
                  +------ Async Replication ------>

                  Monitoring + Failover Management
```

### Design Decisions

| Area | Decision |
|---|---|
| Write destination | Primary |
| Read destination | Replicas for operations that tolerate staleness |
| Critical reads | Primary or a replica meeting the required consistency position |
| Replication | Asynchronous, if the accepted data-loss risk permits it |
| Replica selection | Health-aware and lag-aware |
| Failover | Controlled promotion with split-brain prevention |
| Recovery | Backups and point-in-time recovery |
| Monitoring | Replication lag, database health, query latency, and storage |

This is a possible starting design, not a universal architecture.

If the business cannot tolerate losing acknowledged order or payment writes, asynchronous replication alone may not satisfy its durability requirements. The replication and recovery design would need stronger guarantees.

## 12. Final Takeaways

Database replication is more than maintaining multiple copies of the same data.

It introduces architectural decisions that affect performance, consistency, availability, and recovery.

Before deploying replication, understand:

- Which operations need fresh data?
- How much replication lag can the application tolerate?
- What happens if the primary fails?
- Can the system prevent split brain?
- How much acknowledged data can be lost?
- How quickly must the application recover?
- How will historical data be restored?

A good replication architecture is one whose trade-offs match the application's actual requirements.

Adding database nodes is relatively easy. Designing the behavior around failures, stale reads, and recovery is where the real engineering work begins.
