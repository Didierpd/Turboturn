// =============================================================================
// mecanico.js
// Controla el panel del mecánico: trabajos asignados, revisión inicial,
// finalización del servicio, actualización de historial y MFA.
// =============================================================================

// ── Bloque configuración: clases visuales y cachés del panel ─────────────────
const mecanicoBadgeClass = {
  pendiente: "badge-pendiente",
  pendiente_revision: "badge-pendiente",
  revision_hecha: "badge-confirmada",
  confirmada: "badge-confirmada",
  completada: "badge-completada",
  cancelada: "badge-pendiente"
};

let trabajosCache = [];
let serviciosCache = [];

// ── Bloque UI compartida: mensajes temporales y datos del mecánico actual ────
function mostrarMensaje(id, mensaje, tipo = "success") {
  const alertBox = document.getElementById(id);
  if (!alertBox) return;

  alertBox.textContent = mensaje;
  alertBox.className = `alert alert-${tipo}`;
  alertBox.style.display = "block";

  setTimeout(() => {
    alertBox.style.display = "none";
  }, 3000);
}

function mecanicoActual() {
  return JSON.parse(localStorage.getItem("usuario"));
}

// ── Bloque formato: fechas y limpieza de texto para pintar tablas ────────────
function formatoFechaTrabajo(fechaHora) {
  return new Date(fechaHora).toLocaleString("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function escaparHtml(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, caracter => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[caracter]));
}

// ── Bloque estado del trabajo: interpreta la fase actual de cada cita ────────
function etapaTrabajo(cita) {
  if (cita.estado === "completada") {
    return {
      clave: "completada",
      texto: "Trabajo terminado",
      detalle: "El servicio ya fue guardado en el historial del cliente.",
    };
  }

  if (cita.estado === "cancelada") {
    return {
      clave: "cancelada",
      texto: "Cancelada",
      detalle: "La cita fue cancelada por el taller.",
    };
  }

  if (cita.tiempo_estimado_revision || cita.trabajo_requerido) {
    return {
      clave: "revision_hecha",
      texto: "Revisión hecha",
      detalle: "Ya puedes finalizar el trabajo cuando el servicio esté completo.",
    };
  }

  return {
    clave: "pendiente_revision",
    texto: "Pendiente de revisión",
    detalle: "Primero registra el tiempo estimado y qué toca realizar.",
  };
}

// ── Bloque acciones de tabla: botones según fase del trabajo ─────────────────
function botonTrabajo(cita) {
  if (cita.estado !== "confirmada") {
    return "-";
  }

  const tieneRevision = Boolean(cita.tiempo_estimado_revision || cita.trabajo_requerido);

  return `
    <div class="mechanic-actions">
      <button onclick="abrirFormularioRevision(${cita.id})" class="btn-submit mechanic-action-primary">
        ${tieneRevision ? "Editar revisión" : "Registrar revisión"}
      </button>
      ${tieneRevision ? `
        <button onclick="abrirFormularioFinalizacion(${cita.id})" class="btn-submit mechanic-action-success">
          Finalizar trabajo
        </button>
      ` : ""}
    </div>
  `;
}

// ── Bloque revisión: muestra resumen de diagnóstico ya registrado ────────────
function resumenRevision(cita) {
  // Muestra en la tabla lo que el mecánico ya reportó después de revisar el vehículo.
  if (!cita.tiempo_estimado_revision && !cita.trabajo_requerido) {
    return "-";
  }

  return `
    <div style="min-width:180px;">
      <strong>Tiempo:</strong> ${escaparHtml(cita.tiempo_estimado_revision || "-")}<br>
      <strong>Trabajo:</strong> ${escaparHtml(cita.trabajo_requerido || "-")}
    </div>
  `;
}

// ── Bloque contadores: métricas rápidas del panel mecánico ───────────────────
function actualizarContadoresTrabajos(citas) {
  const asignadas = citas.length;
  const pendientes = citas.filter(c => etapaTrabajo(c).clave === "pendiente_revision").length;
  const revisadas = citas.filter(c => etapaTrabajo(c).clave === "revision_hecha").length;
  const terminadas = citas.filter(c => c.estado === "completada").length;

  document.getElementById("trabajosAsignados").textContent = asignadas;
  document.getElementById("trabajosPendientes").textContent = pendientes;
  document.getElementById("trabajosRevisados").textContent = revisadas;
  document.getElementById("trabajosTerminados").textContent = terminadas;
}

// ── Bloque trabajos: carga y pinta las citas asignadas al mecánico ───────────
async function cargarTrabajosMecanico() {
  const tbody = document.getElementById("trabajosBody");
  if (!tbody) return;

  const mecanico = mecanicoActual();
  try {
    const res = await fetch(`/api/mecanicos/${mecanico.id}/citas`);
    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="7">Error al cargar trabajos</td></tr>`;
      return;
    }

    const citas = await res.json();
    trabajosCache = citas;
    actualizarContadoresTrabajos(citas);

    if (citas.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#64748b;">No tienes trabajos asignados</td></tr>`;
      return;
    }

    tbody.innerHTML = citas.map(c => {
      const etapa = etapaTrabajo(c);
      return `
      <tr>
        <td>${formatoFechaTrabajo(c.fecha_hora)}</td>
        <td>${escaparHtml(c.cliente)}</td>
        <td>${escaparHtml(c.tipo_vehiculo)} ${escaparHtml(c.marca)} (${escaparHtml(c.placa)})</td>
        <td>${escaparHtml(c.notas || "-")}</td>
        <td>${resumenRevision(c)}</td>
        <td>
          <span class="badge ${mecanicoBadgeClass[etapa.clave] || ""}">${etapa.texto}</span>
          <div class="mechanic-status-detail">${etapa.detalle}</div>
        </td>
        <td>${botonTrabajo(c)}</td>
      </tr>
    `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7">Error al cargar trabajos</td></tr>`;
  }
}

// ── Bloque formulario revisión: abre/cierra y guarda diagnóstico inicial ─────
function abrirFormularioRevision(citaId) {
  const cita = trabajosCache.find(c => Number(c.id) === Number(citaId));
  if (!cita) return;

  // Precarga la revisión existente para que el mecánico pueda corregirla sin perder información.
  document.getElementById("revisionCitaId").value = citaId;
  document.getElementById("tiempoEstimadoRevision").value = cita.tiempo_estimado_revision || "";
  document.getElementById("trabajoRequerido").value = cita.trabajo_requerido || "";

  const card = document.getElementById("revisionTrabajoCard");
  card.style.display = "block";
  card.scrollIntoView({ behavior: "smooth", block: "start" });
}

function cerrarFormularioRevision() {
  document.getElementById("revisionTrabajoForm").reset();
  document.getElementById("revisionTrabajoCard").style.display = "none";
}

function activarFormularioRevision() {
  const form = document.getElementById("revisionTrabajoForm");
  if (!form) return;

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const citaId = document.getElementById("revisionCitaId").value;
    const tiempoEstimado = document.getElementById("tiempoEstimadoRevision").value.trim();
    const trabajoRequerido = document.getElementById("trabajoRequerido").value.trim();

    if (tiempoEstimado.length < 2) {
      mostrarMensaje("revisionTrabajoAlert", "Indica cuánto tiempo puede demorar.", "error");
      return;
    }

    if (trabajoRequerido.length < 5) {
      mostrarMensaje("revisionTrabajoAlert", "Describe qué toca realizar.", "error");
      return;
    }

    await guardarRevisionTrabajo(citaId, {
      tiempo_estimado_revision: tiempoEstimado,
      trabajo_requerido: trabajoRequerido,
    });
  });
}

