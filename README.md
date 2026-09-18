# Nutrition API

REST backend for the [Calorie Tracker](https://github.com/Jatinbagga294/calorie-tracker)
app. Accounts, authentication, food entries, and daily nutrition totals.

The tracker started as a local-only PWA that kept everything in browser storage.
That works until you want the same data on a second device. This is the server
that fixes it.

## Stack

FastAPI, PostgreSQL, SQLAlchemy 2.0, JWT auth, pytest, Docker, GitHub Actions.

## Running it

```bash
docker compose up --build
```

API on http://localhost:8000, interactive docs on http://localhost:8000/docs.

Without Docker:

```bash
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Tests need no database. They run against SQLite in memory:

```bash
pytest
```

## Endpoints

| Method | Path | Auth | Does |
|---|---|---|---|
| POST | `/auth/signup` | no | Create an account |
| POST | `/auth/login` | no | Exchange email and password for a JWT |
| GET | `/auth/me` | yes | Current user |
| POST | `/entries` | yes | Log a food entry |
| GET | `/entries` | yes | List entries, filterable by day, paginated |
| GET | `/entries/summary` | yes | Totals for one day against the calorie goal |
| DELETE | `/entries/{id}` | yes | Delete one of your own entries |
| GET | `/health` | no | Liveness probe |

## Design decisions

**Schemas are separate from ORM models.** `models.py` is the database,
`schemas.py` is the API contract. The database stores a `password_hash` the API
must never return, and the API accepts a plaintext `password` the database never
stores. Keeping one class for both is how password hashes end up in JSON
responses.

**Authorization is a filter, not a check.** Every entry query includes
`where(Entry.user_id == user.id)`. There is no code path that reads entries
without it. Two tests exist specifically to prove one user cannot see or delete
another user's data, because that is the failure that actually matters here.

**Deleting someone else's entry returns 404, not 403.** A 403 would confirm the
id exists, which leaks information about other users' data.

**Login failures are indistinguishable.** Wrong password and unknown email
return the same message, so the endpoint cannot be used to enumerate which email
addresses have accounts. A test asserts the two responses are byte-identical.

**Passwords are capped at 72 bytes in the schema.** That is bcrypt's hard limit,
not an arbitrary number. Accepting longer ones means either silent truncation or
a 500 at signup, depending on the bcrypt version.

**The engine is created lazily.** Importing `app.db` does not open a connection
or require a Postgres driver to be installed. Otherwise the test suite, the
linter and `--help` would all need a live database.

**Daily totals are aggregated in SQL.** `/entries/summary` uses `SUM` and `COUNT`
in one query rather than loading a day of rows into Python and adding them up.

**`pool_pre_ping` is on.** Without it, a connection dropped by Postgres or a
proxy surfaces later as a random `OperationalError` on an unrelated request.

## Layout

```
app/
  main.py         app setup, CORS, router registration
  config.py       settings from environment, cached
  db.py           engine, session factory, request-scoped session dependency
  models.py       ORM models (the database schema)
  schemas.py      Pydantic request and response models (the API contract)
  auth.py         password hashing, JWT issue and verify, current_user dependency
  routers/
    auth.py       signup, login, me
    entries.py    entry CRUD and the daily summary
tests/
  conftest.py     in-memory SQLite fixtures, authenticated client
  test_auth.py    signup, login, token validation, user enumeration
  test_entries.py CRUD, validation, aggregation, cross-user isolation
```

## Tests

17 tests covering authentication, validation, aggregation and cross-user access
control.

```
pytest -q
17 passed
```

CI runs ruff and the full suite on every push, and builds the Docker image.

## Not done yet

- Alembic migrations. Tables are created from metadata; a real deployment needs
  versioned migrations.
- Refresh tokens. Access tokens expire after an hour with no refresh flow.
- Rate limiting on `/auth/login`.
- Wiring the Calorie Tracker PWA to this instead of browser storage.
