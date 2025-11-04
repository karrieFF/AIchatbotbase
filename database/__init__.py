"""
Database module for PostgreSQL operations.

This module provides both synchronous and asynchronous database operations
for storing and retrieving chat conversation history.
"""

from .db_sync import (
    init_sync_pool,
    close_sync_pool,
    save_message_sync
)

from .db_async import (
    init_db_pool,
    close_db_pool,
    save_message
)

__all__ = [
    'init_sync_pool',
    'close_sync_pool',
    'save_message_sync',
    'init_db_pool',
    'close_db_pool',
    'save_message',
]

