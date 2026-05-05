"""Test that worker render failures get reported to Sentry."""

import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import fakeredis.aioredis
import pytest


@pytest.fixture
def tmp_db_engine():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "portal.db"
        url = f"sqlite:///{db_path}"
        # Import models package first so SQLModel table classes register
        # on SQLModel.metadata before init_schema runs create_all.
        import app.core.db.models  # noqa: F401
        from app.core.db.session import create_engine_for_url, init_schema

        engine = create_engine_for_url(url)
        init_schema(engine)
        yield engine, Path(tmp)


@pytest.mark.asyncio
async def test_render_failure_captures_to_sentry(tmp_db_engine) -> None:
    """When the render path raises, sentry_sdk.capture_exception is called."""
    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    fake = fakeredis.aioredis.FakeRedis()
    ctx = {
        "redis": fake,
        "engine": engine,
        "content_dir": content_dir,
        "image_size": 256,
    }

    # Passing a non-UUID model_id forces uuidmod.UUID() to raise inside the
    # try block — that's an exception path, which should be captured.
    from render.worker import render_model

    with patch("render.worker.sentry_sdk.capture_exception") as mock_capture:
        result = await render_model(ctx, "not-a-uuid")

    assert result["status"] == "failed"
    assert mock_capture.call_count == 1


@pytest.mark.asyncio
async def test_render_unknown_model_does_not_capture(tmp_db_engine) -> None:
    """Returning {'status':'failed'} for unknown model id is NOT a Sentry event."""
    engine, tmp_root = tmp_db_engine
    content_dir = tmp_root / "content"
    content_dir.mkdir()

    fake = fakeredis.aioredis.FakeRedis()
    ctx = {
        "redis": fake,
        "engine": engine,
        "content_dir": content_dir,
        "image_size": 256,
    }

    # A valid UUID for a model that doesn't exist in the DB — this is a data
    # condition (returns failed), not an exception, so Sentry is not called.
    from render.worker import render_model

    missing_id = str(uuid.uuid4())
    with patch("render.worker.sentry_sdk.capture_exception") as mock_capture:
        result = await render_model(ctx, missing_id)

    assert result["status"] == "failed"
    assert mock_capture.call_count == 0  # data condition, not exception
