import uuid

import fakeredis.aioredis
import pytest

from app.modules.share.service import ShareService

_USER_7 = uuid.UUID("00000000-0000-0000-0000-000000000007")
_USER_1 = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def service():
    fake = fakeredis.aioredis.FakeRedis()
    return ShareService(redis=fake)


@pytest.mark.asyncio
async def test_create_returns_token_and_persists(service):
    token = await service.create(model_id="001", expires_in_hours=24, created_by=_USER_7)
    assert len(token.token) >= 16
    assert token.model_id == "001"
    assert token.created_by == _USER_7

    fetched = await service.resolve(token.token)
    assert fetched is not None
    assert fetched.model_id == "001"


@pytest.mark.asyncio
async def test_resolve_unknown_returns_none(service):
    assert (await service.resolve("nope")) is None


@pytest.mark.asyncio
async def test_revoke_removes_token(service):
    token = await service.create(model_id="002", expires_in_hours=1, created_by=_USER_1)
    await service.revoke(token.token)
    assert (await service.resolve(token.token)) is None


@pytest.mark.asyncio
async def test_list_active_includes_all_tokens(service):
    t1 = await service.create(model_id="001", expires_in_hours=1, created_by=_USER_1)
    t2 = await service.create(model_id="002", expires_in_hours=1, created_by=_USER_1)
    listed = await service.list_active()
    tokens = {entry.token for entry in listed}
    assert t1.token in tokens
    assert t2.token in tokens


@pytest.mark.asyncio
async def test_ttl_zero_hours_is_rejected(service):
    with pytest.raises(ValueError):
        await service.create(model_id="001", expires_in_hours=0, created_by=_USER_1)