async function guardarRevisionTrabajo(citaId, datos) {
  const mecanico = mecanicoActual();
  try {
    // Envia el diagnóstico de revisión sin marcar la cita como terminada.
    const res = await fetch(`/api/mecanicos/${mecanico.id}/citas/${citaId}/revision`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos),
    });

    if (!res.ok) {
      const err = await res.json();
      mostrarMensaje("revisionTrabajoAlert", err.detail || "No se pudo guardar la revisión.", "error");
      return;
    }

    mostrarMensaje("revisionTrabajoAlert", "Revisión guardada correctamente.", "success");
    cerrarFormularioRevision();
    cargarTrabajosMecanico();
  } catch (err) {
    mostrarMensaje("revisionTrabajoAlert", "No se pudo guardar la revisión.", "error");
  }
}

// ── Bloque servicios: carga servicios del taller para finalizar trabajos ─────
async function cargarServiciosMecanico() {
  const mecanico = mecanicoActual();
  const select = document.getElementById("servicioRealizado");
  if (!select) return;

  try {
    const res = await fetch(`/api/servicios/taller/${mecanico.taller_id}`);
    if (!res.ok) {
      select.innerHTML = `<option value="">Error al cargar servicios</option>`;
      return;
    }

    serviciosCache = await res.json();
    if (serviciosCache.length === 0) {
      select.innerHTML = `<option value="">No hay servicios registrados</option>`;
      return;
    }

    select.innerHTML = `<option value="">Selecciona un servicio</option>` +
      serviciosCache.map(s => `<option value="${s.id}" data-precio="${s.precio}">${s.nombre}</option>`).join("");
  } catch (err) {
    select.innerHTML = `<option value="">Error al cargar servicios</option>`;
  }
}

