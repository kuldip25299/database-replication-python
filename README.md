# Database Replication using Python

Understand how database replication works through simple, runnable Python implementations. This repository covers primary-replica architecture, synchronous and asynchronous replication, replication lag, read/write splitting, failover, and consistency trade-offs.

---

## 1. Why This Repository?

As an application grows, a single database server can become a bottleneck.

Increasing application servers does not automatically solve database limitations. The database itself may struggle with increasing read traffic, availability requirements, and the risk of a single point of failure.

Database replication is one approach to address these problems.

Instead of keeping data on only one database server, we maintain copies of that data across multiple database nodes.

For example:

- A primary database handles write operations.
- Replica databases maintain copies of the primary's data.
- Read requests can be distributed across replicas.
- If the primary becomes unavailable, a replica may be promoted to become the new primary.

However, replication introduces its own challenges.

A replica may not have received the latest update. A primary can fail before its changes reach replicas. Promoting a replica can also result in data loss if replication was incomplete.

This repository explores these problems through practical Python examples.

## 2. What You Will Learn

The repository moves from basic concepts to practical implementations.

### Database Replication Fundamentals

- What database replication is
- Why replication is needed
- Primary-replica architecture
- How changes move from primary to replicas
- Replication versus database sharding

### Replication Strategies

- Synchronous replication
- Asynchronous replication
- Advantages and limitations of each strategy
- How replication acknowledgment works
- Latency and availability trade-offs

### Replication Lag

- What replication lag means
- Why replicas can return stale data
- How delayed updates affect application behavior
- Read-after-write consistency problems

### Read/Write Splitting

- Sending writes to the primary
- Distributing reads across replicas
- Routing reads to the primary when fresh data is required
- Handling replica availability

### Failover and Recovery

- What happens when the primary database fails
- Promoting a replica
- Selecting a suitable replica
- Handling incomplete replication
- Understanding split-brain scenarios

### Consistency and Production Trade-offs

- Strong consistency versus eventual consistency
- Replication durability
- Replica synchronization
- Failover risks
- Operational complexity

## 3. Repository Structure

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

## 4. Implementation Approach

The examples use simple Python classes and in-memory dictionaries to simulate database nodes.

There is no requirement to install or configure PostgreSQL, MySQL, Redis, or any other database server.

The goal is to understand the underlying replication behavior before introducing database-specific implementation details.

### Example: Primary-Replica Architecture

Consider an application with one primary and two replicas.

```text
                 Application
                      |
                      |
                Primary Database
                      |
               Replication Changes
                 /         \
                /           \
               v             v
        Replica 1         Replica 2
```

When the application writes a new user:

1. The write request reaches the primary.
2. The primary stores the new record.
3. The change is propagated to replicas.
4. Replicas update their local copies.
5. Read requests can be served by replicas, depending on the consistency requirements.

This sounds straightforward, but the timing of replication makes a significant difference.

For example, in asynchronous replication, the primary may acknowledge a write before replicas receive it.

If the application immediately reads that record from a replica, it may not find the latest data.

The repository will implement this behavior so that the problem is visible in code.

## 5. Learning Path

The examples are organized in the following order.

| Example | What it demonstrates |
|---|---|
| `01_single_database.py` | Starting point with a single database |
| `02_primary_replica.py` | Basic primary-replica architecture |
| `03_synchronous_replication.py` | Waiting for replica acknowledgment |
| `04_asynchronous_replication.py` | Propagating changes without waiting |
| `05_replication_lag.py` | Understanding stale reads |
| `06_read_write_router.py` | Routing reads and writes to different nodes |
| `07_primary_failover.py` | Promoting a replica after primary failure |

Each example builds on the concepts introduced in the documentation.

## 6. Requirements

- Python 3.11+
- pip
- Basic Python knowledge

No external database or infrastructure is required.

## 7. Installation

Clone the repository:

