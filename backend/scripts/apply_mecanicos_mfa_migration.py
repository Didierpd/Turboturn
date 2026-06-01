from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
from database import get_connection


def main():
    sql_path = Path(__file__).resolve().parents[2] / "database" / "mecanicos_mfa_migration.sql"
    sql = sql_path.read_text(encoding="utf-8")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    print("Mecanicos MFA migration applied.")


if __name__ == "__main__":
    main()
