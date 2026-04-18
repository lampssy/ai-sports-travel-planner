from __future__ import annotations

import os

import pytest

from app.config import env as env_module
from app.data.database import reset_database
from app.data.repositories import clear_repository_caches

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://planner:planner@127.0.0.1:5432/ai_sports_travel_planner_test",
)

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("TEST_DATABASE_URL", TEST_DATABASE_URL)

DB_FREE_TEST_FILES = {
    "test_env.py",
    "test_loader.py",
}


@pytest.fixture(autouse=True)
def reset_postgres_database(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    if request.node.path.name in DB_FREE_TEST_FILES:
        yield
        return

    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("TEST_DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setattr(env_module, "_loaded", False)
    clear_repository_caches()
    reset_database(TEST_DATABASE_URL)
    yield
    clear_repository_caches()
