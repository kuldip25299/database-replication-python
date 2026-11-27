# Database Replication Using Python

A practical, code-first guide to understanding database replication, primary-replica architecture, synchronous and asynchronous replication, replication lag, read/write splitting, and failover using Python.

The goal of this repository is to explain how database replication works internally through small, runnable examples rather than introducing a full database infrastructure.

## Why Database Replication Matters

As an application grows, a single database can become a bottleneck.

Consider an e-commerce application:

- Thousands of users browse products simultaneously.
- Customers place orders and update account information.
- Product searches and dashboard requests generate continuous read traffic.
- The database handles both read and write operations.

Eventually, the primary database may struggle to handle all this traffic.

Adding more application servers does not necessarily solve the problem because every server may still depend on the same database.

Database replication helps by maintaining copies of data across multiple database nodes.

A common architecture uses:

- **Primary database:** Handles write operations.
- **Replica databases:** Maintain copies of primary data and serve read requests.
- **Replication mechanism:** Transfers changes from the primary to replicas.

This can improve read scalability and availability, but it also introduces consistency, replication lag, and failover challenges.

## What You Will Learn

This repository covers:

1. Why database replication is needed.
2. Database replication fundamentals.
3. Primary-replica architecture.
4. Synchronous replication.
5. Asynchronous replication.
6. Replication lag and stale reads.
7. Read/write splitting.
8. Primary failure and replica promotion.
9. Replication consistency.
10. Production trade-offs and failure scenarios.

## Repository Structure

```text
database-replication-python/
│
├── README.md
├── requirements.txt
│
├── docs/
│   ├── 01_business_problem.md
│   ├── 02_replication_fundamentals.md
│   ├── 03_primary_replica_architecture.md
│   ├── 04_synchronous_replication.md
│   ├── 05_asynchronous_replication.md
│   ├── 06_replication_lag.md
│   ├── 07_read_write_splitting.md
│   ├── 08_failover_and_recovery.md
│   ├── 09_replication_consistency.md
│   └── 10_production_tradeoffs.md
│
└── examples/
    ├── 01_single_database.py
    ├── 02_primary_replica.py
    ├── 03_synchronous_replication.py
    ├── 04_asynchronous_replication.py
    ├── 05_replication_lag.py
    ├── 06_read_write_router.py
    ├── 07_primary_failover.py
    └── test_replication.py
```

## Documentation

Follow the documentation in order. Each document introduces a concept and explains the engineering decisions behind it.

| No. | Topic | What it covers |
|---|---|---|
| 01 | [Business Problem](docs/01_business_problem.md) | Why a single database becomes a bottleneck |
| 02 | [Replication Fundamentals](docs/02_replication_fundamentals.md) | How database replication works |
| 03 | [Primary-Replica Architecture](docs/03_primary_replica_architecture.md) | Primary and replica responsibilities |
| 04 | [Synchronous Replication](docs/04_synchronous_replication.md) | Waiting for replica acknowledgments |
| 05 | [Asynchronous Replication](docs/05_asynchronous_replication.md) | Replicating changes after primary acknowledgment |
| 06 | [Replication Lag](docs/06_replication_lag.md) | Why replicas can return stale data |
| 07 | [Read/Write Splitting](docs/07_read_write_splitting.md) | Routing reads and writes to different nodes |
| 08 | [Failover and Recovery](docs/08_failover_and_recovery.md) | Handling primary database failure |
| 09 | [Replication Consistency](docs/09_replication_consistency.md) | Understanding consistency guarantees |
| 10 | [Production Trade-offs](docs/10_production_tradeoffs.md) | Practical limitations and design decisions |

## Python Examples

All examples are self-contained educational simulations using in-memory Python objects.

| File | What it demonstrates |
|---|---|
| `01_single_database.py` | Basic database operations and a single database failure |
| `02_primary_replica.py` | Primary-replica architecture |
| `03_synchronous_replication.py` | Replica acknowledgments before write confirmation |
| `04_asynchronous_replication.py` | Queued replication and delayed replica updates |
| `05_replication_lag.py` | Measuring lag and detecting stale reads |
| `06_read_write_router.py` | Routing reads to replicas and writes to the primary |
| `07_primary_failover.py` | Promoting a replica after primary failure |

## Requirements

