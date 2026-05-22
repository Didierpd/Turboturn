import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "host": "turboturb-db.cd6wwa42q63k.us-east-2.rds.amazonaws.com",
    "database": "postgres",
    "user": "postgres",
    "password": "Turboturn2026*",
    "port": 5432,
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)
