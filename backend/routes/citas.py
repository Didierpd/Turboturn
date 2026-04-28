from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2.extras
from database import get_connection

router = APIRouter()


class CitaData(BaseModel):
    usuario_id: int
    vehiculo_id: int
    fecha_hora: str
    notas: Optional[str] = None


@router.get("/{usuario_id}", summary="Obtener citas de un usuario")
def get_citas(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT c.*, v.marca, v.placa
            FROM citas c
            JOIN vehiculos v ON c.vehiculo_id = v.id
            WHERE c.usuario_id = %s
            """,
            (usuario_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener citas")
    finally:
        cur.close()
        conn.close()


@router.post("/", summary="Reservar una cita")
def create_cita(data: CitaData):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """INSERT INTO citas (usuario_id, vehiculo_id, taller_id, fecha_hora, notas)
               VALUES (%s, %s, 1, %s, %s) RETURNING *""",
            (data.usuario_id, data.vehiculo_id, data.fecha_hora, data.notas),
        )
        conn.commit()
        return dict(cur.fetchone())
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al crear cita")
    finally:
        cur.close()
        conn.close()
