"""
routes/usuarios.py
Gestión de usuarios con soporte MFA en el login.

El login ahora tiene DOS fases:
  Fase 1 → POST /api/usuarios/login
           Valida email + contraseña.
           Si el usuario tiene MFA activo, devuelve:
             { "mfa_requerido": true, "usuario_id": <id> }
           Si NO tiene MFA, devuelve el usuario completo directamente.

  Fase 2 → POST /api/mfa/validar   (en routes/mfa.py)
           El frontend envía usuario_id + código TOTP.
           Si es válido, el frontend considera la sesión iniciada.
"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import psycopg2.extras
import hashlib
from datetime import time

from database import get_connection
from email_utils import generar_codigo, enviar_correo_verificacion, enviar_correo_recuperacion

router = APIRouter()


# ── Modelos de datos ──────────────────────────────────────────────────────────
class UsuarioRegistro(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    telefono: Optional[str] = None
    rol: Optional[str] = "usuario"
    nombre_taller: Optional[str] = None
    direccion_taller: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    horario_apertura: Optional[str] = None
    horario_cierre: Optional[str] = None

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


class TallerHorario(BaseModel):
    horario_apertura: str
    horario_cierre: str


# ── Helper: hashea la contraseña con SHA-256 ─────────────────────────────────
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _parse_horario(valor: str, campo: str) -> time:
    try:
        return time.fromisoformat(valor)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{campo} debe tener formato HH:MM.")


def _validar_rango_horario(apertura: str, cierre: str):
    hora_apertura = _parse_horario(apertura, "horario_apertura")
    hora_cierre = _parse_horario(cierre, "horario_cierre")
    if hora_apertura >= hora_cierre:
        raise HTTPException(status_code=400, detail="La hora de apertura debe ser menor que la hora de cierre.")


# ── Registro: guarda datos temporalmente y envía código de verificación por correo ─
@router.post("/registro", summary="Registrar nuevo usuario")
def registro(data: UsuarioRegistro):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id FROM usuarios WHERE email = %s", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El email ya está registrado.")
        cur.execute("SELECT id FROM mecanicos WHERE LOWER(email) = LOWER(%s)", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El email ya está registrado.")

        hashed = _hash_password(data.password)
        datos = {
            "nombre": data.nombre,
            "email": data.email,
            "contrasena": hashed,
            "telefono": data.telefono,
            "rol": data.rol,
            "nombre_taller": data.nombre_taller,
            "direccion_taller": data.direccion_taller,
            "latitud": data.latitud,
            "longitud": data.longitud,
            "horario_apertura": data.horario_apertura,
            "horario_cierre": data.horario_cierre,
        }

        if data.rol == "taller":
            apertura = data.horario_apertura or "08:00"
            cierre = data.horario_cierre or "18:00"
            _validar_rango_horario(apertura, cierre)
            datos["horario_apertura"] = apertura
            datos["horario_cierre"] = cierre

        codigo = generar_codigo()
        cur.execute(
            """
            INSERT INTO codigos_verificacion (email, codigo, datos_registro)
            VALUES (%s, %s, %s)
            """,
            (data.email, codigo, json.dumps(datos)),
        )
        conn.commit()

        enviar_correo_verificacion(data.email, data.nombre, codigo)

        return {"mensaje": "Te enviamos un código a tu correo. Ingrésalo para completar el registro."}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar usuario: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Login fase 1: valida email + contraseña (si tiene MFA, devuelve mfa_requerido: true) ─
@router.post("/login", summary="Iniciar sesión (fase 1 de 2 si MFA está activo)")
def login(data: UsuarioLogin):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        hashed = _hash_password(data.password)
        cur.execute(
            "SELECT id, nombre, email, telefono, rol, estado, mfa_habilitado, contrasena FROM usuarios WHERE email = %s",
            (data.email,),
        )
        usuario = cur.fetchone()

        if not usuario:
            # Evita una segunda petición desde el frontend cuando quien inicia sesión es un mecánico.
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
                raise HTTPException(status_code=404, detail="Correo o contraseña incorrectos.")
            if not mecanico["activo"]:
                raise HTTPException(status_code=403, detail="El mecánico está inactivo.")
            if mecanico["contrasena"] != hashed:
                raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")

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

        if usuario["estado"] != "activo":
            raise HTTPException(status_code=403, detail="Tu cuenta está restringida o pendiente de aprobación.")

        if usuario["contrasena"] != hashed:
            raise HTTPException(status_code=401, detail="Contraseña incorrecta.")

        usuario = dict(usuario)

        if usuario.get("mfa_habilitado"):
            return {
                "mfa_requerido": True,
                "usuario_id": usuario["id"],
                "mensaje": "Ingresa el código de Google Authenticator para continuar.",
            }

        usuario.pop("mfa_habilitado", None)
        # El superadmin entra al mismo panel que el admin pero con rol normalizado
        if usuario.get("rol") == "superadmin":
            usuario["rol"] = "admin"
        return {
            "mfa_requerido": False,
            "mensaje": "Login exitoso.",
            "usuario": usuario,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el login: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Talleres pendientes de aprobación (panel admin) ──────────────────────────
@router.get("/talleres-pendientes", summary="Listar talleres pendientes de aprobación")
def talleres_pendientes():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT id, nombre, email, telefono, creado_en FROM usuarios WHERE rol = 'taller' AND estado = 'pendiente'"
        )
        return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Listar todos los usuarios (panel admin → gestión de cuentas) ─────────────
@router.get("/todos", summary="Listar todos los usuarios")
def todos_usuarios():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # El superadmin no aparece en la interfaz, solo se gestiona desde la terminal
        cur.execute("SELECT id, nombre, email, rol, estado, telefono FROM usuarios WHERE rol != 'superadmin' ORDER BY id")
        return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Aprobar taller: cambia estado a 'activo' ─────────────────────────────────
@router.put("/{usuario_id}/aprobar", summary="Aprobar taller")
def aprobar_taller(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE usuarios SET estado = 'activo' WHERE id = %s AND rol = 'taller'", (usuario_id,))
        conn.commit()
        return {"mensaje": "Taller aprobado."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Rechazar taller: cambia estado a 'rechazado' ─────────────────────────────
@router.put("/{usuario_id}/rechazar", summary="Rechazar taller")
def rechazar_taller(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE usuarios SET estado = 'rechazado' WHERE id = %s AND rol = 'taller'", (usuario_id,))
        conn.commit()
        return {"mensaje": "Taller rechazado."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Activar usuario (admin desbloquea una cuenta restringida) ────────────────
@router.put("/{usuario_id}/activar", summary="Activar usuario")
def activar_usuario(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE usuarios SET estado = 'activo' WHERE id = %s", (usuario_id,))
        conn.commit()
        return {"mensaje": "Usuario activado."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Restringir usuario: bloquea el acceso sin eliminar la cuenta ──────────────
@router.put("/{usuario_id}/restringir", summary="Restringir usuario")
def restringir_usuario(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE usuarios SET estado = 'pendiente' WHERE id = %s", (usuario_id,))
        conn.commit()
        return {"mensaje": "Usuario restringido."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Eliminar usuario permanentemente ─────────────────────────────────────────
# El superadmin nunca puede eliminarse desde la interfaz, solo desde la terminal.
# Para eliminarlo se debe primero asignar otro superadmin desde la BD.
@router.delete("/{usuario_id}/eliminar", summary="Eliminar usuario")
def eliminar_usuario(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT rol FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cur.fetchone()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

        if usuario["rol"] == "superadmin":
            raise HTTPException(
                status_code=403,
                detail="El superadmin no puede eliminarse desde la interfaz. Debe gestionarse directamente desde la terminal.",
            )

        cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
        return {"mensaje": "Usuario eliminado."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Verificar código de registro: confirma el correo y crea la cuenta ─────────
class VerificarCodigoRequest(BaseModel):
    email: EmailStr
    codigo: str

@router.post("/verificar-codigo", summary="Verificar código de registro")
def verificar_codigo(data: VerificarCodigoRequest):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id, datos_registro FROM codigos_verificacion
            WHERE email = %s AND codigo = %s AND usado = FALSE AND expira_en > NOW()
            ORDER BY creado_en DESC LIMIT 1
            """,
            (data.email, data.codigo),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Código incorrecto o expirado.")

        datos = row["datos_registro"]
        if not datos:
            raise HTTPException(status_code=400, detail="No se encontraron datos de registro.")

        estado_inicial = "pendiente" if datos.get("rol") == "taller" else "activo"

        cur.execute(
            """
            INSERT INTO usuarios (nombre, email, contrasena, telefono, rol, estado)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, nombre, email, telefono, rol
            """,
            (
                datos["nombre"],
                datos["email"],
                datos["contrasena"],
                datos.get("telefono"),
                datos.get("rol", "usuario"),
                estado_inicial,
            ),
        )
        nuevo = dict(cur.fetchone())

        if datos.get("rol") == "taller" and datos.get("nombre_taller") and datos.get("direccion_taller"):
            cur.execute(
                """
                INSERT INTO talleres (
                    nombre, direccion, admin_id, latitud, longitud, horario_apertura, horario_cierre
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    datos["nombre_taller"],
                    datos["direccion_taller"],
                    nuevo["id"],
                    datos.get("latitud"),
                    datos.get("longitud"),
                    datos.get("horario_apertura", "08:00"),
                    datos.get("horario_cierre", "18:00"),
                ),
            )

        cur.execute("UPDATE codigos_verificacion SET usado = TRUE WHERE id = %s", (row["id"],))
        conn.commit()

        return {"mensaje": "Cuenta verificada correctamente. Ya puedes iniciar sesión."}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al verificar: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.get("/taller/{usuario_id}/horario", summary="Consultar horario de trabajo del taller")
def obtener_horario_taller(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id, nombre, horario_apertura, horario_cierre
            FROM talleres
            WHERE admin_id = %s
            """,
            (usuario_id,),
        )
        taller = cur.fetchone()
        if not taller:
            raise HTTPException(status_code=404, detail="Taller no encontrado.")
        return dict(taller)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar horario: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.put("/taller/{usuario_id}/horario", summary="Actualizar horario de trabajo del taller")
