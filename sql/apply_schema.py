"""Apply ``sql/schema.sql`` to Supabase.

Two strategies, in order:
  1. Direct PostgreSQL connection via ``DATABASE_URL`` (env var). Requires
     ``psycopg2-binary`` (optional dependency — install if needed).
  2. Manual: print the SQL so the user can paste it into the Supabase
     SQL Editor at https://app.supabase.com/project/_/sql.

Usage:
    $ pip install psycopg2-binary            # optional
    $ export DATABASE_URL="postgresql://..."   # optional
    $ python sql/apply_schema.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def read_schema() -> str:
    return SCHEMA_PATH.read_text(encoding="utf-8")


def try_direct_apply() -> bool:
    """Try to apply schema via psycopg2 + DATABASE_URL."""
    try:
        import psycopg2  # type: ignore
    except ImportError:
        print("💡 Hint: install psycopg2-binary for direct apply "
              "(pip install psycopg2-binary).")
        return False

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("⚠️  DATABASE_URL not in .env — needed for direct PostgreSQL apply.")
        return False

    schema = read_schema()
    print(f"📦 Connecting to {db_url.split('@')[-1]} …")
    conn = psycopg2.connect(db_url)
    try:
        conn.set_isolation_level(0)  # autocommit (needed for CREATE EXTENSION)
        cur = conn.cursor()
        cur.execute(schema)
        print("✅ Schema applied successfully.")
        return True
    except Exception as e:
        print(f"❌ Direct apply failed: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()


def print_for_manual() -> None:
    schema = read_schema()
    print("\n" + "=" * 72)
    print("MANUAL APPLY — paste the SQL below into Supabase SQL Editor:")
    print("https://app.supabase.com/project/_/sql")
    print("=" * 72 + "\n")
    print(schema)
    print("\n" + "=" * 72)


def main() -> int:
    print("🌟 Applying Supabase schema…")
    if try_direct_apply():
        return 0
    print()
    print_for_manual()
    return 1


if __name__ == "__main__":
    sys.exit(main())
