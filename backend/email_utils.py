import smtplib
import jwt
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

EMAIL_ORIGEN = os.getenv("EMAIL_ORIGEN")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
JWT_SECRET = os.getenv("JWT_SECRET", "turboturn_secret_key_2026")
BASE_URL = "http://localhost:8000"


def generar_token_verificacion(email: str) -> str:
    payload = {
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "tipo": "verificacion"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verificar_token(token: str) -> str:
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    if payload.get("tipo") != "verificacion":
        raise ValueError("Token inválido")
    return payload["email"]


def enviar_correo_verificacion(email_destino: str, nombre: str, token: str):
    link = f"{BASE_URL}/api/usuarios/verificar?token={token}"

    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = "Verifica tu cuenta en TurboTurn"
    mensaje["From"] = EMAIL_ORIGEN
    mensaje["To"] = email_destino

    cuerpo_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f7fb;padding:30px;">
      <div style="max-width:500px;margin:auto;background:white;border-radius:16px;padding:30px;box-shadow:0 10px 25px rgba(0,0,0,0.08);">
        <h2 style="color:#0f172a;">Bienvenido a TurboTurn, {nombre}</h2>
        <p style="color:#475569;">Haz clic en el botón para verificar tu correo y activar tu cuenta.</p>
        <a href="{link}" style="display:inline-block;margin:20px 0;padding:12px 24px;background:#1d4ed8;color:white;border-radius:10px;text-decoration:none;font-weight:bold;">
          Verificar mi cuenta
        </a>
        <p style="color:#94a3b8;font-size:0.85rem;">Este enlace expira en 24 horas. Si no te registraste, ignora este correo.</p>
      </div>
    </body></html>
    """

    mensaje.attach(MIMEText(cuerpo_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(EMAIL_ORIGEN, EMAIL_PASSWORD)
        servidor.sendmail(EMAIL_ORIGEN, email_destino, mensaje.as_string())
