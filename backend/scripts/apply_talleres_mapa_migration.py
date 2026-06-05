"""
Aplica la migración SQL que agrega coordenadas para el mapa de talleres.

Uso esperado:
  python3 backend/scripts/apply_talleres_mapa_migration.py
"""

from pathlib import Path
import sys

# ── Bloque path: permite importar database.py desde la carpeta backend ───────
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
from database import get_connection


# ── Bloque ejecución: lee el SQL, lo ejecuta y confirma o revierte cambios ───
def main():
    # Agrega coordenadas para mostrar los talleres en el mapa.
    sql_path = Path(__file__).resolve().parents[2] / "database" / "talleres_mapa_migration.sql"
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

    print("Talleres mapa migration applied.")


if __name__ == "__main__":
    main()
