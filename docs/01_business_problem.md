# 01. The Business Problem: Why Database Replication?

## 1. The Scenario

Imagine an e-commerce application that started with a single database server.

Initially, this setup works perfectly well. The application stores users, products, orders, and payments in one database. Every read and write operation goes to that database.

As the application grows, traffic increases.

More users browse products, place orders, check order status, and update their profiles. The database now handles thousands or millions of operations.

The application servers can scale horizontally, but the database is still a single machine.

This creates two important problems:

1. The database becomes a bottleneck as read traffic increases.
2. If the database server fails, the application may become unavailable.

Adding more application servers does not solve either problem by itself.

## 2. The Single Database Architecture

A simple application architecture looks like this:

```text
             Users
               |
               v
        Application Servers
               |
               v
          Single Database
```

Every application instance communicates with the same database.

For example:

- User profile requests read from the database.
- Product listing requests read from the database.
- Order placement requests write to the database.
- Payment updates write to the database.
- Reports and analytics also query the database.

As traffic increases, all these operations compete for the same database resources.

## 3. Problem 1: Increasing Read Traffic

Consider an application with:

- 100,000 registered users
- Thousands of product views per minute
- Frequent order-status checks
- Multiple application servers

Most of these operations may be read-heavy.

The database has to process all these read requests while also handling writes.

This can increase:

- CPU utilization
- Memory consumption
- Disk I/O
- Query latency
- Connection pool pressure

One option is to optimize queries, add indexes, and improve database resources.

These improvements are useful, but they do not eliminate the single-database dependency.

## 4. Problem 2: Database Availability

A single database server is also a single point of failure.

Imagine the database server crashes because of:

- Hardware failure
- Operating system issues
- Database process crashes
- Storage problems
- Network failures

The application may still be running, but it cannot access the data it depends on.

```text
             Users
               |
               v
        Application Servers
               |
               v
          Single Database
               X
            FAILURE
```

Without another database copy that can take over, recovery may require restoring the database or bringing the failed server back online.

That can result in application downtime.

## 5. Introducing Database Replication

Database replication addresses these problems by maintaining copies of data across multiple database nodes.

A common architecture uses:

- **Primary database:** Handles write operations.
- **Replica databases:** Maintain copies of the primary's data and can serve read operations.

```text
                  Users
                    |
                    v
             Application Servers
                    |
             +------+------+
             |             |
             v             v
          Writes         Reads
             |             |
             v             v
          Primary       Replica 1
             |             ^
             |             |
             +---------- Replica 2
                 Replication
```

The primary sends changes to replicas so that they can maintain copies of the data.

The application can send writes to the primary and distribute eligible reads across replicas.

If the primary fails, a replica may be promoted to become the new primary, depending on the replication and failover strategy.

## 6. What Replication Helps Solve

Database replication can help with several problems.

### Read Scalability

Instead of sending every read request to one database, the application can distribute reads across multiple replicas.

This can reduce read pressure on the primary.

### High Availability

If the primary database becomes unavailable, a healthy replica may be promoted.

This can reduce downtime, although automatic failover requires additional coordination and health checks.

### Data Redundancy

Multiple database nodes maintain copies of the same data.

This provides additional copies that can help with recovery from individual node failures.

Replication is not a replacement for backups. Accidental deletion or corrupted data can also be replicated to other nodes.

### Geographic Distribution

Replicas can be deployed closer to users in different regions.

This can reduce read latency for geographically distributed applications, although replication delay and network latency still matter.

## 7. Replication Introduces New Problems

Replication is useful, but it is not free.

It introduces additional engineering decisions.

### Replication Lag

In asynchronous replication, the primary may confirm a write before replicas receive and apply that change.

A user might update their profile and immediately read from a replica that still contains the old value.

This is called replication lag.

### Consistency

Should a write be acknowledged only after replicas confirm it?

Or should the primary acknowledge immediately and allow replicas to catch up?

These decisions affect latency, availability, and consistency guarantees.

### Failover

What happens when the primary fails?

Which replica should become the new primary? How do we prevent two nodes from accepting writes as primary at the same time?

Failover needs careful coordination.

### Replication Conflicts

If multiple nodes are allowed to accept writes, conflicting updates can occur.

Multi-primary replication requires conflict detection and resolution strategies.

This repository will introduce these concepts through focused examples.

## 8. What We Will Build

We will build a small database replication simulation using Python.

Instead of setting up PostgreSQL, MySQL, or other database infrastructure, we will use Python dictionaries to represent database nodes.

The implementation will gradually introduce:

1. A single database.
2. A primary database with replicas.
3. Synchronous replication.
4. Asynchronous replication.
5. Replication lag.
6. Read/write routing.
7. Primary failure and replica promotion.
8. Replication consistency and trade-offs.

The goal is to understand how replication works internally and what can go wrong when multiple database copies are involved.

## 9. When Should We Consider Replication?

Replication is worth considering when:

- Read traffic is putting too much pressure on the primary database.
- Database availability is an important requirement.
- The application needs additional copies of its data.
- Users are distributed across different geographic regions.
- Recovery from a database node failure needs to be faster.

However, replication should not be the first response to every database performance problem.

Before introducing replicas, investigate query performance, indexing, connection management, caching, and database resource utilization.

Replication adds operational complexity, so there should be a clear reason to introduce it.

## 10. Key Takeaways

- A single database can become a read bottleneck as an application grows.
- A single database server also creates a single point of failure.
- Replication maintains copies of data across multiple database nodes.
- Replicas can improve read capacity and help with availability.
- Replication introduces challenges such as lag, consistency, and failover.
- The replication strategy should depend on the application's consistency and availability requirements.

**Next:** [What Is Database Replication?](02_replication_fundamentals.md)
