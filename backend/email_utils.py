import smtplib
import random
import os
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL_ORIGEN = os.getenv("EMAIL_ORIGEN")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def _enviar_html(email_destino: str, asunto: str, cuerpo_html: str):
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = asunto
    mensaje["From"] = EMAIL_ORIGEN
    mensaje["To"] = email_destino
    mensaje.attach(MIMEText(cuerpo_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(EMAIL_ORIGEN, EMAIL_PASSWORD)
        servidor.sendmail(EMAIL_ORIGEN, email_destino, mensaje.as_string())


def generar_codigo() -> str:
    return str(random.randint(100000, 999999))


def enviar_correo_verificacion(email_destino: str, nombre: str, codigo: str):
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

    _enviar_html(email_destino, "Código de verificación - TurboTurn", cuerpo_html)


def _bloque_cita(taller: str, fecha_hora: str, vehiculo: str, extra: str = "") -> str:
    return f"""
      <div style="background:#f8fafc;border-left:4px solid #0f766e;border-radius:10px;padding:16px;margin:18px 0;color:#334155;">
        <p style="margin:0 0 8px;"><strong>Taller:</strong> {escape(taller)}</p>
        <p style="margin:0 0 8px;"><strong>Fecha:</strong> {escape(fecha_hora)}</p>
        <p style="margin:0 0 8px;"><strong>Vehículo:</strong> {escape(vehiculo)}</p>
        {extra}
      </div>
    """


def enviar_correo_cita_creada(email_destino: str, cliente: str, taller: str, fecha_hora: str, vehiculo: str):
    cuerpo_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f7fb;padding:30px;">
      <div style="max-width:560px;margin:auto;background:white;border-radius:16px;padding:30px;box-shadow:0 10px 25px rgba(0,0,0,0.08);">
        <h2 style="color:#0f172a;">Cita reservada, {escape(cliente)}</h2>
        <p style="color:#475569;">Recibimos tu solicitud. El taller revisará la agenda y confirmará tu cita.</p>
        {_bloque_cita(taller, fecha_hora, vehiculo)}
      </div>
    </body></html>
    """
    _enviar_html(email_destino, "Cita reservada - TurboTurn", cuerpo_html)


def enviar_correo_cita_confirmada(
    email_destino: str,
    cliente: str,
    taller: str,
    fecha_hora: str,
    vehiculo: str,
    mecanico: str,
):
    extra = f'<p style="margin:0;"><strong>Mecánico asignado:</strong> {escape(mecanico)}</p>'
    cuerpo_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f7fb;padding:30px;">
      <div style="max-width:560px;margin:auto;background:white;border-radius:16px;padding:30px;box-shadow:0 10px 25px rgba(0,0,0,0.08);">
        <h2 style="color:#0f172a;">Tu cita fue confirmada</h2>
        <p style="color:#475569;">Hola, {escape(cliente)}. El taller confirmó tu cita y asignó un mecánico.</p>
        {_bloque_cita(taller, fecha_hora, vehiculo, extra)}
      </div>
    </body></html>
    """
    _enviar_html(email_destino, "Cita confirmada - TurboTurn", cuerpo_html)


def enviar_correo_mecanico_asignado(
    email_destino: str,
    mecanico: str,
    cliente: str,
    taller: str,
    fecha_hora: str,
    vehiculo: str,
):
    extra = f'<p style="margin:0;"><strong>Cliente:</strong> {escape(cliente)}</p>'
    cuerpo_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f7fb;padding:30px;">
      <div style="max-width:560px;margin:auto;background:white;border-radius:16px;padding:30px;box-shadow:0 10px 25px rgba(0,0,0,0.08);">
        <h2 style="color:#0f172a;">Nuevo trabajo asignado</h2>
        <p style="color:#475569;">Hola, {escape(mecanico)}. Se te asignó una cita en TurboTurn.</p>
        {_bloque_cita(taller, fecha_hora, vehiculo, extra)}
      </div>
    </body></html>
    """
    _enviar_html(email_destino, "Trabajo asignado - TurboTurn", cuerpo_html)


def enviar_correo_trabajo_finalizado(
    email_destino: str,
    cliente: str,
    taller: str,
    fecha_hora: str,
    vehiculo: str,
    servicio: str,
    costo_final: float,
    observaciones: str | None = None,
):
    extra = (
        f'<p style="margin:0 0 8px;"><strong>Servicio:</strong> {escape(servicio)}</p>'
        f'<p style="margin:0 0 8px;"><strong>Costo final:</strong> ${float(costo_final):,.0f}</p>'
    )
    if observaciones:
        extra += f'<p style="margin:0;"><strong>Observaciones:</strong> {escape(observaciones)}</p>'

    cuerpo_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f7fb;padding:30px;">
      <div style="max-width:560px;margin:auto;background:white;border-radius:16px;padding:30px;box-shadow:0 10px 25px rgba(0,0,0,0.08);">
        <h2 style="color:#0f172a;">Trabajo finalizado</h2>
        <p style="color:#475569;">Hola, {escape(cliente)}. El taller marcó tu servicio como terminado.</p>
        {_bloque_cita(taller, fecha_hora, vehiculo, extra)}
      </div>
    </body></html>
    """
    _enviar_html(email_destino, "Trabajo finalizado - TurboTurn", cuerpo_html)


def enviar_correo_cancelacion_cita(
    email_destino: str,
    cliente: str,
    taller: str,
    fecha_hora: str,
    vehiculo: str,
    motivo: str,
):
    # Notifica al cliente cuando el taller cancela una cita o servicio agendado.
    cliente = escape(cliente)
    taller = escape(taller)
    fecha_hora = escape(fecha_hora)
    vehiculo = escape(vehiculo)
    motivo = escape(motivo)

    cuerpo_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f7fb;padding:30px;">
      <div style="max-width:560px;margin:auto;background:white;border-radius:16px;padding:30px;box-shadow:0 10px 25px rgba(0,0,0,0.08);">
        <h2 style="color:#0f172a;">Hola, {cliente}</h2>
        <p style="color:#475569;">Tu cita en <strong>{taller}</strong> fue cancelada.</p>
        <div style="background:#fef2f2;border-left:4px solid #dc2626;border-radius:10px;padding:16px;margin:18px 0;color:#7f1d1d;">
          <p style="margin:0 0 8px;"><strong>Fecha:</strong> {fecha_hora}</p>
          <p style="margin:0 0 8px;"><strong>Vehículo:</strong> {vehiculo}</p>
          <p style="margin:0;"><strong>Motivo:</strong> {motivo}</p>
        </div>
        <p style="color:#64748b;">Puedes ingresar a TurboTurn para programar una nueva cita si lo necesitas.</p>
      </div>
    </body></html>
    """

    _enviar_html(email_destino, "Tu cita fue cancelada - TurboTurn", cuerpo_html)
