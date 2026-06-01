async function cargarTalleresPendientes() {
  const tbody = document.getElementById("talleresPendientesBody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/usuarios/talleres-pendientes");
    const talleres = await res.json();

    if (talleres.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:#64748b;">No hay talleres pendientes</td></tr>`;
      return;
    }

    tbody.innerHTML = talleres.map(t => `
      <tr id="fila-${t.id}">
        <td>${t.nombre}</td>
        <td>${t.email}</td>
        <td>${t.telefono || "-"}</td>
        <td>${new Date(t.creado_en).toLocaleDateString("es-CO")}</td>
        <td style="display:flex;gap:8px;">
          <button onclick="aprobarTaller(${t.id})" class="btn-submit" style="background:#16a34a;padding:8px 14px;border-radius:8px;">Aprobar</button>
          <button onclick="rechazarTaller(${t.id})" class="btn-submit" style="background:#dc2626;padding:8px 14px;border-radius:8px;">Rechazar</button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">Error al cargar talleres</td></tr>`;
  }
}

async function aprobarTaller(id) {
  try {
    const res = await fetch(`/api/usuarios/${id}/aprobar`, { method: "PUT" });
    if (res.ok) {
      document.getElementById(`fila-${id}`).remove();
      mostrarMensaje("pendientesAlert", "Taller aprobado correctamente.", "success");
      cargarTodosUsuarios();
    }
  } catch (err) {
    mostrarMensaje("pendientesAlert", "Error al aprobar el taller.", "error");
  }
}

async function rechazarTaller(id) {
  try {
    const res = await fetch(`/api/usuarios/${id}/rechazar`, { method: "PUT" });
    if (res.ok) {
      document.getElementById(`fila-${id}`).remove();
      mostrarMensaje("pendientesAlert", "Taller rechazado.", "success");
      cargarTodosUsuarios();
    }
  } catch (err) {
    mostrarMensaje("pendientesAlert", "Error al rechazar el taller.", "error");
  }
}

async function cargarTodosUsuarios() {
  const tbody = document.getElementById("usuariosBody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/usuarios/todos");
    const usuarios = await res.json();

    const badgeRol = { usuario: "badge-confirmada", taller: "badge-pendiente", admin: "badge-completada" };
    const badgeEstado = { activo: "badge-completada", pendiente: "badge-pendiente", rechazado: "badge-pendiente" };

    tbody.innerHTML = usuarios.map(u => `
      <tr id="fila-usuario-${u.id}">
        <td>${u.nombre}</td>
        <td>${u.email}</td>
        <td><span class="badge ${badgeRol[u.rol] || ''}">${u.rol}</span></td>
        <td><span class="badge ${badgeEstado[u.estado] || ''}">${u.estado}</span></td>
        <td>${u.telefono || "-"}</td>
        <td style="display:flex;gap:6px;flex-wrap:wrap;">
          ${u.rol !== 'admin' ? `
            ${u.estado === 'activo' ? `
              <button onclick="restringirUsuario(${u.id})" class="btn-submit" style="background:#f59e0b;padding:6px 12px;border-radius:8px;font-size:0.85rem;">Restringir</button>
            ` : `
              <button onclick="activarUsuario(${u.id})" class="btn-submit" style="background:#16a34a;padding:6px 12px;border-radius:8px;font-size:0.85rem;">Activar</button>
            `}
            <button onclick="eliminarUsuario(${u.id})" class="btn-submit" style="background:#dc2626;padding:6px 12px;border-radius:8px;font-size:0.85rem;">Eliminar</button>
          ` : ''}
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6">Error al cargar usuarios</td></tr>`;
  }
}

async function activarUsuario(id) {
  if (!confirm("¿Activar este usuario?")) return;
  try {
    const res = await fetch(`/api/usuarios/${id}/activar`, { method: "PUT" });
    if (res.ok) {
      mostrarMensaje("pendientesAlert", "Usuario activado correctamente.", "success");
      cargarTodosUsuarios();
    }
  } catch (err) {
    mostrarMensaje("pendientesAlert", "Error al activar el usuario.", "error");
  }
}

async function restringirUsuario(id) {
  if (!confirm("¿Restringir este usuario? Su estado pasará a pendiente.")) return;
  try {
    const res = await fetch(`/api/usuarios/${id}/restringir`, { method: "PUT" });
    if (res.ok) {
      mostrarMensaje("pendientesAlert", "Usuario restringido correctamente.", "success");
      cargarTodosUsuarios();
    }
  } catch (err) {
    mostrarMensaje("pendientesAlert", "Error al restringir el usuario.", "error");
  }
}

async function eliminarUsuario(id) {
  if (!confirm("¿Eliminar este usuario permanentemente? Esta acción no se puede deshacer.")) return;
  try {
    const res = await fetch(`/api/usuarios/${id}/eliminar`, { method: "DELETE" });
    if (res.ok) {
      document.getElementById(`fila-usuario-${id}`).remove();
      mostrarMensaje("pendientesAlert", "Usuario eliminado.", "success");
    }
  } catch (err) {
    mostrarMensaje("pendientesAlert", "Error al eliminar el usuario.", "error");
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

function renderBarChart(id, datos, opciones = {}) {
  const contenedor = document.getElementById(id);
  if (!contenedor) return;

  if (!datos || datos.length === 0) {
    contenedor.innerHTML = `<p class="chart-empty">Sin datos disponibles</p>`;
    return;
  }

  const max = Math.max(...datos.map(item => Number(item.total) || 0), 1);
  contenedor.innerHTML = datos.map(item => {
    const total = Number(item.total) || 0;
    const ancho = Math.max((total / max) * 100, total > 0 ? 6 : 0);
    const label = escapeHtml(item.label || "Sin dato");
    return `
      <div class="bar-row">
        <div class="bar-row-head">
          <span>${label}</span>
          <strong>${opciones.moneda ? "$" : ""}${total.toLocaleString("es-CO")}</strong>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width:${ancho}%;"></div>
        </div>
      </div>
    `;
  }).join("");
}

async function cargarEstadisticasAdmin() {
  try {
    const res = await fetch("/api/citas/estadisticas/admin");
    if (!res.ok) throw new Error("Error al cargar estadísticas");
    const stats = await res.json();

    renderBarChart("adminCitasEstadoChart", stats.citas_por_estado);
    renderBarChart("adminServiciosChart", stats.servicios_mas_solicitados);
    renderBarChart("adminTalleresChart", stats.talleres_con_mas_citas);
    renderBarChart("adminClientesMesChart", stats.clientes_por_mes);
  } catch (err) {
    ["adminCitasEstadoChart", "adminServiciosChart", "adminTalleresChart", "adminClientesMesChart"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = `<p class="chart-empty">Error al cargar estadísticas</p>`;
    });
  }
}
