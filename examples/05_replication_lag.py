```python
"""
Replication Lag Simulation

Demonstrates:
1. How replication lag develops when replicas process updates slowly.
2. How to measure lag using replication positions.
3. How stale reads can return outdated application data.
4. How read-after-write consistency can be handled by waiting for
   a replica to catch up or routing the read to the primary.
5. How a replica can recover after processing pending events.

Run:
    python examples/05_replication_lag.py

Note:
This is an in-memory educational simulation. Replication positions
represent simplified log sequence numbers, not actual database LSNs
or GTIDs.
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
            raise PermissionError("Writes are allowed only on primary")

        self.replication_position += 1
        self.data[key] = value

        return self.replication_position

    def apply_replication(self, event):
        if not self.available:
            raise ConnectionError(f"{self.name} is unavailable")

        if self.role != "replica":
            raise PermissionError("Only replicas can apply replication")

        self.data[event["key"]] = event["value"]
        self.replication_position = event["position"]

    def read(self, key):
        if not self.available:
            raise ConnectionError(f"{self.name} is unavailable")

        return self.data.get(key)


class ReplicationLagCluster:
    def __init__(self, primary, replicas):
        self.primary = primary
        self.replicas = replicas

        self.replication_queues = {
            replica.name: deque()
            for replica in replicas
        }

    def write(self, key, value):
        """
        Write to primary and enqueue updates for replicas.

        The application receives confirmation immediately after
        the primary accepts the write.
        """

        position = self.primary.write(key, value)

        event = {
            "position": position,
            "key": key,
            "value": value,
        }

        for replica in self.replicas:
            self.replication_queues[replica.name].append(event)

        print(
            f"[WRITE] {key} = {value} | "
            f"Primary position: {position}"
        )

        return position

    def replicate(self, replica_name, max_events=None):
        """
        Apply pending events to a replica.

        max_events simulates limited replication throughput.
        """

        replica = self.get_replica(replica_name)
        queue = self.replication_queues[replica_name]

        if not replica.available:
            print(f"[REPLICATION FAILED] {replica_name} unavailable")
            return 0

        processed = 0

        while queue and (
            max_events is None or processed < max_events
        ):
            event = queue.popleft()
            replica.apply_replication(event)

            processed += 1

            print(
                f"[REPLICATED] {replica_name} applied "
                f"position {event['position']}"
            )

        return processed

    def get_replica(self, replica_name):
        for replica in self.replicas:
            if replica.name == replica_name:
                return replica

        raise ValueError(f"Unknown replica: {replica_name}")

    def get_replication_lag(self, replica_name):
        """
        Position-based lag:

        Primary position - Replica position

        This measures unapplied position distance in this simulation.
        It is not a time measurement.
        """

        replica = self.get_replica(replica_name)

        return (
            self.primary.replication_position
            - replica.replication_position
        )

    def get_pending_events(self, replica_name):
        return len(self.replication_queues[replica_name])

    def print_replication_status(self):
        print("\nReplication Status")
        print("-" * 75)

        print(
            f"{'Replica':<15}"
            f"{'Position':<15}"
            f"{'Lag':<10}"
            f"{'Pending Events':<18}"
            f"{'Available'}"
        )

        for replica in self.replicas:
            lag = self.get_replication_lag(replica.name)
            pending = self.get_pending_events(replica.name)

            print(
                f"{replica.name:<15}"
                f"{replica.replication_position:<15}"
                f"{lag:<10}"
                f"{pending:<18}"
                f"{replica.available}"
            )

    def read_from_replica(self, replica_name, key):
        replica = self.get_replica(replica_name)

        value = replica.read(key)

        print(
            f"[REPLICA READ] {replica_name} | "
            f"{key} = {value}"
        )

        return value

    def read_from_primary(self, key):
        value = self.primary.read(key)

        print(
            f"[PRIMARY READ] {key} = {value}"
        )

        return value

    def read_after_write(self, replica_name, key, required_position):
        """
        Read from a replica only when it has applied the required
        replication position.

        If the replica is behind, fall back to the primary.
        """

        replica = self.get_replica(replica_name)

        if (
            replica.available
            and replica.replication_position >= required_position
        ):
            print(
                f"[ROUTER] Replica {replica_name} has caught up. "
                "Reading from replica."
            )

            return replica.read(key)

        print(
            f"[ROUTER] Replica {replica_name} is behind. "
            "Falling back to primary."
        )

        return self.primary.read(key)


def main():
    primary = DatabaseNode("primary-db", "primary")

    replica_1 = DatabaseNode("replica-1", "replica")
    replica_2 = DatabaseNode("replica-2", "replica")

    cluster = ReplicationLagCluster(
        primary=primary,
        replicas=[replica_1, replica_2],
    )

    print("\n--- Scenario 1: Generate database writes ---")

    position_1 = cluster.write(
        "user:101",
        {"name": "Rahul", "balance": 5000}
    )

    position_2 = cluster.write(
        "user:101",
        {"name": "Rahul", "balance": 7000}
    )

    position_3 = cluster.write(
        "user:102",
        {"name": "Priya", "balance": 3000}
    )

    cluster.print_replication_status()

    print("\n--- Scenario 2: Replicas return stale data ---")

    cluster.read_from_primary("user:101")
    cluster.read_from_replica("replica-1", "user:101")

    print("\n--- Scenario 3: Replicas process different amounts of work ---")

    # Replica 1 processes all pending updates.
    cluster.replicate("replica-1")

    # Replica 2 processes only one update.
    cluster.replicate("replica-2", max_events=1)

    cluster.print_replication_status()

    print("\n--- Scenario 4: Compare replica reads ---")

    cluster.read_from_replica("replica-1", "user:101")
    cluster.read_from_replica("replica-2", "user:101")

    print("\n--- Scenario 5: Read-after-write consistency ---")

    print(
        "\nApplication wants to read user:101 after "
        "the latest write."
    )

    # The application remembers the position returned by its write.
    required_position = position_2

    value = cluster.read_after_write(
        replica_name="replica-2",
        key="user:101",
        required_position=required_position,
    )

    print("Application received:", value)

    print("\n--- Scenario 6: Replica catches up ---")

    cluster.replicate("replica-2")

    cluster.print_replication_status()

    value = cluster.read_after_write(
        replica_name="replica-2",
        key="user:101",
        required_position=required_position,
    )

    print("Application received:", value)

    print("\n--- Scenario 7: Read after the latest write ---")

    print(
        "\nThe application now requires position:",
        position_3
    )

    # Replica 2 has caught up to position 3.
    value = cluster.read_after_write(
        replica_name="replica-2",
        key="user:102",
        required_position=position_3,
    )

    print("Application received:", value)


if __name__ == "__main__":
    main()
```
