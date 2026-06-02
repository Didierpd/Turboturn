"""
Aplica la migración SQL de revisión de trabajo para mecánicos.

Uso esperado:
  python3 backend/scripts/apply_revision_mecanico_migration.py
"""

from pathlib import Path
import sys

# ── Bloque path: permite importar database.py desde la carpeta backend ───────
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
from database import get_connection


# ── Bloque ejecución: lee el SQL, lo ejecuta y confirma o revierte cambios ───
def main():
    # Aplica las columnas donde se guarda la revisión hecha por el mecánico.
    sql_path = Path(__file__).resolve().parents[2] / "database" / "revision_mecanico_migration.sql"
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

    print("Revision mecanico migration applied.")


if __name__ == "__main__":
    main()