def actualizar_horario_taller(usuario_id: int, data: TallerHorario):
    _validar_rango_horario(data.horario_apertura, data.horario_cierre)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            UPDATE talleres
               SET horario_apertura = %s,
                   horario_cierre = %s
             WHERE admin_id = %s
             RETURNING id, nombre, horario_apertura, horario_cierre
            """,
            (data.horario_apertura, data.horario_cierre, usuario_id),
        )
        taller = cur.fetchone()
        if not taller:
            raise HTTPException(status_code=404, detail="Taller no encontrado.")
        conn.commit()
        return {"mensaje": "Horario actualizado correctamente.", "taller": dict(taller)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar horario: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Recuperar contraseña: envía código temporal al correo ────────────────────
class RecuperarPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/recuperar-password", summary="Enviar código de recuperación de contraseña")
def recuperar_password(data: RecuperarPasswordRequest):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id, nombre FROM usuarios WHERE email = %s AND estado = 'activo'", (data.email,))
        usuario = cur.fetchone()
        if not usuario:
            raise HTTPException(status_code=404, detail="No existe una cuenta activa con ese correo.")

        codigo = generar_codigo()
        cur.execute(
            """
            INSERT INTO codigos_verificacion (email, codigo, datos_registro)
            VALUES (%s, %s, %s)
            """,
            (data.email, codigo, json.dumps({"tipo": "recuperacion"})),
        )
        conn.commit()
        enviar_correo_recuperacion(data.email, usuario["nombre"], codigo)
        return {"mensaje": "Te enviamos un código a tu correo para restablecer tu contraseña."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al enviar código: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Resetear contraseña: valida código y actualiza la contraseña ──────────────
class ResetearPasswordRequest(BaseModel):
    email: EmailStr
    codigo: str
    nueva_password: str

@router.post("/resetear-password", summary="Restablecer contraseña con código de verificación")
def resetear_password(data: ResetearPasswordRequest):
    if len(data.nueva_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id FROM codigos_verificacion
            WHERE email = %s AND codigo = %s AND usado = FALSE AND expira_en > NOW()
            ORDER BY creado_en DESC LIMIT 1
            """,
            (data.email, data.codigo),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Código incorrecto o expirado.")

        cur.execute(
            "UPDATE usuarios SET contrasena = %s WHERE email = %s",
            (_hash_password(data.nueva_password), data.email),
        )
        cur.execute("UPDATE codigos_verificacion SET usado = TRUE WHERE id = %s", (row["id"],))
        conn.commit()
        return {"mensaje": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al restablecer contraseña: {str(e)}")
    finally:
        cur.close()
        conn.close()


# ── Obtener perfil de un usuario por ID ──────────────────────────────────────
@router.get("/{usuario_id}", summary="Obtener datos de un usuario")
def get_usuario(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT id, nombre, email, telefono, mfa_habilitado, mfa_verificado "
            "FROM usuarios WHERE id = %s",
            (usuario_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener usuario: {str(e)}")
    finally:
        cur.close()
        conn.close()
