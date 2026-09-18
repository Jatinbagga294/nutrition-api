"""Database engine, session factory, and the FastAPI dependency.

The engine is created lazily rather than at import time. Importing this module
must not require a reachable database or an installed Postgres driver, or the
test suite cannot run without Postgres, and neither can `--help` or a CI lint
step. Nothing touches the database until a request actually needs a session.
"""
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Base class every ORM model inherits from."""


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        # Verifies a pooled connection is alive before handing it out. Without
        # this, a connection dropped by the database or a proxy surfaces as a
        # random OperationalError on a later request.
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Request-scoped session. Always closed, even if the handler raises."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
