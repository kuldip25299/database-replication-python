```python
"""
Database Read/Write Router

Demonstrates:
1. Routing all write operations to the primary database.
2. Distributing read operations across replicas.
3. Round-robin replica selection.
4. Skipping unavailable replicas.
5. Falling back to the primary when no replica is available.
6. Handling read-after-write consistency requirements.

Run:
    python examples/06_read_write_router.py

Note:
This is an in-memory educational simulation. Real applications may
implement read/write routing through database proxies, application
middleware, ORM configuration, or database connection pools.
"""


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

    def replicate_from(self, primary):
        if not self.available:
            raise ConnectionError(f"{self.name} is unavailable")

        if self.role != "replica":
            raise PermissionError(
                f"{self.name} is not a replica"
            )

        self.data = primary.data.copy()
        self.replication_position = primary.replication_position

    def read(self, key):
        if not self.available:
            raise ConnectionError(f"{self.name} is unavailable")

        return self.data.get(key)


class ReadWriteRouter:
    def __init__(self, primary, replicas):
        self.primary = primary
        self.replicas = replicas
        self.next_replica_index = 0

    def write(self, key, value):
        """
        All writes must go to the primary.
        """

        print(f"\n[ROUTER] Sending write to {self.primary.name}")

        position = self.primary.write(key, value)

        print(
            f"[PRIMARY] Write completed at position {position}"
        )

        return position

    def get_next_available_replica(self):
        """
        Select an available replica using round-robin routing.

        Each replica is checked at most once per selection.
        """

        if not self.replicas:
            return None

        total_replicas = len(self.replicas)

        for _ in range(total_replicas):
            index = self.next_replica_index

            replica = self.replicas[index]

            self.next_replica_index = (
                index + 1
            ) % total_replicas

            if replica.available:
                return replica

        return None

    def read(self, key, read_after_write=False):
        """
        Route reads to replicas by default.

        When read_after_write=True, read directly from the primary
        to avoid returning stale replica data.
        """

        if read_after_write:
            print(
                f"[ROUTER] Read-after-write requested. "
                f"Using {self.primary.name}"
            )

            return self.primary.read(key)

        replica = self.get_next_available_replica()

        if replica is None:
            print(
                "[ROUTER] No available replicas. "
                "Falling back to primary."
            )

            return self.primary.read(key)

        print(
            f"[ROUTER] Sending read to {replica.name}"
        )

        return replica.read(key)

    def print_status(self):
        print("\nCluster Status")
        print("-" * 60)

        nodes = [self.primary] + self.replicas

        for node in nodes:
            print(
                f"{node.name} | "
                f"Role: {node.role} | "
                f"Available: {node.available} | "
                f"Position: {node.replication_position}"
            )


def main():
    primary = DatabaseNode("primary-db", "primary")

    replica_1 = DatabaseNode("replica-1", "replica")
    replica_2 = DatabaseNode("replica-2", "replica")
    replica_3 = DatabaseNode("replica-3", "replica")

    router = ReadWriteRouter(
        primary=primary,
        replicas=[
            replica_1,
            replica_2,
            replica_3,
        ],
    )

    print("\n--- Scenario 1: Write operations ---")

    router.write(
        "product:101",
        {"name": "Laptop", "price": 75000}
    )

    router.write(
        "product:102",
        {"name": "Monitor", "price": 15000}
    )

    print("\n--- Scenario 2: Replicate primary data ---")

    for replica in router.replicas:
        replica.replicate_from(primary)

        print(
            f"[REPLICATION] {replica.name} is now at "
            f"position {replica.replication_position}"
        )

    print("\n--- Scenario 3: Distribute read requests ---")

    for request_number in range(1, 7):
        print(f"\nRead request #{request_number}")

        result = router.read("product:101")

        print("Result:", result)

    print("\n--- Scenario 4: Replica becomes unavailable ---")

    replica_2.available = False

    for request_number in range(1, 5):
        print(f"\nRead request #{request_number}")

        result = router.read("product:102")

        print("Result:", result)

    print("\n--- Scenario 5: Read-after-write consistency ---")

    router.write(
        "product:103",
        {"name": "Keyboard", "price": 3000}
    )

    # Replicas have not received product:103 yet.
    print("\nNormal replica read:")

    result = router.read("product:103")

    print("Result:", result)

    print("\nRead-after-write request:")

    result = router.read(
        "product:103",
        read_after_write=True,
    )

    print("Result:", result)

    print("\n--- Scenario 6: All replicas unavailable ---")

    for replica in router.replicas:
        replica.available = False

    result = router.read("product:101")

    print("Result:", result)

    router.print_status()


if __name__ == "__main__":
    main()
```
