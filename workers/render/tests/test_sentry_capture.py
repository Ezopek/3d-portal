"""Test that worker render failures get reported to Sentry."""

from unittest.mock import patch

import fakeredis.aioredis
import pytest

from render.worker import render_model


@pytest.mark.asyncio
async def test_render_failure_captures_to_sentry(tmp_path) -> None:
    """When the render path raises, sentry_sdk.capture_exception is called."""
    catalog_dir = tmp_path / "catalog"
    (catalog_dir / "_index").mkdir(parents=True)
    # Deliberately malformed index so json.loads explodes inside the try block.
    (catalog_dir / "_index" / "index.json").write_text("not json")
    renders_dir = tmp_path / "renders"
    renders_dir.mkdir()

    fake = fakeredis.aioredis.FakeRedis()
    ctx = {
        "redis": fake,
        "catalog_dir": str(catalog_dir),
        "renders_dir": str(renders_dir),
        "image_size": 256,
    }

    with patch("render.worker.sentry_sdk.capture_exception") as mock_capture:
        result = await render_model(ctx, "any-id")

    assert result["status"] == "failed"
    assert mock_capture.call_count == 1


@pytest.mark.asyncio
async def test_render_unknown_model_does_not_capture(tmp_path) -> None:
    """Returning {'status':'failed'} for unknown model id is NOT a Sentry event."""
    catalog_dir = tmp_path / "catalog"
    (catalog_dir / "_index").mkdir(parents=True)
    (catalog_dir / "_index" / "index.json").write_text("[]")
    renders_dir = tmp_path / "renders"
    renders_dir.mkdir()

    fake = fakeredis.aioredis.FakeRedis()
    ctx = {
        "redis": fake,
        "catalog_dir": str(catalog_dir),
        "renders_dir": str(renders_dir),
        "image_size": 256,
    }

    with patch("render.worker.sentry_sdk.capture_exception") as mock_capture:
        result = await render_model(ctx, "no-such-model")

    assert result["status"] == "failed"
    assert mock_capture.call_count == 0  # data condition, not exception