```bash
git clone https://github.com/<your-github-username>/database-replication-python.git
```

Navigate into the project:

```bash
cd database-replication-python
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it.

**macOS / Linux**

```bash
source venv/bin/activate
```

**Windows**

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## 8. Running Examples

Run any example directly using Python.

For example:

```bash
python examples/01_single_database.py
```

Run the primary-replica example:

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

Run the replication lag example:

```bash
python examples/05_replication_lag.py
```

Run the read/write routing example:

```bash
python examples/06_read_write_router.py
```

Run the failover example:

```bash
python examples/07_primary_failover.py
```

## 9. Running Tests

The repository includes tests for the Python implementations.

Run the complete test suite from the repository root:

```bash
pytest -q
```

## 10. Synchronous vs. Asynchronous Replication

One of the most important decisions in database replication is whether the primary should wait for replicas before acknowledging a write.

| Aspect | Synchronous | Asynchronous |
|---|---|---|
| Write acknowledgment | Waits for configured replica acknowledgment | Does not wait for replica acknowledgment |
| Write latency | Generally higher | Generally lower |
| Replica freshness | Stronger guarantees, depending on configuration | Replicas may lag |
| Availability | Can be affected by unavailable required replicas | Primary can often continue writing |
| Data loss risk | Lower under the configured acknowledgment and durability guarantees | Recent acknowledged writes may be lost during certain failures |

Neither strategy is universally better.

The right choice depends on the application's consistency requirements, latency tolerance, and failure-handling strategy.

Also, synchronous replication does not automatically mean every replica has acknowledged every write. Real databases have different acknowledgment and durability configurations.

## 11. Important Concepts and Limitations

This repository is an educational simulation, not a production database replication engine.

The Python examples demonstrate the concepts, but they do not implement the full behavior of systems such as PostgreSQL streaming replication or MySQL replication.

Some important production concerns include:

- Network failures between database nodes
- Replication acknowledgment and durability
- Replica lag under heavy write traffic
- Concurrent writes and transaction ordering
- Primary election and split-brain prevention
- Failover coordination
- Replication recovery and resynchronization
- Monitoring replication health

The examples intentionally avoid infrastructure complexity so that the core behavior remains easy to understand.

## 12. Database Replication vs. Database Sharding

Replication and sharding are often used together, but they solve different problems.

| Database Replication | Database Sharding |
|---|---|
| Maintains copies of data across nodes | Splits data across multiple nodes |
| Improves read capacity and availability | Distributes data and workload |
| Multiple nodes can hold the same records | Different nodes hold different data partitions |
| Requires synchronization between copies | Requires routing requests to the correct shard |

For example, an application might use sharding to distribute users across multiple database groups and replication within each group to maintain additional copies.

Understanding both concepts is important when designing systems that need to scale beyond a single database server.

## 13. Who Is This Repository For?

- Backend developers learning distributed database concepts
- Python developers interested in system design
- Engineers preparing to design scalable applications
- Developers who want to understand replication behavior beyond diagrams
- Anyone interested in database architecture and production trade-offs

## 14. Contributions and Feedback

If you find an issue, have a better implementation approach, or want to suggest an improvement, feel free to open an issue or submit a pull request.

I'm particularly interested in feedback around:

- Replication consistency
- Failover strategies
- Replica lag handling
- Read/write routing
- Real-world database replication trade-offs

The goal is to keep the implementations simple while explaining the engineering decisions behind them.

## 15. Final Thoughts

Database replication looks simple at first: maintain copies of data across multiple database nodes.

But the interesting engineering problems appear when those copies are not updated at the same time, a node becomes unavailable, or an application expects to read data immediately after writing it.

Understanding these edge cases is important before choosing a replication strategy for a real application.

This repository explores those problems step by step using Python.

---

**Repository:** [database-replication-python](https://github.com/<your-github-username>/database-replication-python)

*No license has been selected for this repository yet.*
