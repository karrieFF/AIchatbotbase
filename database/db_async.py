import os
import json
import asyncpg
import uuid
from typing import Optional, Union

pool: Optional[asyncpg.pool.Pool] = None # The pool can be pool or None, it can be written as Optional[asyncpg.pool.Pool]

def _build_dsn() -> str:

    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return dsn
        #print("DSN found, using cloud database")

        
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT")
    db = os.environ.get("DB_NAME")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
async def init_db_pool(min_size: int = 1, max_size: int = 10): #async 异步的
    global pool
    if pool is None:
        dsn = _build_dsn()
        pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)

async def close_db_pool():
    global pool
    if pool:
        await pool.close()

async def save_message(
    session_id: Union[str, uuid.UUID], 
    user_id: Union[str, uuid.UUID], 
    role: str, 
    text: str, 
    metadata: dict | None = None):
    if pool is None:
        raise RuntimeError("Db pool not initialized")
    q = """
    INSERT INTO messages (session_id, user_id, role, text, metadata)
    VALUES ($1::uuid, $2::uuid, $3, $4, $5::jsonb)
    """
    async with pool.acquire() as conn:
        # asyncpg accepts native Python dicts for JSONB, but we convert to JSON string for clarity
        await conn.execute(q, session_id, user_id, role, text, json.dumps(metadata or {}))
