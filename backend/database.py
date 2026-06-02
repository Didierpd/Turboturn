"""
database.py
Conexión a PostgreSQL (Amazon RDS) mediante pool de hilos.

Pool: mínimo 5 conexiones, máximo 50 (ThreadedConnectionPool).
Usar get_connection() en cada endpoint; PooledConnection devuelve
la conexión al pool al llamar .close(), no la cierra de verdad.
Credenciales leídas desde .env: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT.
"""

import psycopg2
import psycopg2.extras
from psycopg2 import pool
import threading
import os
from dotenv import load_dotenv

load_dotenv()

# ── Configuración de conexión (leída desde .env) ──────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "connect_timeout": 5,
}

# ── Pool de conexiones (singleton, inicializado al primer uso) ────────────────
_connection_pool = None
_pool_lock = threading.Lock()


# ── Wrapper que devuelve la conexión al pool en vez de cerrarla ───────────────
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


# ── Inicializa el pool con doble check para thread safety ────────────────────
def _get_connection_pool():
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                _connection_pool = pool.ThreadedConnectionPool(5, 50, **DB_CONFIG)
    return _connection_pool


# ── Función pública para obtener una conexión del pool ───────────────────────
def get_connection():
    connection_pool = _get_connection_pool()
    return PooledConnection(connection_pool.getconn(), connection_pool)
