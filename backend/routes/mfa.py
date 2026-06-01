"""
routes/mfa.py
Endpoints para gestión de MFA con Google Authenticator (TOTP).

Flujo completo:
  1. POST /api/mfa/configurar   → genera secret y devuelve QR en base64
  2. POST /api/mfa/verificar    → valida el primer código y activa MFA
  3. POST /api/mfa/validar      → valida código TOTP en cada login
  4. POST /api/mfa/deshabilitar → desactiva MFA del usuario
  5. GET  /api/mfa/estado/{id}  → consulta si el usuario tiene MFA activo
"""

import io
import base64
import pyotp
import qrcode
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2.extras

from database import get_connection

router = APIRouter()


class MFAConfigurarRequest(BaseModel):
    usuario_id: int
    cuenta_tipo: str = "usuario"

class MFAVerificarRequest(BaseModel):
    usuario_id: int
    codigo: str          # Código de 6 dígitos del Authenticator
    cuenta_tipo: str = "usuario"

class MFAValidarRequest(BaseModel):
    usuario_id: int
    codigo: str
    cuenta_tipo: str = "usuario"

class MFADeshabilitarRequest(BaseModel):
    usuario_id: int
    codigo: str          # Se exige un código válido para deshabilitar
    cuenta_tipo: str = "usuario"


def _normalizar_tipo(cuenta_tipo: str) -> str:
    if cuenta_tipo not in ("usuario", "mecanico"):
        raise HTTPException(status_code=400, detail="Tipo de cuenta no válido.")
    return cuenta_tipo


def _get_cuenta(cur, usuario_id: int, cuenta_tipo: str) -> dict:
    """Devuelve la cuenta de usuario o mecánico, o lanza 404."""
    cuenta_tipo = _normalizar_tipo(cuenta_tipo)
    if cuenta_tipo == "mecanico":
        cur.execute(
            """
            SELECT m.id, m.taller_id, m.nombre, m.email, m.telefono, m.especialidad,
                   m.activo, m.mfa_secret, m.mfa_habilitado, m.mfa_verificado,
                   t.nombre AS taller
            FROM mecanicos m
            JOIN talleres t ON m.taller_id = t.id
            WHERE m.id = %s
            """,
            (usuario_id,),
        )
    else:
        cur.execute(
            "SELECT id, nombre, email, telefono, rol, mfa_secret, mfa_habilitado, mfa_verificado "
            "FROM usuarios WHERE id = %s",
            (usuario_id,),
        )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    cuenta = dict(row)
    cuenta["cuenta_tipo"] = cuenta_tipo
    return cuenta


def _tabla_mfa(cuenta_tipo: str) -> str:
    return "mecanicos" if _normalizar_tipo(cuenta_tipo) == "mecanico" else "usuarios"


def _respuesta_cuenta(cur, usuario_id: int, cuenta_tipo: str) -> dict:
    cuenta_tipo = _normalizar_tipo(cuenta_tipo)
    if cuenta_tipo == "mecanico":
        cur.execute(
            """
            SELECT m.id, m.taller_id, m.nombre, m.email, m.telefono, m.especialidad,
                   m.activo, m.mfa_habilitado, t.nombre AS taller
            FROM mecanicos m
            JOIN talleres t ON m.taller_id = t.id
            WHERE m.id = %s
            """,
            (usuario_id,),
        )
        mecanico = dict(cur.fetchone())
        mecanico["rol"] = "mecanico"
        return mecanico

    cur.execute(
        "SELECT id, nombre, email, telefono, rol, mfa_habilitado FROM usuarios WHERE id = %s",
        (usuario_id,),
    )
    return dict(cur.fetchone())


def _generar_qr_base64(secret: str, email: str) -> str:
    """Genera imagen QR como string base64 PNG."""
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name="TurboTurn"
    )
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

