"""
routes/historial.py
Historial de servicios completados para un cliente.

  GET /api/historial/{usuario_id}  → servicios realizados con detalle de cita, vehículo y costo
"""

from fastapi import APIRouter, HTTPException
import psycopg2.extras
from database import get_connection

router = APIRouter()


# ── Historial de servicios completados del cliente (con vehículo y costo) ─────
@router.get("/{usuario_id}", summary="Historial de servicios del usuario")
def get_historial(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT hs.id, hs.observaciones, hs.costo_final, hs.fecha,
                   s.nombre AS servicio,
                   v.marca, v.placa, v.tipo_vehiculo,
                   c.fecha_hora, c.estado AS estado_cita
            FROM historial_servicios hs
            JOIN citas c ON hs.cita_id = c.id
            JOIN servicios s ON hs.servicio_id = s.id
            JOIN vehiculos v ON c.vehiculo_id = v.id
            WHERE c.usuario_id = %s
            ORDER BY hs.fecha DESC
            """,
            (usuario_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener historial")
    finally:
        cur.close()
        conn.close()
