"""
routes/vehiculos.py
Vehículos registrados por los clientes.

  GET    /api/vehiculos/{usuario_id}  → vehículos del usuario
  POST   /api/vehiculos/              → registrar vehículo nuevo
  DELETE /api/vehiculos/{id}          → eliminar vehículo (solo si no tiene citas asociadas)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2.extras
from database import get_connection

router = APIRouter()


# ── Modelo de datos para registrar un vehículo ───────────────────────────────
class VehiculoData(BaseModel):
    usuario_id: int
    tipo_vehiculo: str
    marca: str
    anio: int
    placa: str
    color: Optional[str] = None


# ── Vehículos del cliente ─────────────────────────────────────────────────────
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


# ── Registrar vehículo nuevo para un cliente ──────────────────────────────────
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


# ── Eliminar vehículo (bloqueado si ya tiene citas asociadas) ─────────────────
@router.delete("/{vehiculo_id}", summary="Eliminar un vehículo")
def delete_vehiculo(vehiculo_id: int, usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT id FROM vehiculos WHERE id = %s AND usuario_id = %s",
            (vehiculo_id, usuario_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")

        cur.execute("SELECT id FROM citas WHERE vehiculo_id = %s LIMIT 1", (vehiculo_id,))
        if cur.fetchone():
            raise HTTPException(
                status_code=400,
                detail="No puedes eliminar este vehículo porque ya tiene citas asociadas.",
            )

        cur.execute("DELETE FROM vehiculos WHERE id = %s RETURNING id", (vehiculo_id,))
        conn.commit()
        return {"mensaje": "Vehículo eliminado correctamente."}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar vehículo")
    finally:
        cur.close()
        conn.close()