@router.post("/configurar", summary="Genera secret TOTP y devuelve el QR para escanear")
def configurar_mfa(data: MFAConfigurarRequest):
    """
    Genera (o regenera) el secret TOTP del usuario y devuelve:
      - qr_base64: imagen PNG en base64 lista para mostrar en el frontend
      - secret:    clave manual por si el usuario no puede escanear el QR
    El MFA queda pendiente de verificación hasta que el usuario confirme
    con un código válido en /verificar.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cuenta = _get_cuenta(cur, data.usuario_id, data.cuenta_tipo)
        tabla = _tabla_mfa(data.cuenta_tipo)

        # Genera un nuevo secret (32 chars, base32)
        secret = pyotp.random_base32()

        cur.execute(
            f"""
            UPDATE {tabla}
               SET mfa_secret     = %s,
                   mfa_habilitado = FALSE,
                   mfa_verificado = FALSE
             WHERE id = %s
            """,
            (secret, data.usuario_id),
        )
        conn.commit()

        qr_base64 = _generar_qr_base64(secret, cuenta["email"])

        return {
            "mensaje": "Escanea el QR con Google Authenticator y luego confirma con un código.",
            "qr_base64": qr_base64,
            "secret": secret,          # para entrada manual
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al configurar MFA: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.post("/verificar", summary="Confirma el primer código TOTP y activa el MFA")
def verificar_mfa(data: MFAVerificarRequest):
    """
    Valida el primer código ingresado por el usuario tras escanear el QR.
    Si es correcto, marca mfa_habilitado = TRUE y mfa_verificado = TRUE.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cuenta = _get_cuenta(cur, data.usuario_id, data.cuenta_tipo)
        tabla = _tabla_mfa(data.cuenta_tipo)

        if not cuenta["mfa_secret"]:
            raise HTTPException(
                status_code=400,
                detail="Primero debes iniciar la configuración MFA en /configurar"
            )

        totp = pyotp.TOTP(cuenta["mfa_secret"])

        # valid_window=1 acepta el código del intervalo anterior y siguiente (±30 s)
        if not totp.verify(data.codigo, valid_window=1):
            raise HTTPException(status_code=400, detail="Código incorrecto. Intenta de nuevo.")

        cur.execute(
            f"""
            UPDATE {tabla}
               SET mfa_habilitado = TRUE,
                   mfa_verificado = TRUE
             WHERE id = %s
            """,
            (data.usuario_id,),
        )
        conn.commit()

        return {"mensaje": "MFA activado correctamente. Desde ahora se requerirá en cada inicio de sesión."}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al verificar MFA: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.post("/validar", summary="Valida el código TOTP durante el login")
def validar_mfa(data: MFAValidarRequest):
    """
    Llamado desde el frontend después del login con email/contraseña.
    Devuelve 200 si el código es válido, 401 si no.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cuenta = _get_cuenta(cur, data.usuario_id, data.cuenta_tipo)

        if not cuenta["mfa_habilitado"] or not cuenta["mfa_secret"]:
            raise HTTPException(status_code=400, detail="Este usuario no tiene MFA habilitado.")

        totp = pyotp.TOTP(cuenta["mfa_secret"])
        if not totp.verify(data.codigo, valid_window=1):
            raise HTTPException(status_code=401, detail="Código MFA incorrecto o expirado.")

        datos_usuario = _respuesta_cuenta(cur, data.usuario_id, data.cuenta_tipo)

        return {"mensaje": "Código MFA válido. Acceso autorizado.", "usuario": datos_usuario}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al validar MFA: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.post("/deshabilitar", summary="Desactiva el MFA del usuario")
def deshabilitar_mfa(data: MFADeshabilitarRequest):
    """
    Requiere un código TOTP válido para confirmar que el usuario tiene
    acceso a su Authenticator antes de deshabilitarlo.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cuenta = _get_cuenta(cur, data.usuario_id, data.cuenta_tipo)
        tabla = _tabla_mfa(data.cuenta_tipo)

        if not cuenta["mfa_habilitado"] or not cuenta["mfa_secret"]:
            raise HTTPException(status_code=400, detail="El usuario no tiene MFA habilitado.")

        totp = pyotp.TOTP(cuenta["mfa_secret"])
        if not totp.verify(data.codigo, valid_window=1):
            raise HTTPException(status_code=401, detail="Código MFA incorrecto. No se puede deshabilitar.")

        cur.execute(
            f"""
            UPDATE {tabla}
               SET mfa_secret     = NULL,
                   mfa_habilitado = FALSE,
                   mfa_verificado = FALSE
             WHERE id = %s
            """,
            (data.usuario_id,),
        )
        conn.commit()

        return {"mensaje": "MFA deshabilitado correctamente."}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al deshabilitar MFA: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.get("/estado/{usuario_id}", summary="Consulta el estado MFA de una cuenta")
def estado_mfa(usuario_id: int, cuenta_tipo: str = "usuario"):
    """Devuelve si el usuario tiene MFA habilitado y verificado."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cuenta = _get_cuenta(cur, usuario_id, cuenta_tipo)
        return {
            "usuario_id": usuario_id,
            "cuenta_tipo": cuenta_tipo,
            "mfa_habilitado": cuenta["mfa_habilitado"],
            "mfa_verificado": cuenta["mfa_verificado"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar estado MFA: {str(e)}")
    finally:
        cur.close()
        conn.close()
