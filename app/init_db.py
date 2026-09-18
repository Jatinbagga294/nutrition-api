"""Create the database tables. Run once before the API starts.

    python -m app.init_db

Idempotent: tables that already exist are left alone. Retries for a short while
because on a fresh deploy the database can still be accepting its first
connections when the container boots.

This creates tables from the ORM models. It does not migrate an existing schema,
so a column change needs a real migration tool (Alembic) before this is used on
data that matters.
"""
from __future__ import annotations

import sys
import time

from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from . import models  # noqa: F401  (importing registers every table on Base.metadata)
from .db import Base, get_engine


def create_tables(engine: Engine) -> list[str]:
    """Create every table the models define and return their names."""
    Base.metadata.create_all(engine)
    return sorted(Base.metadata.tables)


def main(attempts: int = 12, delay_seconds: float = 5.0) -> int:
    engine = get_engine()
    for attempt in range(1, attempts + 1):
        try:
            tables = create_tables(engine)
            print(f"database ready, tables: {', '.join(tables)}")
            return 0
        except OperationalError as err:
            reason = err.__class__.__name__
            print(f"database not reachable yet (attempt {attempt}/{attempts}): {reason}")
            time.sleep(delay_seconds)
    print("giving up: the database never became reachable", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