// ── Bloque formulario finalización: abre/cierra y valida cierre de trabajo ───
function abrirFormularioFinalizacion(citaId) {
  const cita = trabajosCache.find(c => Number(c.id) === Number(citaId));
  if (!cita) return;

  document.getElementById("finalizarCitaId").value = citaId;
  document.getElementById("observacionesFinales").value = cita.notas || "";
  document.getElementById("costoFinal").value = "";
  document.getElementById("servicioRealizado").value = "";

  const card = document.getElementById("finalizarTrabajoCard");
  card.style.display = "block";
  card.scrollIntoView({ behavior: "smooth", block: "start" });
}

function cerrarFormularioFinalizacion() {
  document.getElementById("finalizarTrabajoForm").reset();
  document.getElementById("finalizarTrabajoCard").style.display = "none";
}

function activarFormularioFinalizacion() {
  const form = document.getElementById("finalizarTrabajoForm");
  const servicioSelect = document.getElementById("servicioRealizado");
  if (!form || !servicioSelect) return;

  cargarServiciosMecanico();

  servicioSelect.addEventListener("change", function () {
    const precio = this.selectedOptions[0]?.dataset.precio;
    if (precio) {
      document.getElementById("costoFinal").value = Number(precio);
    }
  });

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const citaId = document.getElementById("finalizarCitaId").value;
    const servicioId = document.getElementById("servicioRealizado").value;
    const costoFinal = document.getElementById("costoFinal").value;
    const observaciones = document.getElementById("observacionesFinales").value.trim();

    if (!servicioId) {
      mostrarMensaje("finalizarTrabajoAlert", "Selecciona el servicio realizado.", "error");
      return;
    }

    if (!costoFinal || Number(costoFinal) < 0) {
      mostrarMensaje("finalizarTrabajoAlert", "Ingresa un costo final válido.", "error");
      return;
    }

    await terminarTrabajo(citaId, {
      servicio_id: parseInt(servicioId),
      costo_final: Number(costoFinal),
      observaciones,
    });
  });
}

// ── Bloque cierre: marca el trabajo como terminado y notifica al cliente ─────
async function terminarTrabajo(citaId, datos) {
  const mecanico = mecanicoActual();
  try {
    const res = await fetch(`/api/mecanicos/${mecanico.id}/citas/${citaId}/terminar`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos),
    });

    if (!res.ok) {
      const err = await res.json();
      mostrarMensaje("finalizarTrabajoAlert", err.detail || "No se pudo guardar el servicio en el historial.", "error");
      return;
    }

    const data = await res.json();
    if (data.correo_enviado === false) {
      mostrarMensaje("finalizarTrabajoAlert", "Trabajo finalizado, pero no se pudo enviar el correo al cliente.", "error");
    } else {
      mostrarMensaje("finalizarTrabajoAlert", "Trabajo finalizado y notificado al cliente.", "success");
    }
    cerrarFormularioFinalizacion();
    cargarTrabajosMecanico();
  } catch (err) {
    mostrarMensaje("finalizarTrabajoAlert", "No se pudo guardar el servicio en el historial.", "error");
  }
}
