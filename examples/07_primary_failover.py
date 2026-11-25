```python
"""
Primary Database Failover

Demonstrates:
1. Normal primary-replica operation.
2. Asynchronous replication between database nodes.
3. Primary database failure.
4. Selecting the most up-to-date available replica.
5. Promoting a replica to become the new primary.
6. Handling writes after failover.
7. Understanding potential data loss from replication lag.

Run:
    python examples/07_primary_failover.py

Note:
This is an in-memory educational simulation. It does not implement
distributed leader election, fencing, quorum, or split-brain prevention.

Real database failover requires coordination to ensure that only one
primary can accept writes at a time.
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

        if event["position"] != self.replication_position + 1:
            raise ValueError(
                f"Replication position mismatch on {self.name}. "
                f"Expected {self.replication_position + 1}, "
                f"received {event['position']}"
            )

        self.data[event["key"]] = event["value"]
        self.replication_position = event["position"]

    def promote_to_primary(self):
        if not self.available:
            raise ConnectionError(
                f"Cannot promote unavailable node {self.name}"
            )

        self.role = "primary"

        print(
            f"[PROMOTION] {self.name} is now the primary"
        )

    def read(self, key):
        if not self.available:
            raise ConnectionError(f"{self.name} is unavailable")

        return self.data.get(key)


class FailoverCluster:
    def __init__(self, primary, replicas):
        self.primary = primary
        self.replicas = replicas

        self.replication_queues = {
            replica.name: deque()
            for replica in replicas
        }

    def write(self, key, value):
        if not self.primary.available:
            raise ConnectionError(
                "Primary is unavailable. Writes are rejected."
            )

        position = self.primary.write(key, value)

        event = {
            "position": position,
            "key": key,
            "value": value,
        }

        for replica in self.replicas:
            self.replication_queues[replica.name].append(event)

        print(
            f"[WRITE] {key} = {value} "
            f"| Position: {position}"
        )

        print(
            "[APPLICATION] Write acknowledged by primary"
        )

        return position

    def replicate(self, replica_name, max_events=None):
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
                f"[REPLICATION FAILED] {replica.name} unavailable"
            )
            return

        queue = self.replication_queues[replica.name]
        processed = 0

        while queue and (
            max_events is None or processed < max_events
        ):
            event = queue.popleft()

            replica.apply_replication(event)
            processed += 1

        print(
            f"[REPLICATION] {replica.name} applied "
            f"{processed} events"
        )

    def replicate_all(self):
        for replica in self.replicas:
            self.replicate(replica.name)

    def get_best_replica(self):
        """
        Select the available replica with the highest
        replication position.

        This simple simulation uses replication position as
        the only selection criterion.
        """

        available_replicas = [
            replica
            for replica in self.replicas
            if replica.available
        ]

        if not available_replicas:
            return None

        return max(
            available_replicas,
            key=lambda replica: replica.replication_position,
        )

    def fail_primary(self):
        self.primary.available = False

        print(
            f"\n[FAILURE] {self.primary.name} is unavailable"
        )

    def promote_best_replica(self):
        if self.primary.available:
            raise RuntimeError(
                "Cannot promote a replica while the old primary "
                "is still considered active. Fence the old primary first."
            )

        candidate = self.get_best_replica()

        if candidate is None:
            print(
                "[FAILOVER FAILED] No available replica to promote"
            )
            return False

        old_primary = self.primary

        # The old primary is unavailable and therefore fenced
        # in this educational simulation.
        candidate.promote_to_primary()

        # Remove the promoted node from the replica list.
        self.replicas.remove(candidate)
        self.replication_queues.pop(candidate.name, None)

        # The promoted node becomes the new primary.
        self.primary = candidate

        print(
            f"[FAILOVER COMPLETE] "
            f"{old_primary.name} -> {candidate.name}"
        )

        print(
            f"[FAILOVER STATUS] New primary position: "
            f"{self.primary.replication_position}"
        )

        return True

    def print_status(self):
        print("\nCluster Status")
        print("-" * 70)

        nodes = [self.primary] + self.replicas

        for node in nodes:
            pending = 0

            if node.role == "replica":
                pending = len(
                    self.replication_queues[node.name]
                )

            print(
                f"{node.name} | "
                f"Role: {node.role} | "
                f"Available: {node.available} | "
                f"Position: {node.replication_position} | "
                f"Pending events: {pending}"
            )


def main():
    primary = DatabaseNode("primary-db", "primary")

    replica_1 = DatabaseNode("replica-1", "replica")
    replica_2 = DatabaseNode("replica-2", "replica")

    cluster = FailoverCluster(
        primary=primary,
        replicas=[replica_1, replica_2],
    )

    print("\n--- Scenario 1: Normal database operation ---")

    cluster.write(
        "order:101",
        {"status": "confirmed", "amount": 1500}
    )

    cluster.write(
        "order:102",
        {"status": "confirmed", "amount": 2500}
    )

    cluster.replicate_all()

    cluster.print_status()

    print("\n--- Scenario 2: Replicas progress differently ---")

    cluster.write(
        "order:103",
        {"status": "confirmed", "amount": 3500}
    )

    # Replica 1 receives the latest write.
    cluster.replicate("replica-1")

    # Replica 2 remains behind.
    cluster.print_status()

    print("\n--- Scenario 3: Primary fails ---")

    cluster.fail_primary()

    try:
        cluster.write(
            "order:104",
            {"status": "confirmed", "amount": 4500}
        )
    except ConnectionError as error:
        print(f"[WRITE REJECTED] {error}")

    print("\n--- Scenario 4: Promote the most up-to-date replica ---")

    cluster.promote_best_replica()

    cluster.print_status()

    print("\n--- Scenario 5: Write after failover ---")

    cluster.write(
        "order:104",
        {"status": "confirmed", "amount": 4500}
    )

    print(
        "\nNew primary read:",
        cluster.primary.read("order:104")
    )

    print("\n--- Scenario 6: Check remaining replica ---")

    cluster.replicate_all()

    cluster.print_status()


if __name__ == "__main__":
    main()
```
