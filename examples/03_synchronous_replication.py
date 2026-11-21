```python
"""
Synchronous Database Replication

Demonstrates:
1. A primary database receiving a write.
2. Replicas acknowledging the write.
3. The primary confirming the write only after the required acknowledgments.
4. Write failure when the required replica acknowledgments are not received.

Run:
    python examples/03_synchronous_replication.py

Note:
This is an in-memory educational simulation. Real databases use transaction
logs (such as WAL or binlogs), durable storage, and database-specific
replication acknowledgment policies.
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
                f"Writes are not allowed on replica {self.name}"
            )

        self.replication_position += 1
        self.data[key] = value

        return self.replication_position

    def apply_replication(self, key, value, position):
        if not self.available:
            raise ConnectionError(f"{self.name} is unavailable")

        if self.role != "replica":
            raise PermissionError(
                f"{self.name} is not a replica"
            )

        self.data[key] = value
        self.replication_position = position

        return True

    def read(self, key):
        if not self.available:
            raise ConnectionError(f"{self.name} is unavailable")

        return self.data.get(key)

    def status(self):
        return {
            "name": self.name,
            "role": self.role,
            "available": self.available,
            "replication_position": self.replication_position,
            "records": len(self.data),
        }


class SynchronousReplicationCluster:
    def __init__(self, primary, replicas, required_acknowledgments):
        if required_acknowledgments < 0:
            raise ValueError(
                "Required acknowledgments cannot be negative"
            )

        if required_acknowledgments > len(replicas):
            raise ValueError(
                "Required acknowledgments cannot exceed replica count"
            )

        self.primary = primary
        self.replicas = replicas
        self.required_acknowledgments = required_acknowledgments

    def write(self, key, value):
        print(f"\nWriting {key} = {value}")

        # Step 1: The primary processes the write.
        position = self.primary.write(key, value)

        print(
            f"[PRIMARY] Write recorded at position {position}"
        )

        # Step 2: Send the change to replicas and collect acknowledgments.
        acknowledgments = 0
        acknowledged_replicas = []

        for replica in self.replicas:
            try:
                replica.apply_replication(
                    key,
                    value,
                    position
                )

                acknowledgments += 1
                acknowledged_replicas.append(replica.name)

                print(
                    f"[ACK] {replica.name} acknowledged "
                    f"position {position}"
                )

            except ConnectionError:
                print(
                    f"[FAILED] {replica.name} did not acknowledge "
                    f"position {position}"
                )

        # Step 3: Confirm the write only if the configured
        # acknowledgment requirement is satisfied.
        if acknowledgments >= self.required_acknowledgments:
            print(
                f"[COMMITTED] Write confirmed. "
                f"Acknowledgments: {acknowledgments}/"
                f"{self.required_acknowledgments}"
            )

            return {
                "success": True,
                "position": position,
                "acknowledgments": acknowledgments,
                "replicas": acknowledged_replicas,
            }

        print(
            f"[NOT CONFIRMED] Required "
            f"{self.required_acknowledgments} acknowledgments, "
            f"received {acknowledgments}"
        )

        return {
            "success": False,
            "position": position,
            "acknowledgments": acknowledgments,
            "replicas": acknowledged_replicas,
        }

    def print_cluster_status(self):
        print("\nCluster Status")
        print("-" * 50)

        nodes = [self.primary] + self.replicas

        for node in nodes:
            status = node.status()

            print(
                f"{status['name']} | "
                f"Role: {status['role']} | "
                f"Available: {status['available']} | "
                f"Position: {status['replication_position']} | "
                f"Records: {status['records']}"
            )


def main():
    primary = DatabaseNode("primary-db", "primary")

    replica_1 = DatabaseNode("replica-1", "replica")
    replica_2 = DatabaseNode("replica-2", "replica")

    cluster = SynchronousReplicationCluster(
        primary=primary,
        replicas=[replica_1, replica_2],
        required_acknowledgments=2,
    )

    print("\n--- Scenario 1: All replicas available ---")

    result = cluster.write(
        "order:101",
        {"status": "confirmed", "amount": 1500}
    )

    print(f"Application received: {result}")

    cluster.print_cluster_status()

    print("\n--- Scenario 2: One replica unavailable ---")

    replica_2.available = False

    result = cluster.write(
        "order:102",
        {"status": "confirmed", "amount": 2500}
    )

    print(f"Application received: {result}")

    cluster.print_cluster_status()

    print("\n--- Scenario 3: Required acknowledgments reduced ---")

    cluster.required_acknowledgments = 1

    result = cluster.write(
        "order:103",
        {"status": "confirmed", "amount": 3500}
    )

    print(f"Application received: {result}")

    cluster.print_cluster_status()


if __name__ == "__main__":
    main()
```
