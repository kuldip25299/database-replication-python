```python
"""
Asynchronous Database Replication

Demonstrates:
1. The primary database accepting and confirming writes immediately.
2. Replication events being added to a queue.
3. Replicas applying queued changes later.
4. Replication lag when replicas fall behind.
5. Potential data loss when the primary fails before pending changes
   reach a replica.

Run:
    python examples/04_asynchronous_replication.py

Note:
This is an in-memory educational simulation. Real databases generally
replicate transaction logs such as WAL or binlogs rather than copying
Python dictionaries or using an application-level queue.
"""


from collections import deque


class DatabaseNode:
    def __init__(self, name, role):
        self.name = name
        self.role = role
        self.data = {}
        self.available = True
        self.replication_position = 0

    def write(self, key, value):
        if not self.available:
            raise ConnectionError(f"{self.name} is unavailable")

        if self.role != "primary":
            raise PermissionError(
                f"Writes are not allowed on {self.name}"
            )

        self.replication_position += 1
        self.data[key] = value

        return self.replication_position

    def apply_replication(self, event):
        if not self.available:
            raise ConnectionError(f"{self.name} is unavailable")

        if self.role != "replica":
            raise PermissionError(
                f"{self.name} is not a replica"
            )

        self.data[event["key"]] = event["value"]
        self.replication_position = event["position"]

    def read(self, key):
        if not self.available:
            raise ConnectionError(f"{self.name} is unavailable")

        return self.data.get(key)

    def status(self):
        return {
            "name": self.name,
            "role": self.role,
            "available": self.available,
            "position": self.replication_position,
            "records": len(self.data),
        }


class AsynchronousReplicationCluster:
    def __init__(self, primary, replicas):
        self.primary = primary
        self.replicas = replicas

        # Each replica has its own pending replication queue.
        self.replication_queues = {
            replica.name: deque()
            for replica in replicas
        }

    def write(self, key, value):
        """
        Write to the primary and enqueue replication events.

        The application receives confirmation after the primary
        accepts the write. Replica acknowledgment is not required.
        """

        position = self.primary.write(key, value)

        event = {
            "position": position,
            "key": key,
            "value": value,
        }

        # Queue the event for every replica.
        for replica in self.replicas:
            self.replication_queues[replica.name].append(event)

        print(
            f"[PRIMARY] Write confirmed at position {position}: "
            f"{key} = {value}"
        )

        print(
            "[APPLICATION] Received successful response "
            "without waiting for replicas"
        )

        return {
            "success": True,
            "position": position,
        }

    def replicate(self, replica_name, max_events=None):
        """
        Apply pending replication events to one replica.

        max_events controls how many events are processed in
        a single replication cycle.
        """

        replica = next(
            (
                node for node in self.replicas
                if node.name == replica_name
            ),
            None,
        )

        if replica is None:
            raise ValueError(
                f"Replica not found: {replica_name}"
            )

        if not replica.available:
            print(
                f"[REPLICATION FAILED] {replica.name} is unavailable"
            )
            return 0

        queue = self.replication_queues[replica.name]

        processed = 0

        while queue and (
            max_events is None or processed < max_events
        ):
            event = queue.popleft()

            replica.apply_replication(event)

            processed += 1

            print(
                f"[REPLICATED] {replica.name} applied "
                f"position {event['position']}"
            )

        if processed == 0:
            print(
                f"[REPLICATION] No pending events for {replica.name}"
            )

        return processed

    def replicate_all(self):
        """Process all pending events for available replicas."""

        for replica in self.replicas:
            self.replicate(replica.name)

    def get_replication_lag(self, replica_name):
        """
        Return the difference between the primary and replica
        replication positions.
        """

        replica = next(
            (
                node for node in self.replicas
                if node.name == replica_name
            ),
            None,
        )

        if replica is None:
            raise ValueError(
                f"Replica not found: {replica_name}"
            )

        return (
            self.primary.replication_position
            - replica.replication_position
        )

    def print_cluster_status(self):
        print("\nCluster Status")
        print("-" * 65)

        nodes = [self.primary] + self.replicas

        for node in nodes:
            status = node.status()

            pending = 0

            if node.role == "replica":
                pending = len(
                    self.replication_queues[node.name]
                )

            print(
                f"{status['name']} | "
                f"Role: {status['role']} | "
                f"Available: {status['available']} | "
                f"Position: {status['position']} | "
                f"Pending: {pending}"
            )

    def fail_primary(self):
        """
        Simulate primary failure.

        This does not automatically promote a replica.
        """

        self.primary.available = False

        print("\n[FAILURE] Primary database is unavailable")

    def get_replica_data(self, replica_name):
        replica = next(
            (
                node for node in self.replicas
                if node.name == replica_name
            ),
            None,
        )

        if replica is None:
            raise ValueError(
                f"Replica not found: {replica_name}"
            )

        return replica.data


def main():
    primary = DatabaseNode("primary-db", "primary")

    replica_1 = DatabaseNode("replica-1", "replica")
    replica_2 = DatabaseNode("replica-2", "replica")

    cluster = AsynchronousReplicationCluster(
        primary=primary,
        replicas=[replica_1, replica_2],
    )

    print("\n--- Scenario 1: Primary accepts writes ---")

    cluster.write(
        "order:101",
        {"status": "confirmed", "amount": 1500}
    )

    cluster.write(
        "order:102",
        {"status": "confirmed", "amount": 2500}
    )

    cluster.print_cluster_status()

    print("\n--- Scenario 2: Read before replication ---")

    print(
        "Primary read:",
        primary.read("order:101")
    )

    print(
        "Replica read:",
        replica_1.read("order:101")
    )

    print("\n--- Scenario 3: Replicate only one event ---")

    cluster.replicate(
        replica_name="replica-1",
        max_events=1,
    )

    cluster.print_cluster_status()

    print(
        "\nReplica 1 lag:",
        cluster.get_replication_lag("replica-1")
    )

    print(
        "Replica 2 lag:",
        cluster.get_replication_lag("replica-2")
    )

    print("\n--- Scenario 4: Replicate remaining events ---")

    cluster.replicate_all()

    cluster.print_cluster_status()

    print(
        "\nReplica 1 data:",
        cluster.get_replica_data("replica-1")
    )

    print(
        "\nReplica 2 data:",
        cluster.get_replica_data("replica-2")
    )

    print("\n--- Scenario 5: Primary fails before replication ---")

    cluster.write(
        "order:103",
        {"status": "confirmed", "amount": 3500}
    )

    # Simulate primary failure before the replicas process
    # the newly queued event.
    cluster.fail_primary()

    cluster.print_cluster_status()

    print(
        "\nReplica 1 has order:103:",
        replica_1.read("order:103")
    )

    print(
        "Replica 2 has order:103:",
        replica_2.read("order:103")
    )

    print(
        "\n[OBSERVATION] The primary acknowledged order:103, "
        "but neither replica received it before the failure."
    )


if __name__ == "__main__":
    main()
```
