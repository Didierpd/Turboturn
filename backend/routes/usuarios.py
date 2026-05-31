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

from database import get_connection
from email_utils import generar_codigo, enviar_correo_verificacion

router = APIRouter()


class UsuarioRegistro(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    telefono: Optional[str] = None
    rol: Optional[str] = "usuario"
    nombre_taller: Optional[str] = None
    direccion_taller: Optional[str] = None

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


@router.post("/registro", summary="Registrar nuevo usuario")
def registro(data: UsuarioRegistro):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id FROM usuarios WHERE email = %s", (data.email,))
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
        }
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


@router.post("/login", summary="Iniciar sesión (fase 1 de 2 si MFA está activo)")
def login(data: UsuarioLogin):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        hashed = _hash_password(data.password)
        cur.execute(
            "SELECT id, nombre, email, telefono, rol, mfa_habilitado, contrasena FROM usuarios WHERE email = %s",
            (data.email,),
        )
        usuario = cur.fetchone()

        if not usuario:
            # Evita una segunda petición desde el frontend cuando quien inicia sesión es un mecánico.
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
                raise HTTPException(status_code=404, detail="Correo o contraseña incorrectos.")
            if not mecanico["activo"]:
                raise HTTPException(status_code=403, detail="El mecánico está inactivo.")
            if mecanico["contrasena"] != hashed:
                raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")

            mecanico = dict(mecanico)
            mecanico.pop("contrasena", None)
            mecanico["rol"] = "mecanico"
            return {
                "mfa_requerido": False,
                "mensaje": "Login exitoso.",
                "usuario": mecanico,
            }

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
                INSERT INTO talleres (nombre, direccion, admin_id)
                VALUES (%s, %s, %s)
                """,
                (datos["nombre_taller"], datos["direccion_taller"], nuevo["id"]),
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
