from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2.extras
from database import get_connection

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


@router.post("/registro", summary="Registrar usuario o taller")
def registro(data: RegistroData):
    if data.rol not in ("usuario", "taller"):
        raise HTTPException(status_code=400, detail="Rol no válido")

    estado = "pendiente" if data.rol == "taller" else "activo"

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT id FROM usuarios WHERE email=%s",
            (data.email,),
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="El correo ya está registrado")

        cur.execute(
            """INSERT INTO usuarios (nombre, email, contrasena, rol, estado, telefono)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, nombre, email, rol, estado""",
            (data.nombre, data.email, data.contrasena, data.rol, estado, data.telefono),
        )
        nuevo = cur.fetchone()
        conn.commit()
        return dict(nuevo)
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
