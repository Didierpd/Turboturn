const mecanicoBadgeClass = {
  pendiente: "badge-pendiente",
  confirmada: "badge-confirmada",
  completada: "badge-completada",
  cancelada: "badge-pendiente"
};

let trabajosCache = [];
let serviciosCache = [];

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

function botonTrabajo(cita) {
  if (cita.estado !== "confirmada") {
    return "-";
  }

  return `
    <button onclick="abrirFormularioRevision(${cita.id})" class="btn-submit" style="background:#1d4ed8;padding:6px 10px;border-radius:8px;font-size:0.8rem;">
      Registrar revisión
    </button>
    <button onclick="abrirFormularioFinalizacion(${cita.id})" class="btn-submit" style="background:#16a34a;padding:6px 10px;border-radius:8px;font-size:0.8rem;">
      Trabajo terminado
    </button>
  `;
}

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

function actualizarContadoresTrabajos(citas) {
  const asignadas = citas.length;
  const pendientes = citas.filter(c => c.estado === "confirmada").length;
  const terminadas = citas.filter(c => c.estado === "completada").length;

  document.getElementById("trabajosAsignados").textContent = asignadas;
  document.getElementById("trabajosPendientes").textContent = pendientes;
  document.getElementById("trabajosTerminados").textContent = terminadas;
}

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

    tbody.innerHTML = citas.map(c => `
      <tr>
        <td>${formatoFechaTrabajo(c.fecha_hora)}</td>
        <td>${c.cliente}</td>
        <td>${c.tipo_vehiculo} ${c.marca} (${c.placa})</td>
        <td>${c.notas || "-"}</td>
        <td>${resumenRevision(c)}</td>
        <td><span class="badge ${mecanicoBadgeClass[c.estado] || ""}">${c.estado}</span></td>
        <td>${botonTrabajo(c)}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7">Error al cargar trabajos</td></tr>`;
  }
}

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

    alert("Servicio guardado en el historial del cliente.");
    cerrarFormularioFinalizacion();
    cargarTrabajosMecanico();
  } catch (err) {
    mostrarMensaje("finalizarTrabajoAlert", "No se pudo guardar el servicio en el historial.", "error");
  }
}
