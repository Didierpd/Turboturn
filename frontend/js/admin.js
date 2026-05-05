async function cargarTalleresPendientes() {
  const tbody = document.getElementById("talleresPendientesBody");
  if (!tbody) return;

  try {
    const res = await fetch("http://localhost:8000/api/usuarios/talleres-pendientes");
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
    const res = await fetch(`http://localhost:8000/api/usuarios/${id}/aprobar`, { method: "PUT" });
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
    const res = await fetch(`http://localhost:8000/api/usuarios/${id}/rechazar`, { method: "PUT" });
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
    const res = await fetch("http://localhost:8000/api/usuarios/todos");
    const usuarios = await res.json();

    const badgeRol = { usuario: "badge-confirmada", taller: "badge-pendiente", admin: "badge-completada" };
    const badgeEstado = { activo: "badge-completada", pendiente: "badge-pendiente", rechazado: "badge-pendiente" };

    tbody.innerHTML = usuarios.map(u => `
      <tr>
        <td>${u.nombre}</td>
        <td>${u.email}</td>
        <td><span class="badge ${badgeRol[u.rol] || ''}">${u.rol}</span></td>
        <td><span class="badge ${badgeEstado[u.estado] || ''}">${u.estado}</span></td>
        <td>${u.telefono || "-"}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">Error al cargar usuarios</td></tr>`;
  }
}
