# run_migrations.py - Run all database migrations
import sys
import os
from importlib import import_module
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_all_migrations():
    """Run all migration scripts in order"""

    migrations_dir = Path("migrations")
    migration_files = sorted(
        [f for f in migrations_dir.glob("add_*.py") if f.name != "__init__.py"]
    )

    print("🔄 Running database migrations...")

    for migration_file in migration_files:
        module_name = f"migrations.{migration_file.stem}"
        print(f"\n📝 Running migration: {migration_file.name}")

        try:
            module = import_module(module_name)
            if hasattr(module, "upgrade"):
                module.upgrade()
                print(f"✅ {migration_file.name} completed successfully")
            else:
                print(f"⚠️  {migration_file.name} has no upgrade function")
        except Exception as e:
            print(f"❌ Error running {migration_file.name}: {e}")
            return False

    print("\n✅ All migrations completed successfully!")
    return True


if __name__ == "__main__":
    success = run_all_migrations()
    sys.exit(0 if success else 1)
