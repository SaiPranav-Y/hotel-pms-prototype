# -*- coding: utf-8 -*-
"""
Shared pytest fixtures.

Every test runs against an isolated, freshly-seeded SQLite database in a temp
directory so tests never touch the developer's real voice_agent.db and never
interfere with each other.
"""

import pytest


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    """
    Point the app at a temp DB, (re)create the schema, seed rooms, and return
    the list of known locations. The DB is discarded when the temp dir is
    cleaned up by pytest.
    """
    from app import config
    from app.db import models

    db_path = str(tmp_path / "test_voice_agent.db")
    monkeypatch.setattr(config, "DB_PATH", db_path, raising=False)

    # seed() calls init_db(db_path), which rebinds the module-global engine +
    # session factory to this temp DB. So every later get_session() in the test
    # uses this isolated database.
    from app.db.seed import seed, all_locations
    seed(db_path)

    locations = all_locations()
    assert locations, "seed produced no locations"
    return {"db_path": db_path, "locations": locations}
