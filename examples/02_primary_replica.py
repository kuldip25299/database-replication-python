# examples/02_primary_replica.py

"""
Primary-Replica Database Architecture

Demonstrates:
1. A primary database handling all writes.
2. Multiple replicas maintaining copies of primary data.
3. Replication from primary to replicas.
4. Read operations distributed across replicas.
5. What happens when a replica is behind.

This is an in-memory educational simulation.
Replication is triggered manually to make the data flow visible.

Run:
    python examples/02_primary_replica.py
"""


class DatabaseNode:
    def __init__(self, name, role="replica"):
        self.name = name
        self.role = role
        self.data = {}
        self.available = True
        self.read_count = 0
        self.write_count = 0
        self.replication_position = 0

    def _check_availability(self):
        if not self.available:
            raise ConnectionError(
                f"{self.name} is unavailable"
            )

    def write(self, key, value):
        self._check_availability()

        if self.role != "primary":
            raise PermissionError(
                f"Writes are not allowed on {self.name}"
            )

        self.data[key] = value
        self.write_count += 1
        self.replication_position += 1

        print(
            f"[{self.name}] WRITE: "
            f"{key} = {value}"
        )

    def read(self, key):
        self._check_availability()

        self.read_count += 1
        value = self.data.get(key)

        print(
            f"[{self.name}] READ: "
            f"{key} = {value}"
        )

        return value

    def replicate_from(self, primary):
        self._check_availability()
        primary._check_availability()

        if self.role != "replica":
            raise PermissionError(
                f"{self.name} is not configured as a replica"
            )

        # Copy the primary's current state.
        self.data = primary.data.copy()
        self.replication_position = (
            primary.replication_position
        )

        print(
            f"[{self.name}] Replicated data from "
            f"{primary.name} "
            f"(position: {self.replication_position})"
        )

    def get_stats(self):
        return {
            "role": self.role,
            "records": len(self.data),
            "reads": self.read_count,
            "writes": self.write_count,
            "replication_position": self.replication_position,
        }


class PrimaryReplicaCluster:
    def __init__(self, primary, replicas):
        if primary.role != "primary":
            raise ValueError(
                "The primary node must have role='primary'"
            )

        for replica in replicas:
            if replica.role != "replica":
                raise ValueError(
                    f"{replica.name} must have role='replica'"
                )

        self.primary = primary
        self.replicas = replicas

    def write(self, key, value):
        # All writes go to the primary.
        self.primary.write(key, value)

    def replicate(self):
        # Simulate primary-to-replica data propagation.
        for replica in self.replicas:
            if not replica.available:
                print(
                    f"[CLUSTER] Skipping unavailable "
                    f"replica: {replica.name}"
                )
                continue

            replica.replicate_from(self.primary)

    def read_from_replica(self, key, replica_index=0):
        if not self.replicas:
            raise RuntimeError("No replicas configured")

        if replica_index < 0 or replica_index >= len(self.replicas):
            raise IndexError("Invalid replica index")

        replica = self.replicas[replica_index]

        return replica.read(key)

    def read_from_primary(self, key):
        return self.primary.read(key)

    def show_cluster_status(self):
        print("\n" + "=" * 60)
        print("CLUSTER STATUS")
        print("=" * 60)

        nodes = [self.primary] + self.replicas

        for node in nodes:
            stats = node.get_stats()

            print(f"\nNode: {node.name}")
            for key, value in stats.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")


def main():
    # Create database nodes.
    primary = DatabaseNode(
        name="Primary",
        role="primary"
    )

    replica_1 = DatabaseNode(
        name="Replica-1"
    )

    replica_2 = DatabaseNode(
        name="Replica-2"
    )

    # Create the cluster.
    cluster = PrimaryReplicaCluster(
        primary=primary,
        replicas=[replica_1, replica_2]
    )

    print("=" * 60)
    print("PRIMARY-REPLICA DATABASE ARCHITECTURE")
    print("=" * 60)

    # --------------------------------------------------
    # 1. Write operations
    # --------------------------------------------------

    print("\n--- WRITE OPERATIONS ---")

    cluster.write("user_1", "Kuldip")
    cluster.write("user_2", "Rahul")
    cluster.write("user_3", "Amit")

    # --------------------------------------------------
    # 2. Read before replication
    # --------------------------------------------------

    print("\n--- READ BEFORE REPLICATION ---")

    print("Reading from primary:")
    cluster.read_from_primary("user_1")

    print("\nReading from Replica-1:")
    cluster.read_from_replica(
        "user_1",
        replica_index=0
    )

    # The replica has not received any writes yet.
    # It returns None for user_1.

    # --------------------------------------------------
    # 3. Replicate primary data
    # --------------------------------------------------

    print("\n--- REPLICATION ---")

    cluster.replicate()

    # --------------------------------------------------
    # 4. Read after replication
    # --------------------------------------------------

    print("\n--- READ AFTER REPLICATION ---")

    cluster.read_from_replica(
        "user_1",
        replica_index=0
    )

    cluster.read_from_replica(
        "user_2",
        replica_index=1
    )

    # --------------------------------------------------
    # 5. Update primary after replication
    # --------------------------------------------------

    print("\n--- NEW WRITE ON PRIMARY ---")

    cluster.write("user_1", "Kuldip Updated")

    print("\nReading from Replica-1 before next replication:")
    cluster.read_from_replica(
        "user_1",
        replica_index=0
    )

    # The replica still contains the older value.

    # --------------------------------------------------
    # 6. Replicate the latest changes
    # --------------------------------------------------

    print("\n--- REPLICATING LATEST CHANGES ---")

    cluster.replicate()

    print("\nReading from Replica-1 after replication:")
    cluster.read_from_replica(
        "user_1",
        replica_index=0
    )

    # --------------------------------------------------
    # 7. Display cluster status
    # --------------------------------------------------

    cluster.show_cluster_status()


if __name__ == "__main__":
    main()
