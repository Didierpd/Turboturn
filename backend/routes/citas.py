from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2.extras
from database import get_connection
from email_utils import enviar_correo_cancelacion_cita

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
            SELECT t.id, t.nombre, t.direccion, t.telefono, t.latitud, t.longitud
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
def cambiar_estado_cita(
    cita_id: int,
    estado: str,
    mecanico_id: Optional[int] = None,
    motivo_cancelacion: Optional[str] = None,
):
    estados_validos = ("pendiente", "confirmada", "completada", "cancelada")
    if estado not in estados_validos:
        raise HTTPException(status_code=400, detail="Estado no válido")
    if estado == "cancelada" and (not motivo_cancelacion or len(motivo_cancelacion.strip()) < 5):
        raise HTTPException(status_code=400, detail="Indica el motivo de cancelación para notificar al cliente.")

    datos_cancelacion = None
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if estado == "cancelada":
            # Datos necesarios para avisarle al cliente por correo por qué se canceló la cita.
            cur.execute(
                """
                SELECT c.id, c.fecha_hora,
                       u.nombre AS cliente, u.email AS cliente_email,
                       t.nombre AS taller,
                       v.tipo_vehiculo, v.marca, v.placa
                FROM citas c
                JOIN usuarios u ON c.usuario_id = u.id
                JOIN talleres t ON c.taller_id = t.id
                JOIN vehiculos v ON c.vehiculo_id = v.id
                WHERE c.id = %s
                """,
                (cita_id,),
            )
            datos_cancelacion = cur.fetchone()
            if not datos_cancelacion:
                raise HTTPException(status_code=404, detail="Cita no encontrada")

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

        if estado == "cancelada" and datos_cancelacion:
            try:
                enviar_correo_cancelacion_cita(
                    email_destino=datos_cancelacion["cliente_email"],
                    cliente=datos_cancelacion["cliente"],
                    taller=datos_cancelacion["taller"],
                    fecha_hora=str(datos_cancelacion["fecha_hora"]),
                    vehiculo=f"{datos_cancelacion['tipo_vehiculo']} {datos_cancelacion['marca']} ({datos_cancelacion['placa']})",
                    motivo=motivo_cancelacion.strip(),
                )
            except Exception:
                # La cita queda cancelada aunque el proveedor de correo falle.
                return {
                    "mensaje": "Cita cancelada, pero no se pudo enviar el correo al cliente.",
                    "correo_enviado": False,
                }

        return {"mensaje": f"Cita actualizada a {estado}", "correo_enviado": estado == "cancelada"}
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
