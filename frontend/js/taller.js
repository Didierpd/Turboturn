const badgeClass = {
  pendiente: "badge-pendiente",
  confirmada: "badge-confirmada",
  completada: "badge-completada",
  cancelada: "badge-pendiente"
};

function botonesAccion(cita) {
  let btns = "";
  if (cita.estado === "pendiente")
    btns += `<button onclick="cambiarEstadoCita(${cita.id},'confirmada')" class="btn-submit" style="background:#1d4ed8;padding:6px 10px;border-radius:8px;font-size:0.8rem;">Confirmar</button>`;
  if (cita.estado === "confirmada")
    btns += `<button onclick="cambiarEstadoCita(${cita.id},'completada')" class="btn-submit" style="background:#16a34a;padding:6px 10px;border-radius:8px;font-size:0.8rem;">Completar</button>`;
  if (cita.estado !== "cancelada" && cita.estado !== "completada")
    btns += `<button onclick="cambiarEstadoCita(${cita.id},'cancelada')" class="btn-submit" style="background:#dc2626;padding:6px 10px;border-radius:8px;font-size:0.8rem;">Cancelar</button>`;
  return `<div style="display:flex;gap:6px;flex-wrap:wrap;">${btns}</div>`;
}

async function fetchCitasTaller() {
  const usuario = JSON.parse(localStorage.getItem("usuario"));
  const res = await fetch(`http://localhost:8000/api/citas/taller/${usuario.id}`);
  return await res.json();
}

async function cargarAgendaHoy() {
  const tbody = document.getElementById("agendaHoyBody");
  if (!tbody) return;

  try {
    const citas = await fetchCitasTaller();
    const hoy = new Date().toDateString();
    const citasHoy = citas.filter(c => new Date(c.fecha_hora).toDateString() === hoy);

    actualizarContadores(citas);

    if (citasHoy.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#64748b;">No hay citas para hoy</td></tr>`;
      return;
    }

    tbody.innerHTML = citasHoy.map(c => `
      <tr id="cita-${c.id}">
        <td>${new Date(c.fecha_hora).toLocaleTimeString("es-CO", {hour:"2-digit", minute:"2-digit"})}</td>
        <td>${c.cliente}</td>
        <td>${c.tipo_vehiculo} ${c.marca} (${c.placa})</td>
        <td>${c.notas || "-"}</td>
        <td><span class="badge ${badgeClass[c.estado] || ""}">${c.estado}</span></td>
        <td>${botonesAccion(c)}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6">Error al cargar agenda</td></tr>`;
  }
}

async function cargarTodasCitas() {
  const tbody = document.getElementById("todasCitasBody");
  if (!tbody) return;

  try {
    const citas = await fetchCitasTaller();

    if (citas.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#64748b;">No hay citas registradas</td></tr>`;
      return;
    }

    tbody.innerHTML = citas.map(c => `
      <tr id="cita-${c.id}">
        <td>${new Date(c.fecha_hora).toLocaleString("es-CO")}</td>
        <td>${c.cliente}</td>
        <td>${c.tipo_vehiculo} ${c.marca} (${c.placa})</td>
        <td>${c.notas || "-"}</td>
        <td><span class="badge ${badgeClass[c.estado] || ""}">${c.estado}</span></td>
        <td>${botonesAccion(c)}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6">Error al cargar citas</td></tr>`;
  }
}

async function cargarClientes() {
  const tbody = document.getElementById("clientesBody");
  if (!tbody) return;

  const usuario = JSON.parse(localStorage.getItem("usuario"));
  try {
    const res = await fetch(`http://localhost:8000/api/citas/taller/${usuario.id}/clientes`);
    const clientes = await res.json();

    if (clientes.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:#64748b;">No hay clientes registrados</td></tr>`;
      return;
    }

    tbody.innerHTML = clientes.map(c => `
      <tr>
        <td>${c.nombre}</td>
        <td>${c.email}</td>
        <td>${c.telefono || "-"}</td>
        <td>${c.tipo_vehiculo} ${c.marca} ${c.anio}</td>
        <td>${c.placa}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">Error al cargar clientes</td></tr>`;
  }
}

function actualizarContadores(citas) {
  const hoy = new Date().toDateString();
  const countHoy = citas.filter(c => new Date(c.fecha_hora).toDateString() === hoy).length;
  const countPend = citas.filter(c => c.estado === "pendiente").length;
  const countComp = citas.filter(c => c.estado === "completada").length;

  const elHoy = document.getElementById("citasHoy");
  const elPend = document.getElementById("citasPendientes");
  const elComp = document.getElementById("citasCompletadas");
  if (elHoy) elHoy.textContent = countHoy;
  if (elPend) elPend.textContent = countPend;
  if (elComp) elComp.textContent = countComp;
}

async function cambiarEstadoCita(id, estado) {
  try {
    const res = await fetch(`http://localhost:8000/api/citas/${id}/estado?estado=${estado}`, {
      method: "PUT",
    });
    if (res.ok) {
      const tabActivo = document.querySelector(".tab-btn.active")?.dataset.tab;
      if (tabActivo === "agenda") cargarAgendaHoy();
      else cargarTodasCitas();
    }
  } catch (err) {
    alert("Error al actualizar la cita.");
  }
}
