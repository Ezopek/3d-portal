def test_sqlite_engine_runs_in_wal_mode():
    """WAL is required so api + render worker can both write concurrently."""
    from app.core.db.session import get_engine

    engine = get_engine()
    if not str(engine.url).startswith("sqlite"):
        return  # not applicable for postgres
    with engine.connect() as conn:
        mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
        assert mode is not None and mode.lower() == "wal", f"expected WAL, got {mode!r}"


def test_sqlite_engine_has_busy_timeout():
    from app.core.db.session import get_engine

    engine = get_engine()
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.connect() as conn:
        timeout = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
        assert timeout is not None and int(timeout) >= 5000
