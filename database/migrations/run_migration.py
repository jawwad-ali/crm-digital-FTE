"""Run SQL migration files against the database using asyncpg.

Usage:
    python -m database.migrations.run_migration
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)


async def run(dsn: str | None = None) -> None:
    dsn = dsn or os.environ["DATABASE_URL"]
    sql_file = Path(__file__).parent / "001_initial_schema.sql"
    sql = sql_file.read_text(encoding="utf-8")

    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(sql)
        logger.info("Migration applied: %s", sql_file.name)

        # Verify tables
        rows = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        )
        tables = [r["tablename"] for r in rows]
        print(f"Tables created ({len(tables)}): {', '.join(tables)}")
    finally:
        await conn.close()


async def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    await run()


if __name__ == "__main__":
    asyncio.run(main())