- Python 3.10 or later
- No external Python packages required

The implementation uses Python standard library modules.

## Getting Started

Clone the repository:

```bash
git clone https://github.com/kuldip25299/database-replication-python.git
```

Navigate into the project:

```bash
cd database-replication-python
```

No dependency installation is necessary.

Run an example:

```bash
python examples/01_single_database.py
```

Explore primary-replica replication:

```bash
python examples/02_primary_replica.py
```

Run the synchronous replication example:

```bash
python examples/03_synchronous_replication.py
```

Run the asynchronous replication example:

```bash
python examples/04_asynchronous_replication.py
```

Explore replication lag:

```bash
python examples/05_replication_lag.py
```

Run the read/write router:

```bash
python examples/06_read_write_router.py
```

Explore primary failover:

```bash
python examples/07_primary_failover.py
```

## Running Tests

The repository includes tests using Python's built-in `unittest` framework.

Run the complete test suite from the repository root:

```bash
python -m unittest discover -s examples -p "test_replication.py" -v
```

Alternatively:

```bash
python examples/test_replication.py
```

## Important Engineering Concepts

### 1. Synchronous vs Asynchronous Replication

| Consideration | Synchronous | Asynchronous |
|---|---|---|
| Write acknowledgment | Waits for configured replica acknowledgments | Does not wait for replica updates |
| Write latency | Generally higher | Generally lower |
| Replica freshness | Depends on acknowledgment policy | Replicas can lag behind |
| Potential data loss | Reduced under appropriate durability guarantees | Acknowledged writes may be missing from replicas |
| Availability trade-off | Writes may be blocked when required acknowledgments are unavailable | Primary can continue accepting writes while replicas are behind |

The exact guarantees depend on the database engine and replication configuration.

### 2. Replication Lag

Replication lag occurs when a replica has not yet applied all changes from the primary.

This can cause:

- Stale reads.
- Inconsistent user experiences.
- Incorrect decisions based on outdated information.
- Problems with read-after-write behavior.

### 3. Read/Write Splitting

A common application architecture routes:

- Writes to the primary.
- Read-heavy operations to replicas.
- Consistency-sensitive reads to the primary when necessary.

This reduces pressure on the primary, but replica selection must account for availability and lag.

### 4. Failover

When the primary fails, an eligible replica may be promoted.

However, failover requires careful handling of:

- Replication positions.
- Potentially missing acknowledged writes.
- Old-primary fencing.
- Leader election.
- Split-brain prevention.

Promoting a replica is not sufficient by itself to guarantee safe recovery.

## Production Considerations

These examples intentionally keep the implementation small. Real database replication involves additional concerns:

- Write-ahead logs and transaction logs.
- Durable replication acknowledgments.
- Replication slots and log retention.
- Network interruptions and reconnection.
- Replica lag monitoring.
- Connection management and routing.
- Leader election and fencing.
- Backup and point-in-time recovery.

**Replication is not a replacement for backups.** Replicated deletions and corrupted data can propagate to replicas as well.

## Implementation Scope

This repository focuses on understanding replication behavior through Python simulations.

It does not attempt to implement a production database engine.

The examples use:

- Python dictionaries for in-memory data storage.
- Sequential replication positions for tracking progress.
- Python queues to simulate asynchronous replication.
- Simple application-level routing.
- Explicit failure scenarios to demonstrate recovery behavior.

These abstractions make the concepts easier to inspect and experiment with. They should not be interpreted as implementations of PostgreSQL WAL, MySQL binlog, consensus protocols, or production-grade failover.

## Suggested Learning Path

If you are learning scalable database architecture, explore these topics in order:

1. Database replication
2. Database sharding
3. Database indexing
4. Database partitioning
5. Caching strategies
6. Distributed transactions
7. Database consistency models

Understanding the trade-offs between these approaches is more useful than treating any one of them as a universal scaling solution.

## Contributing

Found an issue, an incorrect assumption, or a better way to demonstrate a replication scenario?

Feel free to open an issue or submit a pull request.

Feedback and practical suggestions are welcome.

## Author

**Kuldip Awachar**

GitHub: [github.com/kuldip25299](https://github.com/kuldip25299)

---

If this repository helps you understand database replication, consider giving it a star and sharing your feedback.
