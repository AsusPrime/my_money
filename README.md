# My Money

Backend for a personal budgeting and investment-tracking app. Tracks budgets and transactions. Renders custom analytics charts. Tracks investment portfolio returns.

## Stack

- **Python 3.12**
- **FastAPI** — web framework
- **SQLAlchemy 2.0** (async) + **asyncpg** — ORM / Postgres driver
- **Alembic** — migrations
- **pydantic-settings** — config via `.env`
- **loguru** — logging
- **pytest** + **pytest-asyncio** + **httpx** — tests
- **ruff** + **black** — lint/format
- **Docker / docker-compose**

## Install & run

```bash
cp .env.example .env

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# start Postgres (or point .env at your own instance)
docker compose up -d db

uvicorn src.main:app --reload
```

App runs at `http://127.0.0.1:8000`, docs at `/docs`.

### Or just Docker

```bash
cp .env.example .env
docker compose up --build
```

### Tests

```bash
pytest
```

