# tests/test_db_async.py
import pytest
import asyncio
from db_async import save_message, pool

class DummyConn:
    async def execute(self, q, *args):
        assert "INSERT INTO messages" in q
        return

class DummyPool:
    def acquire(self):
        class Ctx:
            async def __aenter__(self_inner):
                return DummyConn()
            async def __aexit__(self_inner, exc_type, exc, tb):
                return False
        return Ctx()

@pytest.mark.asyncio
async def test_save_message(monkeypatch):
    # monkeypatch pool object
    import db_async
    monkeypatch.setattr(db_async, "pool", DummyPool())
    await save_message("11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222", "user", "hello", {"a":1})