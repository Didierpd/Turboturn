from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import psycopg2.extras
import hashlib

from database import get_connection

router = APIRouter()


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


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _get_taller_id(cur, usuario_id: int):
    cur.execute("SELECT id FROM talleres WHERE admin_id = %s", (usuario_id,))
    taller = cur.fetchone()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado para este usuario.")
    return taller["id"]


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


@router.post("/login", summary="Iniciar sesión como mecánico")
def login_mecanico(data: MecanicoLogin):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT m.id, m.taller_id, m.nombre, m.email, m.telefono, m.especialidad,
                   m.activo, m.contrasena, t.nombre AS taller
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

        mecanico = dict(mecanico)
        mecanico.pop("contrasena", None)
        mecanico["rol"] = "mecanico"
        return {
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


@router.put("/{mecanico_id}/citas/{cita_id}/terminar", summary="Marcar trabajo asignado como terminado")
def terminar_cita_mecanico(mecanico_id: int, cita_id: int, data: TerminarTrabajoData):
    if data.costo_final is not None and data.costo_final < 0:
        raise HTTPException(status_code=400, detail="El costo final no puede ser negativo.")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT c.id, c.taller_id, c.estado
            FROM citas c
            JOIN mecanicos m ON c.mecanico_id = m.id
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
            SELECT id, precio
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
        return {"mensaje": "Trabajo marcado como terminado."}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al terminar la cita")
    finally:
        cur.close()
        conn.close()


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
