from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import psycopg2.extras
from database import get_connection
from email_utils import generar_token_verificacion, verificar_token, enviar_correo_verificacion

router = APIRouter()


class LoginData(BaseModel):
    email: str
    contrasena: str


class RegistroData(BaseModel):
    nombre: str
    email: str
    contrasena: str
    rol: str
    telefono: str = None
    nombre_taller: str = None
    direccion_taller: str = None


@router.post("/registro", summary="Registrar usuario o taller")
def registro(data: RegistroData):
    if data.rol not in ("usuario", "taller"):
        raise HTTPException(status_code=400, detail="Rol no válido")

    if data.rol == "taller":
        if not data.nombre_taller or not data.direccion_taller:
            raise HTTPException(status_code=400, detail="El taller debe tener nombre y dirección")

    estado = "pendiente" if data.rol == "taller" else "activo"

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id FROM usuarios WHERE email=%s", (data.email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="El correo ya está registrado")

        cur.execute(
            """INSERT INTO usuarios (nombre, email, contrasena, rol, estado, telefono, email_verificado)
               VALUES (%s, %s, %s, %s, %s, %s, FALSE) RETURNING id, nombre, email, rol, estado""",
            (data.nombre, data.email, data.contrasena, data.rol, estado, data.telefono),
        )
        nuevo = cur.fetchone()

        if data.rol == "taller":
            cur.execute(
                "INSERT INTO talleres (nombre, direccion, telefono, admin_id) VALUES (%s, %s, %s, %s)",
                (data.nombre_taller, data.direccion_taller, data.telefono, nuevo["id"]),
            )

        conn.commit()

        token = generar_token_verificacion(data.email)
        try:
            enviar_correo_verificacion(data.email, data.nombre, token)
        except Exception:
            pass

        return dict(nuevo)
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error del servidor")
    finally:
        cur.close()
        conn.close()


@router.get("/verificar", summary="Verificar correo electrónico", response_class=HTMLResponse)
def verificar_email(token: str):
    try:
        email = verificar_token(token)
    except Exception:
        return HTMLResponse("""
        <html><body style="font-family:Arial;text-align:center;padding:60px;background:#f4f7fb;">
          <div style="max-width:400px;margin:auto;background:white;padding:30px;border-radius:16px;box-shadow:0 10px 25px rgba(0,0,0,0.08);">
            <h2 style="color:#dc2626;">Enlace inválido o expirado</h2>
            <p style="color:#475569;">El enlace de verificación no es válido o ya expiró. Regístrate nuevamente.</p>
            <a href="/views/registro.html" style="display:inline-block;margin-top:20px;padding:10px 20px;background:#1d4ed8;color:white;border-radius:8px;text-decoration:none;">Registrarse</a>
          </div>
        </body></html>
        """, status_code=400)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE usuarios SET email_verificado=TRUE WHERE email=%s RETURNING id",
            (email,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return HTMLResponse("""
    <html><body style="font-family:Arial;text-align:center;padding:60px;background:#f4f7fb;">
      <div style="max-width:400px;margin:auto;background:white;padding:30px;border-radius:16px;box-shadow:0 10px 25px rgba(0,0,0,0.08);">
        <h2 style="color:#16a34a;">¡Correo verificado!</h2>
        <p style="color:#475569;">Tu cuenta ha sido activada correctamente.</p>
        <a href="/views/login.html" style="display:inline-block;margin-top:20px;padding:10px 20px;background:#1d4ed8;color:white;border-radius:8px;text-decoration:none;">Iniciar sesión</a>
      </div>
    </body></html>
    """)


@router.get("/talleres-pendientes", summary="Talleres pendientes de aprobación")
def talleres_pendientes():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT id, nombre, email, telefono, creado_en FROM usuarios WHERE rol='taller' AND estado='pendiente' ORDER BY creado_en DESC"
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


@router.get("/todos", summary="Todos los usuarios")
def todos_usuarios():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT id, nombre, email, rol, estado, telefono, creado_en FROM usuarios ORDER BY creado_en DESC"
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


@router.put("/{usuario_id}/aprobar", summary="Aprobar taller")
def aprobar_taller(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE usuarios SET estado='activo' WHERE id=%s AND rol='taller' RETURNING id",
            (usuario_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Taller no encontrado")
        conn.commit()
        return {"mensaje": "Taller aprobado"}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error del servidor")
    finally:
        cur.close()
        conn.close()


@router.put("/{usuario_id}/rechazar", summary="Rechazar taller")
def rechazar_taller(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE usuarios SET estado='rechazado' WHERE id=%s AND rol='taller' RETURNING id",
            (usuario_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Taller no encontrado")
        conn.commit()
        return {"mensaje": "Taller rechazado"}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error del servidor")
    finally:
        cur.close()
        conn.close()


@router.post("/login", summary="Iniciar sesión")
def login(data: LoginData):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT * FROM usuarios WHERE email=%s AND contrasena=%s",
            (data.email, data.contrasena),
        )
        usuario = cur.fetchone()
        if not usuario:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        if not usuario["email_verificado"]:
            raise HTTPException(status_code=403, detail="Debes verificar tu correo antes de ingresar. Revisa tu bandeja de entrada.")
        if usuario["estado"] == "pendiente":
            raise HTTPException(status_code=403, detail="Tu cuenta está pendiente de aprobación por el administrador")
        if usuario["estado"] == "rechazado":
            raise HTTPException(status_code=403, detail="Tu cuenta fue rechazada")
        return dict(usuario)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error del servidor")
    finally:
        cur.close()
        conn.close()
