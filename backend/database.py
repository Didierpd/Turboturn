import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "host": "localhost",
    "database": "Turboturn_db",
    "user": "postgres",
    "password": "1234",
    "port": 5432,
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)
