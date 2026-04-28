from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2.extras
from database import get_connection

router = APIRouter()


class LoginData(BaseModel):
    email: str
    contrasena: str


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
        return dict(usuario)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error del servidor")
    finally:
        cur.close()
        conn.close()
