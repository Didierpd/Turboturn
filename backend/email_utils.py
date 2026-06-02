"""
email_utils.py
Envío de correos HTML y generación/envío de facturas PDF via Gmail SMTP.

Correos de notificación:
  enviar_correo_verificacion()       → código 6 dígitos al registrarse
  enviar_correo_cita_creada()        → confirmación al cliente al reservar
  enviar_correo_cita_confirmada()    → cliente y mecánico al confirmar cita
  enviar_correo_mecanico_asignado()  → notifica al mecánico asignado
  enviar_correo_revision_mecanico()  → al cliente con diagnóstico y costo estimado
  enviar_correo_trabajo_finalizado() → al cliente al cerrar el trabajo
  enviar_correo_cancelacion_cita()   → al cliente si el taller cancela

Factura PDF (ReportLab):
  generar_pdf_factura()  → retorna bytes del PDF
  enviar_factura_pdf()   → envía el PDF como adjunto al correo del cliente

Credenciales en .env: EMAIL_ORIGEN, EMAIL_PASSWORD.
"""

import smtplib
import random
import os
import io
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

load_dotenv()

EMAIL_ORIGEN = os.getenv("EMAIL_ORIGEN")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


# ── Helper privado: envía cualquier correo HTML por Gmail SMTP ────────────────
def _enviar_html(email_destino: str, asunto: str, cuerpo_html: str):
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = asunto
    mensaje["From"] = EMAIL_ORIGEN
    mensaje["To"] = email_destino
    mensaje.attach(MIMEText(cuerpo_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(EMAIL_ORIGEN, EMAIL_PASSWORD)
        servidor.sendmail(EMAIL_ORIGEN, email_destino, mensaje.as_string())


# ── Helper: genera código de verificación de 6 dígitos ───────────────────────
def generar_codigo() -> str:
    return str(random.randint(100000, 999999))


# ── Correo de verificación de registro (envía el código de 6 dígitos) ────────
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


# ── Helper privado: genera el bloque HTML con los datos de la cita ────────────
def _bloque_cita(taller: str, fecha_hora: str, vehiculo: str, extra: str = "") -> str:
    return f"""
      <div style="background:#f8fafc;border-left:4px solid #0f766e;border-radius:10px;padding:16px;margin:18px 0;color:#334155;">
        <p style="margin:0 0 8px;"><strong>Taller:</strong> {escape(taller)}</p>
        <p style="margin:0 0 8px;"><strong>Fecha:</strong> {escape(fecha_hora)}</p>
        <p style="margin:0 0 8px;"><strong>Vehículo:</strong> {escape(vehiculo)}</p>
        {extra}
      </div>
    """


# ── Notifica al cliente que su cita fue recibida (pendiente de confirmación) ──
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


# ── Notifica al cliente que la cita fue confirmada con mecánico asignado ──────
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


# ── Notifica al mecánico que le asignaron una cita ───────────────────────────
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


# ── Notifica al cliente el diagnóstico, reparación sugerida y costo estimado ─
def enviar_correo_revision_mecanico(
    email_destino: str,
    cliente: str,
    taller: str,
    fecha_hora: str,
    vehiculo: str,
    mecanico: str,
    tiempo_estimado: str,
    trabajo_requerido: str,
    costo_estimado: float,
):
    # Este correo se envía después de la revisión, antes de cerrar el servicio.
    extra = (
        f'<p style="margin:0 0 8px;"><strong>Mecánico:</strong> {escape(mecanico)}</p>'
        f'<p style="margin:0 0 8px;"><strong>Trabajo recomendado:</strong> {escape(trabajo_requerido)}</p>'
        f'<p style="margin:0 0 8px;"><strong>Tiempo estimado:</strong> {escape(tiempo_estimado)}</p>'
        f'<p style="margin:0;"><strong>Costo estimado:</strong> ${float(costo_estimado):,.0f}</p>'
    )

    cuerpo_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f7fb;padding:30px;">
      <div style="max-width:560px;margin:auto;background:white;border-radius:16px;padding:30px;box-shadow:0 10px 25px rgba(0,0,0,0.08);">
        <h2 style="color:#0f172a;">Resultado de la revisión</h2>
        <p style="color:#475569;">Hola, {escape(cliente)}. El mecánico revisó tu vehículo y registró el diagnóstico inicial.</p>
        {_bloque_cita(taller, fecha_hora, vehiculo, extra)}
        <p style="color:#64748b;">Este valor es un estimado. El taller confirmará el cierre cuando el servicio quede terminado.</p>
      </div>
    </body></html>
    """
    _enviar_html(email_destino, "Resultado de revisión - TurboTurn", cuerpo_html)


# ── Notifica al cliente que el trabajo fue completado con costo y observaciones ─
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


# ── Notifica al cliente que el taller canceló su cita con el motivo ──────────
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


# ── Genera el PDF de la factura con ReportLab y retorna los bytes ─────────────
def generar_pdf_factura(datos: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elementos = []

    estilo_titulo = ParagraphStyle("titulo", parent=styles["Title"], fontSize=22, textColor=colors.HexColor("#1d4ed8"), spaceAfter=4)
    estilo_subtitulo = ParagraphStyle("subtitulo", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#64748b"), spaceAfter=12)
    estilo_seccion = ParagraphStyle("seccion", parent=styles["Normal"], fontSize=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#0f172a"), spaceBefore=12, spaceAfter=6)
    estilo_normal = ParagraphStyle("normal", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#334155"))
    estilo_total = ParagraphStyle("total", parent=styles["Normal"], fontSize=13, fontName="Helvetica-Bold", textColor=colors.HexColor("#1d4ed8"), alignment=TA_RIGHT, spaceBefore=10)

    elementos.append(Paragraph("TurboTurn", estilo_titulo))
    elementos.append(Paragraph("Gestion de turnos para talleres mecanicos", estilo_subtitulo))
    elementos.append(Spacer(1, 0.3*cm))

    fecha = str(datos.get("fecha_hora", ""))[:10]
    elementos.append(Paragraph("<b>FACTURA DE SERVICIO</b>", estilo_seccion))
    elementos.append(Paragraph(f"Fecha: {fecha}", estilo_normal))
    elementos.append(Spacer(1, 0.4*cm))

    elementos.append(Paragraph("Datos del taller", estilo_seccion))
    taller_data = [
        ["Nombre:", datos.get("taller_nombre", "-")],
        ["Direccion:", datos.get("taller_direccion", "-")],
        ["Telefono:", datos.get("taller_telefono", "-")],
        ["Correo:", datos.get("taller_email", "-")],
    ]
    tabla_taller = Table(taller_data, colWidths=[4*cm, 13*cm])
    tabla_taller.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("TEXTCOLOR", (0,0), (-1,-1), colors.HexColor("#334155")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elementos.append(tabla_taller)

    elementos.append(Paragraph("Datos del cliente", estilo_seccion))
    cliente_data = [
        ["Nombre:", datos.get("cliente_nombre", "-")],
        ["Correo:", datos.get("cliente_email", "-")],
        ["Vehiculo:", f"{datos.get('tipo_vehiculo','')} {datos.get('marca','')} - Placa: {datos.get('placa','')}"],
    ]
    tabla_cliente = Table(cliente_data, colWidths=[4*cm, 13*cm])
    tabla_cliente.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("TEXTCOLOR", (0,0), (-1,-1), colors.HexColor("#334155")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elementos.append(tabla_cliente)

    elementos.append(Paragraph("Servicios realizados", estilo_seccion))
    precio = datos.get("servicio_precio") or 0
    servicios_data = [
        ["Servicio", "Precio"],
        [datos.get("servicio_nombre") or "Servicio general", f"${precio:,.0f}"],
    ]
    tabla_servicios = Table(servicios_data, colWidths=[13*cm, 4*cm])
    tabla_servicios.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1d4ed8")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#f8fafc"), colors.white]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
    ]))
    elementos.append(tabla_servicios)
    elementos.append(Paragraph(f"<b>TOTAL: ${precio:,.0f}</b>", estilo_total))

    if datos.get("notas"):
        elementos.append(Spacer(1, 0.4*cm))
        elementos.append(Paragraph("Observaciones", estilo_seccion))
        elementos.append(Paragraph(datos["notas"], estilo_normal))

    elementos.append(Spacer(1, 1*cm))
    elementos.append(Paragraph("Gracias por confiar en TurboTurn.", ParagraphStyle("footer", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#94a3b8"), alignment=TA_CENTER)))

    doc.build(elementos)
    return buffer.getvalue()


# ── Genera el PDF y lo envía como adjunto al correo del cliente ───────────────
def enviar_factura_pdf(datos: dict):
    pdf_bytes = generar_pdf_factura(datos)

    mensaje = MIMEMultipart()
    mensaje["Subject"] = f"Factura de servicio - {datos.get('taller_nombre', 'TurboTurn')}"
    mensaje["From"] = EMAIL_ORIGEN
    mensaje["To"] = datos["cliente_email"]
    mensaje["Reply-To"] = datos.get("taller_email", EMAIL_ORIGEN)

    cuerpo = MIMEText(f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f7fb;padding:30px;">
      <div style="max-width:560px;margin:auto;background:white;border-radius:16px;padding:30px;box-shadow:0 10px 25px rgba(0,0,0,0.08);">
        <h2 style="color:#1d4ed8;">TurboTurn - Factura de servicio</h2>
        <p style="color:#475569;">Hola <strong>{datos.get('cliente_nombre','')}</strong>,</p>
        <p style="color:#475569;">Adjunto encontraras la factura por el servicio realizado en <strong>{datos.get('taller_nombre','')}</strong>.</p>
        <p style="color:#475569;">Si tienes alguna pregunta puedes responder este correo directamente al taller.</p>
        <p style="color:#94a3b8;font-size:0.85rem;">Este correo fue enviado desde TurboTurn en nombre de {datos.get('taller_nombre','')}.</p>
      </div>
    </body></html>
    """, "html")
    mensaje.attach(cuerpo)

    adjunto = MIMEBase("application", "octet-stream")
    adjunto.set_payload(pdf_bytes)
    encoders.encode_base64(adjunto)
    adjunto.add_header("Content-Disposition", f"attachment; filename=factura_turboturn_{datos['id']}.pdf")
    mensaje.attach(adjunto)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(EMAIL_ORIGEN, EMAIL_PASSWORD)
        servidor.sendmail(EMAIL_ORIGEN, datos["cliente_email"], mensaje.as_string())
