"""
routes/mecanicos.py
Gestión de mecánicos por taller y flujo de trabajo de citas asignadas.

  GET    /api/mecanicos/taller/{usuario_id}               → listar mecánicos del taller
  POST   /api/mecanicos/taller/{usuario_id}               → registrar mecánico
  PUT    /api/mecanicos/{id}/taller/{usuario_id}          → actualizar datos del mecánico
  POST   /api/mecanicos/login                             → login del mecánico (fase 1, soporta MFA)
  PUT    /api/mecanicos/{id}/taller/{usuario_id}/password → cambiar contraseña
  DELETE /api/mecanicos/{id}/taller/{usuario_id}          → eliminar (solo sin citas asociadas)
  GET    /api/mecanicos/{id}/citas                        → citas asignadas al mecánico
  PUT    /api/mecanicos/{id}/citas/{cita_id}/revision     → guardar diagnóstico inicial
  PUT    /api/mecanicos/{id}/citas/{cita_id}/terminar     → cerrar trabajo y registrar en historial
  PUT    /api/mecanicos/{id}/taller/{usuario_id}/estado   → activar / desactivar mecánico
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import psycopg2.extras
import hashlib

from database import get_connection
from email_utils import enviar_correo_trabajo_finalizado

router = APIRouter()


# ── Modelos de datos ──────────────────────────────────────────────────────────
class MecanicoData(BaseModel):
    nombre: str
    email: EmailStr
    password: Optional[str] = None
    telefono: Optional[str] = None
    especialidad: Optional[str] = None


class MecanicoLogin(BaseModel):
    email: EmailStr
    password: str


class MecanicoPasswordData(BaseModel):
    password: str


class TerminarTrabajoData(BaseModel):
    servicio_id: int
    observaciones: Optional[str] = None
    costo_final: Optional[float] = None


class RevisionTrabajoData(BaseModel):
    tiempo_estimado_revision: str
    trabajo_requerido: str


# ── Helper: hashea contraseña con SHA-256 ────────────────────────────────────
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── Helper: obtiene el taller_id a partir del usuario_id del admin ────────────
def _get_taller_id(cur, usuario_id: int):
    cur.execute("SELECT id FROM talleres WHERE admin_id = %s", (usuario_id,))
    taller = cur.fetchone()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado para este usuario.")
    return taller["id"]


# ── Listar mecánicos del taller ───────────────────────────────────────────────
@router.get("/taller/{usuario_id}", summary="Listar mecánicos de un taller")
def get_mecanicos_taller(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        taller_id = _get_taller_id(cur, usuario_id)
        cur.execute(
            """
            SELECT id, taller_id, nombre, email, telefono, especialidad, activo, creado_en
            FROM mecanicos
            WHERE taller_id = %s
            ORDER BY activo DESC, nombre
            """,
            (taller_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener mecánicos")
    finally:
        cur.close()
        conn.close()


# ── Registrar mecánico nuevo en el taller ────────────────────────────────────
@router.post("/taller/{usuario_id}", summary="Registrar mecánico en un taller")
def create_mecanico(usuario_id: int, data: MecanicoData):
    nombre = data.nombre.strip()
    if len(nombre) < 3:
        raise HTTPException(status_code=400, detail="El nombre del mecánico debe tener al menos 3 caracteres.")
    if not data.password or len(data.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña del mecánico debe tener al menos 6 caracteres.")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        taller_id = _get_taller_id(cur, usuario_id)
        cur.execute("SELECT id FROM mecanicos WHERE LOWER(email) = LOWER(%s)", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Ya existe un mecánico con ese correo.")
        cur.execute("SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s)", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Ese correo ya está registrado en otra cuenta.")

        cur.execute(
            """
            INSERT INTO mecanicos (taller_id, nombre, email, contrasena, telefono, especialidad)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, taller_id, nombre, email, telefono, especialidad, activo, creado_en
            """,
            (taller_id, nombre, data.email.lower(), _hash_password(data.password), data.telefono, data.especialidad),
        )
        conn.commit()
        return dict(cur.fetchone())
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al registrar mecánico")
    finally:
        cur.close()
        conn.close()


# ── Actualizar datos del mecánico (nombre, email, teléfono, especialidad) ─────
@router.put("/{mecanico_id}/taller/{usuario_id}", summary="Actualizar mecánico de un taller")
def update_mecanico(mecanico_id: int, usuario_id: int, data: MecanicoData):
    nombre = data.nombre.strip()
    if len(nombre) < 3:
        raise HTTPException(status_code=400, detail="El nombre del mecánico debe tener al menos 3 caracteres.")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        taller_id = _get_taller_id(cur, usuario_id)
        cur.execute(
            "SELECT id FROM mecanicos WHERE LOWER(email) = LOWER(%s) AND id <> %s",
            (data.email, mecanico_id),
        )
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Ya existe un mecánico con ese correo.")
        cur.execute("SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s)", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Ese correo ya está registrado en otra cuenta.")

        cur.execute(
            """
            UPDATE mecanicos
            SET nombre = %s, email = %s, telefono = %s, especialidad = %s
            WHERE id = %s AND taller_id = %s
            RETURNING id, taller_id, nombre, email, telefono, especialidad, activo, creado_en
            """,
            (nombre, data.email.lower(), data.telefono, data.especialidad, mecanico_id, taller_id),
        )
        mecanico = cur.fetchone()
        if not mecanico:
            raise HTTPException(status_code=404, detail="Mecánico no encontrado")
        conn.commit()
        return dict(mecanico)
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar mecánico")
    finally:
        cur.close()
        conn.close()


# ── Login del mecánico fase 1 (también soporta MFA) ──────────────────────────
@router.post("/login", summary="Iniciar sesión como mecánico")
def login_mecanico(data: MecanicoLogin):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT m.id, m.taller_id, m.nombre, m.email, m.telefono, m.especialidad,
                   m.activo, m.contrasena, m.mfa_habilitado, t.nombre AS taller
            FROM mecanicos m
            JOIN talleres t ON m.taller_id = t.id
            WHERE LOWER(m.email) = LOWER(%s)
            """,
            (data.email,),
        )
        mecanico = cur.fetchone()
        if not mecanico:
            raise HTTPException(status_code=404, detail="El mecánico no existe.")
        if not mecanico["activo"]:
            raise HTTPException(status_code=403, detail="El mecánico está inactivo.")
        if mecanico["contrasena"] != _hash_password(data.password):
            raise HTTPException(status_code=401, detail="Contraseña incorrecta.")

        if mecanico.get("mfa_habilitado"):
            return {
                "mfa_requerido": True,
                "usuario_id": mecanico["id"],
                "cuenta_tipo": "mecanico",
                "mensaje": "Ingresa el código de Google Authenticator para continuar.",
            }

        mecanico = dict(mecanico)
        mecanico.pop("contrasena", None)
        mecanico.pop("mfa_habilitado", None)
        mecanico["rol"] = "mecanico"
        return {
            "mfa_requerido": False,
            "mensaje": "Login exitoso.",
            "usuario": mecanico,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error en el login del mecánico")
    finally:
        cur.close()
        conn.close()


# ── Cambiar contraseña del mecánico ──────────────────────────────────────────
@router.put("/{mecanico_id}/taller/{usuario_id}/password", summary="Cambiar contraseña de un mecánico")
def cambiar_password_mecanico(mecanico_id: int, usuario_id: int, data: MecanicoPasswordData):
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        taller_id = _get_taller_id(cur, usuario_id)
        cur.execute(
            """
            UPDATE mecanicos
            SET contrasena = %s
            WHERE id = %s AND taller_id = %s
            RETURNING id
            """,
            (_hash_password(data.password), mecanico_id, taller_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Mecánico no encontrado")
        conn.commit()
        return {"mensaje": "Contraseña del mecánico actualizada."}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al cambiar contraseña del mecánico")
    finally:
        cur.close()
        conn.close()


# ── Eliminar mecánico (solo si no tiene citas asociadas, si tiene → desactivar) ─
@router.delete("/{mecanico_id}/taller/{usuario_id}", summary="Eliminar mecánico de un taller")
def delete_mecanico(mecanico_id: int, usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        taller_id = _get_taller_id(cur, usuario_id)
        cur.execute(
            "SELECT id FROM mecanicos WHERE id = %s AND taller_id = %s",
            (mecanico_id, taller_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Mecánico no encontrado")

        cur.execute("SELECT id FROM citas WHERE mecanico_id = %s LIMIT 1", (mecanico_id,))
        if cur.fetchone():
            raise HTTPException(
                status_code=400,
                detail="No puedes eliminar este mecánico porque ya tiene citas asociadas. Puedes desactivarlo.",
            )

        cur.execute("DELETE FROM mecanicos WHERE id = %s RETURNING id", (mecanico_id,))
        conn.commit()
        return {"mensaje": "Mecánico eliminado correctamente."}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar mecánico")
    finally:
        cur.close()
        conn.close()


# ── Citas asignadas al mecánico (vista del panel mecánico) ───────────────────
@router.get("/{mecanico_id}/citas", summary="Citas asignadas a un mecánico")
def get_citas_mecanico(mecanico_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT c.id, c.fecha_hora, c.estado, c.notas,
                   c.tiempo_estimado_revision, c.trabajo_requerido,
                   u.nombre AS cliente,
                   v.marca, v.placa, v.tipo_vehiculo,
                   t.nombre AS taller
            FROM citas c
            JOIN usuarios u ON c.usuario_id = u.id
            JOIN vehiculos v ON c.vehiculo_id = v.id
            JOIN talleres t ON c.taller_id = t.id
            JOIN mecanicos m ON c.mecanico_id = m.id
            WHERE c.mecanico_id = %s
              AND m.activo = TRUE
            ORDER BY c.fecha_hora DESC
            """,
            (mecanico_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener citas del mecánico")
    finally:
        cur.close()
        conn.close()


# ── Guardar diagnóstico inicial: tiempo estimado y trabajo requerido ──────────
@router.put("/{mecanico_id}/citas/{cita_id}/revision", summary="Guardar revisión inicial del mecánico")
def guardar_revision_mecanico(mecanico_id: int, cita_id: int, data: RevisionTrabajoData):
    # Este apartado permite que el mecánico registre el diagnóstico antes de cerrar el trabajo.
    tiempo_estimado = data.tiempo_estimado_revision.strip()
    trabajo_requerido = data.trabajo_requerido.strip()

    if len(tiempo_estimado) < 2:
        raise HTTPException(status_code=400, detail="Indica cuánto tiempo puede demorar el trabajo.")
    if len(trabajo_requerido) < 5:
        raise HTTPException(status_code=400, detail="Describe qué toca realizar después de la revisión.")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            UPDATE citas c
            SET tiempo_estimado_revision = %s,
                trabajo_requerido = %s
            FROM mecanicos m
            WHERE c.id = %s
              AND c.mecanico_id = %s
              AND c.mecanico_id = m.id
              AND c.estado = 'confirmada'
              AND m.activo = TRUE
            RETURNING c.id, c.tiempo_estimado_revision, c.trabajo_requerido
            """,
            (tiempo_estimado, trabajo_requerido, cita_id, mecanico_id),
        )
        revision = cur.fetchone()
        if not revision:
            raise HTTPException(status_code=404, detail="Cita confirmada no encontrada para este mecánico.")

        conn.commit()
        return dict(revision)
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar la revisión del mecánico")
    finally:
        cur.close()
        conn.close()


# ── Cerrar trabajo: registra en historial, cambia cita a 'completada' y notifica al cliente ─
@router.put("/{mecanico_id}/citas/{cita_id}/terminar", summary="Marcar trabajo asignado como terminado")
def terminar_cita_mecanico(mecanico_id: int, cita_id: int, data: TerminarTrabajoData):
    if data.costo_final is not None and data.costo_final < 0:
        raise HTTPException(status_code=400, detail="El costo final no puede ser negativo.")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT c.id, c.taller_id, c.estado, c.fecha_hora,
                   u.nombre AS cliente, u.email AS cliente_email,
                   t.nombre AS taller,
                   v.tipo_vehiculo, v.marca, v.placa
            FROM citas c
            JOIN mecanicos m ON c.mecanico_id = m.id
            JOIN usuarios u ON c.usuario_id = u.id
            JOIN talleres t ON c.taller_id = t.id
            JOIN vehiculos v ON c.vehiculo_id = v.id
            WHERE c.id = %s
              AND c.mecanico_id = %s
              AND c.estado = 'confirmada'
              AND m.activo = TRUE
            """,
            (cita_id, mecanico_id),
        )
        cita = cur.fetchone()
        if not cita:
            raise HTTPException(status_code=404, detail="Cita confirmada no encontrada para este mecánico.")

        cur.execute(
            """
            SELECT id, nombre, precio
            FROM servicios
            WHERE id = %s AND taller_id = %s
            """,
            (data.servicio_id, cita["taller_id"]),
        )
        servicio = cur.fetchone()
        if not servicio:
            raise HTTPException(status_code=400, detail="El servicio no pertenece al taller de esta cita.")

        costo_final = data.costo_final if data.costo_final is not None else servicio["precio"]
        observaciones = data.observaciones.strip() if data.observaciones else None

        cur.execute(
            "SELECT id FROM historial_servicios WHERE cita_id = %s ORDER BY id LIMIT 1",
            (cita_id,),
        )
        historial = cur.fetchone()
        if historial:
            cur.execute(
                """
                UPDATE historial_servicios
                SET servicio_id = %s, observaciones = %s, costo_final = %s, fecha = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (data.servicio_id, observaciones, costo_final, historial["id"]),
            )
        else:
            cur.execute(
                """
                INSERT INTO historial_servicios (cita_id, servicio_id, observaciones, costo_final)
                VALUES (%s, %s, %s, %s)
                """,
                (cita_id, data.servicio_id, observaciones, costo_final),
            )

        cur.execute(
            "UPDATE citas SET estado = 'completada' WHERE id = %s RETURNING id",
            (cita_id,),
        )
        conn.commit()

        correo_enviado = True
        try:
            enviar_correo_trabajo_finalizado(
                email_destino=cita["cliente_email"],
                cliente=cita["cliente"],
                taller=cita["taller"],
                fecha_hora=str(cita["fecha_hora"]),
                vehiculo=f"{cita['tipo_vehiculo']} {cita['marca']} ({cita['placa']})",
                servicio=servicio["nombre"],
                costo_final=float(costo_final),
                observaciones=observaciones,
            )
        except Exception:
            correo_enviado = False

        return {"mensaje": "Trabajo marcado como terminado.", "correo_enviado": correo_enviado}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al terminar la cita")
    finally:
        cur.close()
        conn.close()


# ── Activar o desactivar mecánico (sin eliminarlo) ───────────────────────────
@router.put("/{mecanico_id}/taller/{usuario_id}/estado", summary="Activar o desactivar mecánico")
def cambiar_estado_mecanico(mecanico_id: int, usuario_id: int, activo: bool):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        taller_id = _get_taller_id(cur, usuario_id)
        cur.execute(
            """
            UPDATE mecanicos
            SET activo = %s
            WHERE id = %s AND taller_id = %s
            RETURNING id, taller_id, nombre, email, telefono, especialidad, activo, creado_en
            """,
            (activo, mecanico_id, taller_id),
        )
        mecanico = cur.fetchone()
        if not mecanico:
            raise HTTPException(status_code=404, detail="Mecánico no encontrado")
        conn.commit()
        return dict(mecanico)
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al cambiar estado del mecánico")
    finally:
        cur.close()
        conn.close()
