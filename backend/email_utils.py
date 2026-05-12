import smtplib
import random
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL_ORIGEN = os.getenv("EMAIL_ORIGEN")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def generar_codigo() -> str:
    return str(random.randint(100000, 999999))


def enviar_correo_verificacion(email_destino: str, nombre: str, codigo: str):
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = "Código de verificación - TurboTurn"
    mensaje["From"] = EMAIL_ORIGEN
    mensaje["To"] = email_destino

    cuerpo_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f7fb;padding:30px;">
      <div style="max-width:500px;margin:auto;background:white;border-radius:16px;padding:30px;box-shadow:0 10px 25px rgba(0,0,0,0.08);">
        <h2 style="color:#0f172a;">Bienvenido a TurboTurn, {nombre}</h2>
        <p style="color:#475569;">Usa este código para verificar tu correo:</p>
        <div style="font-size:2.5rem;font-weight:bold;letter-spacing:10px;color:#1d4ed8;text-align:center;margin:20px 0;padding:20px;background:#eff6ff;border-radius:10px;">
          {codigo}
        </div>
        <p style="color:#94a3b8;font-size:0.85rem;">Este código expira en 15 minutos. Si no te registraste, ignora este correo.</p>
      </div>
    </body></html>
    """

    mensaje.attach(MIMEText(cuerpo_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(EMAIL_ORIGEN, EMAIL_PASSWORD)
        servidor.sendmail(EMAIL_ORIGEN, email_destino, mensaje.as_string())
