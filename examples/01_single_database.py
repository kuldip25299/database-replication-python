# examples/01_single_database.py

"""
Single Database Architecture

Demonstrates a basic application where all read and write
operations are handled by a single database node.

This is the starting point before introducing database
replication.

Run:
    python examples/01_single_database.py
"""


class Database:
    def __init__(self):
        self.data = {}
        self.available = True
        self.read_count = 0
        self.write_count = 0

    def _check_availability(self):
        if not self.available:
            raise ConnectionError("Database is unavailable")

    def write(self, key, value):
        self._check_availability()

        self.data[key] = value
        self.write_count += 1

        print(f"[DATABASE] WRITE: {key} = {value}")

    def read(self, key):
        self._check_availability()

        self.read_count += 1
        value = self.data.get(key)

        print(f"[DATABASE] READ: {key} = {value}")

        return value

    def get_stats(self):
        return {
            "total_records": len(self.data),
            "read_operations": self.read_count,
            "write_operations": self.write_count,
        }


class Application:
    def __init__(self, database):
        self.database = database

    def create_product(self, product_id, product_name):
        print("\n[APPLICATION] Creating product")

        self.database.write(product_id, product_name)

    def get_product(self, product_id):
        print("\n[APPLICATION] Fetching product")

        return self.database.read(product_id)


def main():
    # Create a single database instance.
    database = Database()

    # Application uses this database for every operation.
    application = Application(database)

    print("=" * 50)
    print("SINGLE DATABASE ARCHITECTURE")
    print("=" * 50)

    # Write operations.
    application.create_product("P101", "Laptop")
    application.create_product("P102", "Mobile")
    application.create_product("P103", "Keyboard")

    # Read operations.
    application.get_product("P101")
    application.get_product("P102")
    application.get_product("P103")
    application.get_product("P101")

    # Display database statistics.
    print("\n" + "=" * 50)
    print("DATABASE STATISTICS")
    print("=" * 50)

    stats = database.get_stats()

    for key, value in stats.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    # Demonstrate single point of availability.
    print("\n" + "=" * 50)
    print("DATABASE FAILURE SIMULATION")
    print("=" * 50)

    database.available = False

    try:
        application.get_product("P101")
    except ConnectionError as error:
        print(f"[APPLICATION ERROR] {error}")

    try:
        application.create_product("P104", "Monitor")
    except ConnectionError as error:
        print(f"[APPLICATION ERROR] {error}")

    print("\nAll database operations now fail because")
    print("the application has only one database node.")


if __name__ == "__main__":
    main()
