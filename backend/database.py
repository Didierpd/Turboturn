import psycopg2
import psycopg2.extras
from psycopg2 import pool
import threading

DB_CONFIG = {
    "host": "turboturb-db.cd6wwa42q63k.us-east-2.rds.amazonaws.com",
    "database": "postgres",
    "user": "postgres",
    "password": "Turboturn2026*",
    "port": 5432,
    "connect_timeout": 5,
}

_connection_pool = None
_pool_lock = threading.Lock()


class PooledConnection:
    def __init__(self, connection, connection_pool):
        self._connection = connection
        self._connection_pool = connection_pool
        self._closed = False

    def close(self):
        if self._closed:
            return
        self._connection_pool.putconn(self._connection)
        self._closed = True

    def __getattr__(self, name):
        return getattr(self._connection, name)


def _get_connection_pool():
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                _connection_pool = pool.ThreadedConnectionPool(1, 10, **DB_CONFIG)
    return _connection_pool


def get_connection():
    connection_pool = _get_connection_pool()
    return PooledConnection(connection_pool.getconn(), connection_pool)
