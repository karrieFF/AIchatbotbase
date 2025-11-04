import os
import json
from psycopg2.pool import ThreadedConnectionPool
import uuid
from typing import Optional, Union

pg_pool: Optional[ThreadedConnectionPool] = None # The pool can be pool or None, it can be written as Optional[asyncpg.pool.Pool]

def _build_dsn() -> str:
    user = os.environ.get("DB_USER", "chatbot_user")
    password = os.environ.get("DB_PASSWORD", "chatbot2025")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    db = os.environ.get("DB_NAME", "chatbot_db")
    return f"host={host} port={port} dbname={db} user={user} password={password}"


def init_sync_pool(minconn: int = 1, maxconn: int = 10) -> None: #async 异步的
    global pg_pool
    if pg_pool is None:
        dsn = _build_dsn()
        pg_pool = ThreadedConnectionPool(minconn, maxconn, dsn)

def close_sync_pool() -> None:
    global pg_pool
    if pg_pool:
        pg_pool.closeall()

def save_message_sync(
    session_id: Union[str, uuid.UUID], 
    user_id: Union[str, uuid.UUID], 
    role: str, 
    text: str, 
    metadata: dict | None = None) -> None:
    if pg_pool is None:
        raise RuntimeError("pg_pool not initialized")
    conn = pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (session_id, user_id, role, text, metadata) VALUES (%s,%s,%s,%s,%s)",
                (session_id, user_id, role, text, json,dumps(metadata or {}))
            )
        conn.commit()

    finally:
        pg_pool.putconn(conn)

