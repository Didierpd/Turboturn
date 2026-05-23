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

function botonTrabajo(cita) {
  if (cita.estado !== "confirmada") {
    return "-";
  }

  return `
    <button onclick="abrirFormularioFinalizacion(${cita.id})" class="btn-submit" style="background:#16a34a;padding:6px 10px;border-radius:8px;font-size:0.8rem;">
      Trabajo terminado
    </button>
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
      tbody.innerHTML = `<tr><td colspan="6">Error al cargar trabajos</td></tr>`;
      return;
    }

    const citas = await res.json();
    trabajosCache = citas;
    actualizarContadoresTrabajos(citas);

    if (citas.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#64748b;">No tienes trabajos asignados</td></tr>`;
      return;
    }

    tbody.innerHTML = citas.map(c => `
      <tr>
        <td>${formatoFechaTrabajo(c.fecha_hora)}</td>
        <td>${c.cliente}</td>
        <td>${c.tipo_vehiculo} ${c.marca} (${c.placa})</td>
        <td>${c.notas || "-"}</td>
        <td><span class="badge ${mecanicoBadgeClass[c.estado] || ""}">${c.estado}</span></td>
        <td>${botonTrabajo(c)}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6">Error al cargar trabajos</td></tr>`;
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
