async function cargarAgendaTaller() {
  const tbody = document.getElementById("agendaBody");
  if (!tbody) return;

  const usuario = JSON.parse(localStorage.getItem("usuario"));
  if (!usuario) return;

  try {
    const res = await fetch(`http://localhost:8000/api/citas/taller/${usuario.id}`);
    const citas = await res.json();

    const hoy = new Date().toDateString();
    let countHoy = 0, countPendientes = 0, countCompletadas = 0;

    if (citas.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#64748b;">No hay citas asignadas</td></tr>`;
    } else {
      tbody.innerHTML = citas.map(c => {
        const fecha = new Date(c.fecha_hora);
        if (fecha.toDateString() === hoy) countHoy++;
        if (c.estado === "pendiente") countPendientes++;
        if (c.estado === "completada") countCompletadas++;

        const badgeClass = {
          pendiente: "badge-pendiente",
          confirmada: "badge-confirmada",
          completada: "badge-completada",
          cancelada: "badge-pendiente"
        }[c.estado] || "";

        return `
          <tr id="cita-${c.id}">
            <td>${fecha.toLocaleString("es-CO")}</td>
            <td>${c.cliente}</td>
            <td>${c.tipo_vehiculo} ${c.marca} (${c.placa})</td>
            <td>${c.notas || "-"}</td>
            <td><span class="badge ${badgeClass}">${c.estado}</span></td>
            <td style="display:flex;gap:6px;flex-wrap:wrap;">
              ${c.estado === "pendiente" ? `<button onclick="cambiarEstadoCita(${c.id},'confirmada')" class="btn-submit" style="background:#1d4ed8;padding:6px 10px;border-radius:8px;font-size:0.8rem;">Confirmar</button>` : ""}
              ${c.estado === "confirmada" ? `<button onclick="cambiarEstadoCita(${c.id},'completada')" class="btn-submit" style="background:#16a34a;padding:6px 10px;border-radius:8px;font-size:0.8rem;">Completar</button>` : ""}
              ${c.estado !== "cancelada" && c.estado !== "completada" ? `<button onclick="cambiarEstadoCita(${c.id},'cancelada')" class="btn-submit" style="background:#dc2626;padding:6px 10px;border-radius:8px;font-size:0.8rem;">Cancelar</button>` : ""}
            </td>
          </tr>
        `;
      }).join("");
    }

    const elHoy = document.getElementById("citasHoy");
    const elPend = document.getElementById("citasPendientes");
    const elComp = document.getElementById("citasCompletadas");
    if (elHoy) elHoy.textContent = countHoy;
    if (elPend) elPend.textContent = countPendientes;
    if (elComp) elComp.textContent = countCompletadas;

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6">Error al cargar agenda</td></tr>`;
  }
}

async function cambiarEstadoCita(id, estado) {
  try {
    const res = await fetch(`http://localhost:8000/api/citas/${id}/estado?estado=${estado}`, {
      method: "PUT",
    });
    if (res.ok) {
      cargarAgendaTaller();
    }
  } catch (err) {
    alert("Error al actualizar la cita.");
  }
}
