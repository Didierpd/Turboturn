from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2.extras
from database import get_connection

router = APIRouter()


class VehiculoData(BaseModel):
    usuario_id: int
    tipo_vehiculo: str
    marca: str
    anio: int
    placa: str
    color: Optional[str] = None


@router.get("/{usuario_id}", summary="Obtener vehículos de un usuario")
def get_vehiculos(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM vehiculos WHERE usuario_id=%s", (usuario_id,))
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener vehículos")
    finally:
        cur.close()
        conn.close()


@router.post("/", summary="Registrar un nuevo vehículo")
def create_vehiculo(data: VehiculoData):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """INSERT INTO vehiculos (usuario_id, tipo_vehiculo, marca, anio, placa, color)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (data.usuario_id, data.tipo_vehiculo, data.marca, data.anio, data.placa, data.color),
        )
        conn.commit()
        return dict(cur.fetchone())
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar vehículo")
    finally:
        cur.close()
        conn.close()
