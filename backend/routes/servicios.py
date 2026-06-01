from fastapi import APIRouter, HTTPException
import psycopg2.extras
from database import get_connection
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


def _get_taller_id(cur, usuario_id: int):
    cur.execute("SELECT id FROM talleres WHERE admin_id = %s", (usuario_id,))
    taller = cur.fetchone()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado para este usuario.")
    return taller["id"]


@router.get("/taller-usuario/{usuario_id}", summary="Obtener servicios del taller por usuario taller")
def get_servicios_taller_usuario(usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        taller_id = _get_taller_id(cur, usuario_id)
        cur.execute(
            """
            SELECT id, taller_id, nombre, descripcion, precio, tiempo_estimado
            FROM servicios
            WHERE taller_id = %s
            ORDER BY nombre
            """,
            (taller_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener servicios del taller")
    finally:
        cur.close()
        conn.close()


@router.delete("/{servicio_id}/taller-usuario/{usuario_id}", summary="Eliminar servicio de un taller")
def delete_servicio_taller(servicio_id: int, usuario_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        taller_id = _get_taller_id(cur, usuario_id)
        cur.execute(
            "SELECT id FROM servicios WHERE id = %s AND taller_id = %s",
            (servicio_id, taller_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Servicio no encontrado")

        cur.execute("SELECT id FROM historial_servicios WHERE servicio_id = %s LIMIT 1", (servicio_id,))
        if cur.fetchone():
            raise HTTPException(
                status_code=400,
                detail="No puedes eliminar este servicio porque ya aparece en historiales de clientes.",
            )

        cur.execute("DELETE FROM servicios WHERE id = %s RETURNING id", (servicio_id,))
        conn.commit()
        return {"mensaje": "Servicio eliminado correctamente."}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Error al eliminar servicio")
    finally:
        cur.close()
        conn.close()


@router.get("/taller/{taller_id}", summary="Obtener servicios de un taller")
def get_servicios_taller(taller_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id, taller_id, nombre, descripcion, precio, tiempo_estimado
            FROM servicios
            WHERE taller_id = %s
            ORDER BY nombre
            """,
            (taller_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener servicios del taller")
    finally:
        cur.close()
        conn.close()


@router.get("/", summary="Obtener todos los servicios disponibles")
def get_servicios():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id, taller_id, nombre, descripcion, precio, tiempo_estimado
            FROM servicios
            ORDER BY nombre
            """
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        raise HTTPException(status_code=500, detail="Error al obtener servicios")
    finally:
        cur.close()
        conn.close()

class ServicioData(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    tiempo_estimado: Optional[str] = None
    usuario_id: int


def _validar_servicio(data: ServicioData):
    nombre = data.nombre.strip()
    if len(nombre) < 2:
        raise HTTPException(status_code=400, detail="El nombre del servicio debe tener al menos 2 caracteres.")
    if data.precio < 0:
        raise HTTPException(status_code=400, detail="El precio no puede ser negativo.")
    return {
        "nombre": nombre,
        "descripcion": data.descripcion.strip() if data.descripcion else None,
        "precio": data.precio,
        "tiempo_estimado": data.tiempo_estimado.strip() if data.tiempo_estimado else None,
    }


@router.post("/", summary="Crear servicio para un taller")
def create_servicio(data: ServicioData):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        servicio = _validar_servicio(data)
        taller_id = _get_taller_id(cur, data.usuario_id)
        cur.execute(
            """INSERT INTO servicios (taller_id, nombre, descripcion, precio, tiempo_estimado)
               VALUES (%s, %s, %s, %s, %s) RETURNING *""",
            (taller_id, servicio["nombre"], servicio["descripcion"], servicio["precio"], servicio["tiempo_estimado"]),
        )
        conn.commit()
        return dict(cur.fetchone())
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear servicio: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.put("/{servicio_id}/taller-usuario/{usuario_id}", summary="Actualizar servicio de un taller")
def update_servicio_taller(servicio_id: int, usuario_id: int, data: ServicioData):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        servicio = _validar_servicio(data)
        taller_id = _get_taller_id(cur, usuario_id)
        cur.execute(
            """
            UPDATE servicios
            SET nombre = %s,
                descripcion = %s,
                precio = %s,
                tiempo_estimado = %s
            WHERE id = %s AND taller_id = %s
            RETURNING id, taller_id, nombre, descripcion, precio, tiempo_estimado
            """,
            (
                servicio["nombre"],
                servicio["descripcion"],
                servicio["precio"],
                servicio["tiempo_estimado"],
                servicio_id,
                taller_id,
            ),
        )
        actualizado = cur.fetchone()
        if not actualizado:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")

        conn.commit()
        return dict(actualizado)
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar servicio: {str(e)}")
    finally:
        cur.close()
        conn.close()
