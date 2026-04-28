from fastapi import APIRouter, HTTPException
import psycopg2.extras
from database import get_connection

router = APIRouter()


@router.get("/", summary="Obtener todos los servicios disponibles")
def get_servicios():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM servicios")
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener servicios")
    finally:
        cur.close()
        conn.close()
