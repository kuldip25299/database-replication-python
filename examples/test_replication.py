```python
"""
Database Replication Tests

Tests the behavior of:
1. Primary database writes.
2. Primary-replica replication.
3. Synchronous replication acknowledgments.
4. Asynchronous replication and lag.
5. Read/write routing.
6. Primary failover.

Run all tests:
    python -m unittest discover -s examples -p "test_replication.py" -v

Run this file directly:
    python examples/test_replication.py

Note:
These tests use the classes defined in the example files.
The implementations are educational in-memory simulations.
"""

import importlib.util
import unittest
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parent


def load_module(filename, module_name):
    """Load a Python example file whose name starts with a number."""

    file_path = EXAMPLES_DIR / filename

    spec = importlib.util.spec_from_file_location(
        module_name,
        file_path,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Could not load module: {filename}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


# Load example modules.
single_db = load_module(
    "01_single_database.py",
    "single_database",
)

primary_replica = load_module(
    "02_primary_replica.py",
    "primary_replica",
)

synchronous = load_module(
    "03_synchronous_replication.py",
    "synchronous_replication",
)

asynchronous = load_module(
    "04_asynchronous_replication.py",
    "asynchronous_replication",
)

lag_module = load_module(
    "05_replication_lag.py",
    "replication_lag",
)

router_module = load_module(
    "06_read_write_router.py",
    "read_write_router",
)

failover_module = load_module(
    "07_primary_failover.py",
    "primary_failover",
)


class TestSingleDatabase(unittest.TestCase):

    def setUp(self):
        self.database = single_db.Database()

    def test_write_and_read(self):
        self.database.write(
            "product:101",
            {"name": "Laptop"},
        )

        result = self.database.read("product:101")

        self.assertEqual(
            result,
            {"name": "Laptop"},
        )

    def test_unavailable_database_rejects_write(self):
        self.database.available = False

        with self.assertRaises(ConnectionError):
            self.database.write(
                "product:101",
                {"name": "Laptop"},
            )


class TestPrimaryReplica(unittest.TestCase):

    def setUp(self):
        self.primary = primary_replica.DatabaseNode(
            "primary-db",
            "primary",
        )

        self.replica = primary_replica.DatabaseNode(
            "replica-1",
            "replica",
        )

        self.cluster = primary_replica.PrimaryReplicaCluster(
            self.primary,
            [self.replica],
        )

    def test_write_goes_to_primary(self):
        self.cluster.write(
            "product:101",
            {"name": "Laptop"},
        )

        self.assertEqual(
            self.primary.read("product:101"),
            {"name": "Laptop"},
        )

    def test_replica_receives_data_after_replication(self):
        self.cluster.write(
            "product:101",
            {"name": "Laptop"},
        )

        self.assertIsNone(
            self.replica.read("product:101")
        )

        self.cluster.replicate()

        self.assertEqual(
            self.replica.read("product:101"),
            {"name": "Laptop"},
        )


class TestSynchronousReplication(unittest.TestCase):

    def setUp(self):
        self.primary = synchronous.DatabaseNode(
            "primary-db",
            "primary",
        )

        self.replica_1 = synchronous.DatabaseNode(
            "replica-1",
            "replica",
        )

        self.replica_2 = synchronous.DatabaseNode(
            "replica-2",
            "replica",
        )

        self.cluster = synchronous.SynchronousReplicationCluster(
            primary=self.primary,
            replicas=[
                self.replica_1,
                self.replica_2,
            ],
            required_acknowledgments=2,
        )

    def test_write_succeeds_with_required_acknowledgments(self):
        result = self.cluster.write(
            "order:101",
            {"status": "confirmed"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["acknowledgments"], 2)

        self.assertEqual(
            self.replica_1.read("order:101"),
            {"status": "confirmed"},
        )

        self.assertEqual(
            self.replica_2.read("order:101"),
            {"status": "confirmed"},
        )

    def test_write_is_not_confirmed_when_acknowledgments_missing(self):
        self.replica_2.available = False

        result = self.cluster.write(
            "order:102",
            {"status": "confirmed"},
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["acknowledgments"], 1)

        # The primary write is not automatically rolled back.
        self.assertEqual(
            self.primary.read("order:102"),
            {"status": "confirmed"},
        )

    def test_invalid_acknowledgment_requirement(self):
        with self.assertRaises(ValueError):
            synchronous.SynchronousReplicationCluster(
                primary=self.primary,
                replicas=[self.replica_1],
                required_acknowledgments=2,
            )


class TestAsynchronousReplication(unittest.TestCase):

    def setUp(self):
        self.primary = asynchronous.DatabaseNode(
            "primary-db",
            "primary",
        )

        self.replica = asynchronous.DatabaseNode(
            "replica-1",
            "replica",
        )

        self.cluster = asynchronous.AsynchronousReplicationCluster(
            self.primary,
            [self.replica],
        )

    def test_write_is_acknowledged_before_replication(self):
        result = self.cluster.write(
            "order:101",
            {"status": "confirmed"},
        )

        self.assertTrue(result["success"])

        self.assertEqual(
            self.primary.read("order:101"),
            {"status": "confirmed"},
        )

        self.assertIsNone(
            self.replica.read("order:101")
        )

    def test_replication_applies_pending_events(self):
        self.cluster.write(
            "order:101",
            {"status": "confirmed"},
        )

        self.cluster.replicate("replica-1")

        self.assertEqual(
            self.replica.read("order:101"),
            {"status": "confirmed"},
        )

    def test_primary_failure_can_leave_replica_behind(self):
        self.cluster.write(
            "order:101",
            {"status": "confirmed"},
        )

        self.cluster.fail_primary()

        self.assertIsNone(
            self.replica.read("order:101")
        )

        self.assertEqual(
            self.cluster.replication_queues["replica-1"].__len__(),
            1,
        )


class TestReplicationLag(unittest.TestCase):

    def setUp(self):
        self.primary = lag_module.DatabaseNode(
            "primary-db",
            "primary",
        )

        self.replica = lag_module.DatabaseNode(
            "replica-1",
            "replica",
        )

        self.cluster = lag_module.ReplicationCluster(
            self.primary,
            [self.replica],
        )

    def test_lag_increases_when_replica_falls_behind(self):
        self.cluster.write("account:101", {"balance": 1000})
        self.cluster.write("account:102", {"balance": 2000})

        lag = self.cluster.monitor.get_lag(self.replica)

        self.assertEqual(lag, 2)

    def test_lag_becomes_zero_after_replication(self):
        self.cluster.write("account:101", {"balance": 1000})
        self.cluster.write("account:102", {"balance": 2000})

        self.cluster.replicate("replica-1")

        lag = self.cluster.monitor.get_lag(self.replica)

        self.assertEqual(lag, 0)

    def test_router_falls_back_when_replica_exceeds_lag_threshold(self):
        self.cluster.write("account:101", {"balance": 1000})

        result = self.cluster.read_with_lag_check(
            "account:101",
            max_allowed_lag=0,
        )

        self.assertEqual(result, {"balance": 1000})


class TestReadWriteRouter(unittest.TestCase):

    def setUp(self):
        self.primary = router_module.DatabaseNode(
            "primary-db",
            "primary",
        )

        self.replica_1 = router_module.DatabaseNode(
            "replica-1",
            "replica",
        )

        self.replica_2 = router_module.DatabaseNode(
            "replica-2",
            "replica",
        )

        self.router = router_module.ReadWriteRouter(
            self.primary,
            [self.replica_1, self.replica_2],
        )

    def test_write_goes_to_primary(self):
        self.router.write(
            "product:101",
            {"name": "Laptop"},
        )

        self.assertEqual(
            self.primary.read("product:101"),
            {"name": "Laptop"},
        )

        self.assertIsNone(
            self.replica_1.read("product:101")
        )

    def test_read_uses_available_replica(self):
        self.primary.write(
            "product:101",
            {"name": "Laptop"},
        )

        self.replica_1.replicate_from(self.primary)

        result = self.router.read("product:101")

        self.assertEqual(
            result,
            {"name": "Laptop"},
        )

    def test_unavailable_replicas_fall_back_to_primary(self):
        self.primary.write(
            "product:101",
            {"name": "Laptop"},
        )

        self.replica_1.available = False
        self.replica_2.available = False

        result = self.router.read("product:101")

        self.assertEqual(
            result,
            {"name": "Laptop"},
        )

    def test_read_after_write_uses_primary(self):
        self.router.write(
            "product:101",
            {"name": "Laptop"},
        )

        result = self.router.read(
            "product:101",
            read_after_write=True,
        )

        self.assertEqual(
            result,
            {"name": "Laptop"},
        )


class TestPrimaryFailover(unittest.TestCase):

    def setUp(self):
        self.primary = failover_module.DatabaseNode(
            "primary-db",
            "primary",
        )

        self.replica_1 = failover_module.DatabaseNode(
            "replica-1",
            "replica",
        )

        self.replica_2 = failover_module.DatabaseNode(
            "replica-2",
            "replica",
        )

        self.cluster = failover_module.FailoverCluster(
            self.primary,
            [
                self.replica_1,
                self.replica_2,
            ],
        )

    def test_most_up_to_date_replica_is_promoted(self):
        self.cluster.write(
            "order:101",
            {"status": "confirmed"},
        )

        self.cluster.replicate("replica-1")

        self.cluster.fail_primary()

        result = self.cluster.promote_best_replica()

        self.assertTrue(result)

        self.assertEqual(
            self.cluster.primary.name,
            "replica-1",
        )

        self.assertEqual(
            self.cluster.primary.role,
            "primary",
        )

    def test_new_primary_accepts_writes(self):
        self.cluster.write(
            "order:101",
            {"status": "confirmed"},
        )

        self.cluster.replicate_all()
        self.cluster.fail_primary()
        self.cluster.promote_best_replica()

        self.cluster.write(
            "order:102",
            {"status": "confirmed"},
        )

        self.assertEqual(
            self.cluster.primary.read("order:102"),
            {"status": "confirmed"},
        )

    def test_failover_fails_without_available_replicas(self):
        self.cluster.fail_primary()

        self.replica_1.available = False
        self.replica_2.available = False

        result = self.cluster.promote_best_replica()

        self.assertFalse(result)

    def test_promotion_is_rejected_while_old_primary_is_active(self):
        with self.assertRaises(RuntimeError):
            self.cluster.promote_best_replica()


if __name__ == "__main__":
    unittest.main(verbosity=2)
```
