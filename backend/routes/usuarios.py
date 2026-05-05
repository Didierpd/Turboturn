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
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "UPDATE usuarios SET estado='activo' WHERE id=%s AND rol='taller' RETURNING id, nombre, telefono",
            (usuario_id,),
        )
        taller_usuario = cur.fetchone()
        if not taller_usuario:
            raise HTTPException(status_code=404, detail="Taller no encontrado")

        cur.execute("SELECT id FROM talleres WHERE admin_id=%s", (usuario_id,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO talleres (nombre, direccion, telefono, admin_id) VALUES (%s, %s, %s, %s)",
                (taller_usuario["nombre"], "Por definir", taller_usuario["telefono"], usuario_id),
            )

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
