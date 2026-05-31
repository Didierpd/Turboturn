from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

from database import get_connection
from routes import usuarios, vehiculos, citas, servicios, historial, mfa, mecanicos   # ← mfa agregado

app = FastAPI(
    title="TurboTurn API",
    description="Sistema de gestión de turnos para talleres mecánicos",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.on_event("startup")
def warm_database_connection():
    # Abre la conexión a RDS al iniciar para que el primer login no pague esa espera.
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.middleware("http")
async def add_cache_control_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    no_cache_extensions = (".html", ".css", ".js")

    # En desarrollo evitamos que el navegador conserve pantallas, estilos o datos viejos.
    if path.startswith("/api/") or path == "/" or path.endswith(no_cache_extensions):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response

app.include_router(usuarios.router,  prefix="/api/usuarios",  tags=["Usuarios"])
app.include_router(vehiculos.router, prefix="/api/vehiculos", tags=["Vehículos"])
app.include_router(citas.router,     prefix="/api/citas",     tags=["Citas"])
app.include_router(servicios.router, prefix="/api/servicios", tags=["Servicios"])
app.include_router(historial.router, prefix="/api/historial", tags=["Historial"])
app.include_router(mfa.router,       prefix="/api/mfa",       tags=["MFA"])   # ← nuevo
app.include_router(mecanicos.router, prefix="/api/mecanicos", tags=["Mecánicos"])

frontend_path = os.path.join(os.path.dirname(__file__), "../frontend")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(os.path.join(frontend_path, "images", "logo_turbo.png"))


app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
