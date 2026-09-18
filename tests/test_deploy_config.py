"""Tests for the pieces a deployment depends on: table creation and configuration."""
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect

from app.config import DEV_JWT_SECRET, Settings
from app.init_db import create_tables


def test_create_tables_builds_the_schema_from_the_models():
    engine = create_engine("sqlite://")
    names = create_tables(engine)
    assert {"users", "entries"} <= set(names)
    assert {"users", "entries"} <= set(inspect(engine).get_table_names())


def test_create_tables_is_safe_to_run_twice():
    """A container restart runs init again against a database that already has tables."""
    engine = create_engine("sqlite://")
    create_tables(engine)
    create_tables(engine)  # must not raise
    assert "users" in inspect(engine).get_table_names()


def test_production_refuses_the_default_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret=DEV_JWT_SECRET)


def test_production_accepts_a_real_secret():
    s = Settings(environment="production", jwt_secret="x" * 48)
    assert s.environment == "production"


def test_development_allows_the_default_secret():
    assert Settings(environment="development").jwt_secret == DEV_JWT_SECRET


def test_cors_origins_are_split_and_trimmed():
    s = Settings(cors_origins=" https://a.example ,https://b.example,, ")
    assert s.cors_origin_list == ["https://a.example", "https://b.example"]
