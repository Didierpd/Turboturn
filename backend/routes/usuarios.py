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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import psycopg2.extras
import hashlib

from database import get_connection

router = APIRouter()


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class UsuarioRegistro(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    telefono: Optional[str] = None

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """SHA-256 simple. Si ya usas bcrypt, reemplaza aquí."""
    return hashlib.sha256(password.encode()).hexdigest()


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post("/registro", summary="Registrar nuevo usuario")
def registro(data: UsuarioRegistro):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verificar email duplicado
        cur.execute("SELECT id FROM usuarios WHERE email = %s", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El email ya está registrado.")

        hashed = _hash_password(data.password)
        cur.execute(
            """
            INSERT INTO usuarios (nombre, email, contrasena, telefono)
            VALUES (%s, %s, %s, %s)
            RETURNING id, nombre, email, telefono
            """,
            (data.nombre, data.email, hashed, data.telefono),
        )
        conn.commit()
        nuevo = dict(cur.fetchone())
        return {"mensaje": "Usuario registrado correctamente.", "usuario": nuevo}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar usuario: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.post("/login", summary="Iniciar sesión (fase 1 de 2 si MFA está activo)")
def login(data: UsuarioLogin):
    """
    Fase 1 del login.

    Respuestas posibles:
      - MFA desactivado → devuelve datos del usuario (sesión completa).
      - MFA activado    → devuelve { mfa_requerido: true, usuario_id: X }
                          El frontend debe pedir el código al usuario
                          y llamar a POST /api/mfa/validar.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        hashed = _hash_password(data.password)
        cur.execute(
            """
            SELECT id, nombre, email, telefono, rol, mfa_habilitado
            FROM usuarios
            WHERE email = %s AND contrasena = %s
            """,
            (data.email, hashed),
        )
        usuario = cur.fetchone()

        if not usuario:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas.")

        usuario = dict(usuario)

        # ── Si el usuario tiene MFA activo, detener aquí ──
        if usuario.get("mfa_habilitado"):
            return {
                "mfa_requerido": True,
                "usuario_id": usuario["id"],
                "mensaje": "Ingresa el código de Google Authenticator para continuar.",
            }

        # ── Sin MFA: login completo ──
        usuario.pop("mfa_habilitado", None)
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


@router.get("/todos", summary="Listar todos los usuarios")
def todos_usuarios():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id, nombre, email, rol, estado, telefono FROM usuarios ORDER BY id")
        return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        cur.close()
        conn.close()


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