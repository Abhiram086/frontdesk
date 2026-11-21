import os
from pathlib import Path
import psycopg

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def main():
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY)"
        )
        done = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,)
            )
            print("applied", path.name)


if __name__ == "__main__":
    main()