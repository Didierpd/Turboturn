from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2.extras
from database import get_connection

router = APIRouter()


class CitaData(BaseModel):
    usuario_id: int
    vehiculo_id: int
    taller_id: int
    fecha_hora: str
    notas: Optional[str] = None
    servicio_id: Optional[int] = None


@router.get("/talleres-activos", summary="Listar talleres activos")
def get_talleres_activos():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT t.id, t.nombre, t.direccion, t.telefono
            FROM talleres t
            JOIN usuarios u ON t.admin_id = u.id
            WHERE u.estado = 'activo'
            ORDER BY t.nombre
            """
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener talleres")
    finally:
        cur.close()
        conn.close()


@router.get("/taller/{usuario_id}/clientes", summary="Clientes del taller")
def get_clientes_taller(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT DISTINCT u.id, u.nombre, u.email, u.telefono,
                   v.marca, v.placa, v.tipo_vehiculo, v.anio
            FROM citas c
            JOIN usuarios u ON c.usuario_id = u.id
            JOIN vehiculos v ON c.vehiculo_id = v.id
            JOIN talleres t ON c.taller_id = t.id
            WHERE t.admin_id = %s
            ORDER BY u.nombre
            """,
            (usuario_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener clientes")
    finally:
        cur.close()
        conn.close()


@router.get("/taller/{usuario_id}", summary="Obtener citas del taller por usuario taller")
def get_citas_taller(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT c.id, c.fecha_hora, c.estado, c.notas, c.mecanico_id,
                   u.nombre AS cliente, v.marca, v.placa, v.tipo_vehiculo,
                   m.nombre AS mecanico_nombre
            FROM citas c
            JOIN usuarios u ON c.usuario_id = u.id
            JOIN vehiculos v ON c.vehiculo_id = v.id
            JOIN talleres t ON c.taller_id = t.id
            LEFT JOIN mecanicos m ON c.mecanico_id = m.id
            WHERE t.admin_id = %s
            ORDER BY c.fecha_hora DESC
            """,
            (usuario_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener citas del taller")
    finally:
        cur.close()
        conn.close()


@router.put("/{cita_id}/estado", summary="Cambiar estado de una cita")
def cambiar_estado_cita(cita_id: int, estado: str, mecanico_id: Optional[int] = None):
    estados_validos = ("pendiente", "confirmada", "completada", "cancelada")
    if estado not in estados_validos:
        raise HTTPException(status_code=400, detail="Estado no válido")
    conn = get_connection()
    cur = conn.cursor()
    try:
        if estado == "confirmada":
            if not mecanico_id:
                raise HTTPException(status_code=400, detail="Selecciona un mecánico para confirmar la cita.")

            cur.execute(
                """
                SELECT c.id
                FROM citas c
                JOIN mecanicos m ON m.id = %s
                WHERE c.id = %s
                  AND c.taller_id = m.taller_id
                  AND m.activo = TRUE
                """,
                (mecanico_id, cita_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=400, detail="El mecánico no pertenece al taller de esta cita o está inactivo.")

            cur.execute(
                "UPDATE citas SET estado=%s, mecanico_id=%s WHERE id=%s RETURNING id",
                (estado, mecanico_id, cita_id),
            )
        else:
            cur.execute(
                "UPDATE citas SET estado=%s WHERE id=%s RETURNING id",
                (estado, cita_id),
            )

        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Cita no encontrada")
        conn.commit()
        return {"mensaje": f"Cita actualizada a {estado}"}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar cita")
    finally:
        cur.close()
        conn.close()


@router.get("/{usuario_id}", summary="Obtener citas de un usuario")
def get_citas(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT c.*, v.marca, v.placa, t.nombre AS taller, m.nombre AS mecanico_nombre
            FROM citas c
            JOIN vehiculos v ON c.vehiculo_id = v.id
            JOIN talleres t ON c.taller_id = t.id
            LEFT JOIN mecanicos m ON c.mecanico_id = m.id
            WHERE c.usuario_id = %s
            ORDER BY c.fecha_hora DESC
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
            """SELECT COUNT(*) as total FROM citas
               WHERE taller_id = %s AND DATE(fecha_hora) = DATE(%s)""",
            (data.taller_id, data.fecha_hora),
        )
        if cur.fetchone()["total"] >= 10:
            raise HTTPException(status_code=400, detail="Este taller ya tiene 10 citas reservadas para ese dia.")

        cur.execute(
            """SELECT COUNT(*) as total FROM citas
               WHERE taller_id = %s AND fecha_hora = %s""",
            (data.taller_id, data.fecha_hora),
        )
        if cur.fetchone()["total"] > 0:
            raise HTTPException(status_code=400, detail="Ya hay una cita en ese taller para esa fecha y hora.")

        cur.execute(
            """INSERT INTO citas (usuario_id, vehiculo_id, taller_id, fecha_hora, notas, servicio_id)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
            (data.usuario_id, data.vehiculo_id, data.taller_id, data.fecha_hora, data.notas, data.servicio_id),
        )

        conn.commit()
        return dict(cur.fetchone())
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al crear cita")
    finally:
        cur.close()
        conn.close()
