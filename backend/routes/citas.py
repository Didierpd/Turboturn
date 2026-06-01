from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2.extras
from database import get_connection
from email_utils import (
    enviar_correo_cancelacion_cita,
    enviar_correo_cita_confirmada,
    enviar_correo_cita_creada,
    enviar_correo_mecanico_asignado,
)

router = APIRouter()


class CitaData(BaseModel):
    usuario_id: int
    vehiculo_id: int
    taller_id: int
    fecha_hora: str
    notas: Optional[str] = None
    servicio_id: Optional[int] = None


def _fetchall_dict(cur):
    return [dict(row) for row in cur.fetchall()]


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


@router.get("/estadisticas/admin", summary="Estadísticas generales para administrador")
def estadisticas_admin():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT estado AS label, COUNT(*)::int AS total
            FROM citas
            GROUP BY estado
            ORDER BY total DESC
            """
        )
        citas_por_estado = _fetchall_dict(cur)

        cur.execute(
            """
            SELECT s.nombre AS label, COUNT(*)::int AS total
            FROM (
                SELECT servicio_id FROM citas WHERE servicio_id IS NOT NULL
                UNION ALL
                SELECT servicio_id FROM historial_servicios WHERE servicio_id IS NOT NULL
            ) usos
            JOIN servicios s ON s.id = usos.servicio_id
            GROUP BY s.id, s.nombre
            ORDER BY total DESC, s.nombre
            LIMIT 8
            """
        )
        servicios_mas_solicitados = _fetchall_dict(cur)

        cur.execute(
            """
            SELECT t.nombre AS label, COUNT(c.id)::int AS total
            FROM citas c
            JOIN talleres t ON t.id = c.taller_id
            GROUP BY t.id, t.nombre
            ORDER BY total DESC, t.nombre
            LIMIT 8
            """
        )
        talleres_con_mas_citas = _fetchall_dict(cur)

        cur.execute(
            """
            SELECT TO_CHAR(DATE_TRUNC('month', creado_en), 'YYYY-MM') AS label,
                   COUNT(*)::int AS total
            FROM usuarios
            WHERE rol = 'usuario'
              AND creado_en >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '11 months'
            GROUP BY DATE_TRUNC('month', creado_en)
            ORDER BY label
            """
        )
        clientes_por_mes = _fetchall_dict(cur)

        return {
            "citas_por_estado": citas_por_estado,
            "servicios_mas_solicitados": servicios_mas_solicitados,
            "talleres_con_mas_citas": talleres_con_mas_citas,
            "clientes_por_mes": clientes_por_mes,
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener estadísticas del administrador")
    finally:
        cur.close()
        conn.close()


@router.get("/estadisticas/taller/{usuario_id}", summary="Estadísticas del taller")
def estadisticas_taller(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id FROM talleres WHERE admin_id = %s", (usuario_id,))
        taller = cur.fetchone()
        if not taller:
            raise HTTPException(status_code=404, detail="Taller no encontrado para este usuario.")
        taller_id = taller["id"]

        cur.execute(
            """
            SELECT estado AS label, COUNT(*)::int AS total
            FROM citas
            WHERE taller_id = %s
            GROUP BY estado
            ORDER BY total DESC
            """,
            (taller_id,),
        )
        citas_por_estado = _fetchall_dict(cur)

        cur.execute(
            """
            SELECT s.nombre AS label, COUNT(*)::int AS total
            FROM (
                SELECT servicio_id FROM citas
                WHERE taller_id = %s AND servicio_id IS NOT NULL
                UNION ALL
                SELECT hs.servicio_id
                FROM historial_servicios hs
                JOIN citas c ON c.id = hs.cita_id
                WHERE c.taller_id = %s AND hs.servicio_id IS NOT NULL
            ) usos
            JOIN servicios s ON s.id = usos.servicio_id
            GROUP BY s.id, s.nombre
            ORDER BY total DESC, s.nombre
            LIMIT 8
            """,
            (taller_id, taller_id),
        )
        servicios_mas_solicitados = _fetchall_dict(cur)

        cur.execute(
            """
            SELECT TO_CHAR(DATE_TRUNC('month', u.creado_en), 'YYYY-MM') AS label,
                   COUNT(DISTINCT u.id)::int AS total
            FROM citas c
            JOIN usuarios u ON u.id = c.usuario_id
            WHERE c.taller_id = %s
              AND u.creado_en >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '11 months'
            GROUP BY DATE_TRUNC('month', u.creado_en)
            ORDER BY label
            """,
            (taller_id,),
        )
        clientes_por_mes = _fetchall_dict(cur)

        cur.execute(
            """
            SELECT COALESCE(m.nombre, 'Sin asignar') AS label, COUNT(c.id)::int AS total
            FROM citas c
            LEFT JOIN mecanicos m ON m.id = c.mecanico_id
            WHERE c.taller_id = %s
            GROUP BY COALESCE(m.nombre, 'Sin asignar')
            ORDER BY total DESC, label
            LIMIT 8
            """,
            (taller_id,),
        )
        mecanicos_con_mas_citas = _fetchall_dict(cur)

        return {
            "citas_por_estado": citas_por_estado,
            "servicios_mas_solicitados": servicios_mas_solicitados,
            "clientes_por_mes": clientes_por_mes,
            "mecanicos_con_mas_citas": mecanicos_con_mas_citas,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener estadísticas del taller")
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
    datos_confirmacion = None
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
                """
                SELECT c.id, c.fecha_hora,
                       u.nombre AS cliente, u.email AS cliente_email,
                       t.nombre AS taller,
                       v.tipo_vehiculo, v.marca, v.placa,
                       m.nombre AS mecanico, m.email AS mecanico_email
                FROM citas c
                JOIN usuarios u ON c.usuario_id = u.id
                JOIN talleres t ON c.taller_id = t.id
                JOIN vehiculos v ON c.vehiculo_id = v.id
                JOIN mecanicos m ON m.id = %s
                WHERE c.id = %s
                """,
                (mecanico_id, cita_id),
            )
            datos_confirmacion = cur.fetchone()
            if not datos_confirmacion:
                raise HTTPException(status_code=404, detail="Cita no encontrada")

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

        correo_enviado = None
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
                correo_enviado = True
            except Exception:
                # La cita queda cancelada aunque el proveedor de correo falle.
                return {
                    "mensaje": "Cita cancelada, pero no se pudo enviar el correo al cliente.",
                    "correo_enviado": False,
                }

        if estado == "confirmada" and datos_confirmacion:
            correo_enviado = True
            vehiculo = f"{datos_confirmacion['tipo_vehiculo']} {datos_confirmacion['marca']} ({datos_confirmacion['placa']})"
            try:
                enviar_correo_cita_confirmada(
                    email_destino=datos_confirmacion["cliente_email"],
                    cliente=datos_confirmacion["cliente"],
                    taller=datos_confirmacion["taller"],
                    fecha_hora=str(datos_confirmacion["fecha_hora"]),
                    vehiculo=vehiculo,
                    mecanico=datos_confirmacion["mecanico"],
                )
                if datos_confirmacion["mecanico_email"]:
                    enviar_correo_mecanico_asignado(
                        email_destino=datos_confirmacion["mecanico_email"],
                        mecanico=datos_confirmacion["mecanico"],
                        cliente=datos_confirmacion["cliente"],
                        taller=datos_confirmacion["taller"],
                        fecha_hora=str(datos_confirmacion["fecha_hora"]),
                        vehiculo=vehiculo,
                    )
            except Exception:
                correo_enviado = False

        return {"mensaje": f"Cita actualizada a {estado}", "correo_enviado": correo_enviado}
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
    cita_creada = None
    datos_correo = None
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
        cita_creada = dict(cur.fetchone())

        cur.execute(
            """
            SELECT c.fecha_hora,
                   u.nombre AS cliente, u.email AS cliente_email,
                   t.nombre AS taller,
                   v.tipo_vehiculo, v.marca, v.placa
            FROM citas c
            JOIN usuarios u ON c.usuario_id = u.id
            JOIN talleres t ON c.taller_id = t.id
            JOIN vehiculos v ON c.vehiculo_id = v.id
            WHERE c.id = %s
            """,
            (cita_creada["id"],),
        )
        datos_correo = cur.fetchone()

        conn.commit()
        correo_enviado = None
        if datos_correo:
            try:
                enviar_correo_cita_creada(
                    email_destino=datos_correo["cliente_email"],
                    cliente=datos_correo["cliente"],
                    taller=datos_correo["taller"],
                    fecha_hora=str(datos_correo["fecha_hora"]),
                    vehiculo=f"{datos_correo['tipo_vehiculo']} {datos_correo['marca']} ({datos_correo['placa']})",
                )
                correo_enviado = True
            except Exception:
                correo_enviado = False

        cita_creada["correo_enviado"] = correo_enviado
        return cita_creada
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al crear cita")
    finally:
        cur.close()
        conn.close()
