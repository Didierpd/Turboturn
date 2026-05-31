const badgeClass = {
  pendiente: "badge-pendiente",
  confirmada: "badge-confirmada",
  completada: "badge-completada",
  cancelada: "badge-pendiente"
};

let mecanicosCache = [];

function usuarioTaller() {
  return JSON.parse(localStorage.getItem("usuario"));
}

function formatoFecha(fechaHora) {
  return new Date(fechaHora).toLocaleString("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function formatoHora(fechaHora) {
  return new Date(fechaHora).toLocaleTimeString("es-CO", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function fetchCitasTaller() {
  const usuario = usuarioTaller();
  const res = await fetch(`/api/citas/taller/${usuario.id}`);
  if (!res.ok) throw new Error("Error al cargar citas");
  return await res.json();
}

async function fetchMecanicosTaller() {
  const usuario = usuarioTaller();
  const res = await fetch(`/api/mecanicos/taller/${usuario.id}`);
  if (!res.ok) throw new Error("Error al cargar mecánicos");
  mecanicosCache = await res.json();
  return mecanicosCache;
}

function opcionesMecanicos(mecanicoId) {
  const activos = mecanicosCache.filter(m => m.activo);
  if (activos.length === 0) {
    return `<option value="">Registra un mecánico</option>`;
  }

  return `<option value="">Asignar mecánico</option>` + activos.map(m => {
    const selected = Number(mecanicoId) === Number(m.id) ? "selected" : "";
    return `<option value="${m.id}" ${selected}>${m.nombre}</option>`;
  }).join("");
}

function celdaMecanico(cita) {
  if (cita.estado === "pendiente") {
    return `
      <select id="mecanico-cita-${cita.id}" style="min-width:160px;padding:8px;border-radius:8px;">
        ${opcionesMecanicos(cita.mecanico_id)}
      </select>
    `;
  }

  return cita.mecanico_nombre || "-";
}

function botonesAccion(cita) {
  let btns = "";
  if (cita.estado === "pendiente") {
    btns += `<button onclick="confirmarCita(${cita.id})" class="btn-submit" style="background:#1d4ed8;padding:6px 10px;border-radius:8px;font-size:0.8rem;">Confirmar</button>`;
  }
  if (cita.estado === "confirmada") {
    btns += `<span style="color:#64748b;font-size:0.8rem;">Asignada al mecánico</span>`;
  }
  if (cita.estado !== "cancelada" && cita.estado !== "completada") {
    btns += `<button onclick="cambiarEstadoCita(${cita.id},'cancelada')" class="btn-submit" style="background:#dc2626;padding:6px 10px;border-radius:8px;font-size:0.8rem;">Cancelar</button>`;
  }
  return `<div style="display:flex;gap:6px;flex-wrap:wrap;">${btns}</div>`;
}

async function cargarAgendaHoy() {
  const tbody = document.getElementById("agendaHoyBody");
  if (!tbody) return;

  try {
    const [citas] = await Promise.all([fetchCitasTaller(), fetchMecanicosTaller()]);
    const hoy = new Date().toDateString();
    const citasHoy = citas.filter(c => new Date(c.fecha_hora).toDateString() === hoy);

    actualizarContadores(citas);

    if (citasHoy.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#64748b;">No hay citas para hoy</td></tr>`;
      return;
    }

    tbody.innerHTML = citasHoy.map(c => `
      <tr id="cita-${c.id}">
        <td>${formatoHora(c.fecha_hora)}</td>
        <td>${c.cliente}</td>
        <td>${c.tipo_vehiculo} ${c.marca} (${c.placa})</td>
        <td>${c.notas || "-"}</td>
        <td>${celdaMecanico(c)}</td>
        <td><span class="badge ${badgeClass[c.estado] || ""}">${c.estado}</span></td>
        <td>${botonesAccion(c)}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7">Error al cargar agenda</td></tr>`;
  }
}

async function cargarTodasCitas() {
  const tbody = document.getElementById("todasCitasBody");
  if (!tbody) return;

  try {
    const [citas] = await Promise.all([fetchCitasTaller(), fetchMecanicosTaller()]);

    if (citas.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#64748b;">No hay citas registradas</td></tr>`;
      return;
    }

    tbody.innerHTML = citas.map(c => `
      <tr id="cita-${c.id}">
        <td>${formatoFecha(c.fecha_hora)}</td>
        <td>${c.cliente}</td>
        <td>${c.tipo_vehiculo} ${c.marca} (${c.placa})</td>
        <td>${c.notas || "-"}</td>
        <td>${celdaMecanico(c)}</td>
        <td><span class="badge ${badgeClass[c.estado] || ""}">${c.estado}</span></td>
        <td>${botonesAccion(c)}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7">Error al cargar citas</td></tr>`;
  }
}

async function cargarClientes() {
  const tbody = document.getElementById("clientesBody");
  if (!tbody) return;

  const usuario = usuarioTaller();
  try {
    const res = await fetch(`/api/citas/taller/${usuario.id}/clientes`);
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

async function cargarMecanicos() {
  const tbody = document.getElementById("mecanicosBody");
  if (!tbody) return;

  try {
    const mecanicos = await fetchMecanicosTaller();
    if (mecanicos.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#64748b;">No hay mecánicos registrados</td></tr>`;
      return;
    }

    tbody.innerHTML = mecanicos.map(m => `
      <tr>
        <td>${m.nombre}</td>
        <td>${m.telefono || "-"}</td>
        <td>${m.email || "-"}</td>
        <td>${m.especialidad || "-"}</td>
        <td><span class="badge ${m.activo ? "badge-confirmada" : "badge-pendiente"}">${m.activo ? "activo" : "inactivo"}</span></td>
        <td>
          <button onclick="cambiarEstadoMecanico(${m.id}, ${!m.activo})" class="btn-submit" style="background:${m.activo ? "#dc2626" : "#16a34a"};padding:6px 10px;border-radius:8px;font-size:0.8rem;">
            ${m.activo ? "Desactivar" : "Activar"}
          </button>
          <button onclick="cambiarClaveMecanico(${m.id})" class="btn-submit" style="background:#1d4ed8;padding:6px 10px;border-radius:8px;font-size:0.8rem;margin-left:6px;">
            Cambiar clave
          </button>
          <button onclick="eliminarMecanico(${m.id})" class="btn-submit" style="background:#991b1b;padding:6px 10px;border-radius:8px;font-size:0.8rem;margin-left:6px;">
            Eliminar
          </button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6">Error al cargar mecánicos</td></tr>`;
  }
}

async function cargarServiciosTaller() {
  const tbody = document.getElementById("serviciosTallerBody");
  if (!tbody) return;

  const usuario = usuarioTaller();
  try {
    const res = await fetch(`/api/servicios/taller-usuario/${usuario.id}`);
    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="4">Error al cargar servicios</td></tr>`;
      return;
    }

    const servicios = await res.json();
    if (servicios.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:#64748b;">No hay servicios registrados</td></tr>`;
      return;
    }

    tbody.innerHTML = servicios.map(s => `
      <tr>
        <td>${s.nombre}</td>
        <td>${s.descripcion || "-"}</td>
        <td>$${Number(s.precio).toLocaleString("es-CO")}</td>
        <td>${s.tiempo_estimado || "-"}</td>
        <td>
          <button onclick="eliminarServicio(${s.id})" class="btn-submit" style="background:#dc2626;padding:6px 10px;border-radius:8px;font-size:0.8rem;">
            Eliminar
          </button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4">Error al cargar servicios</td></tr>`;
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

async function confirmarCita(id) {
  const mecanicoId = document.getElementById(`mecanico-cita-${id}`)?.value;
  if (!mecanicoId) {
    alert("Selecciona un mecánico antes de confirmar la cita.");
    return;
  }

  await cambiarEstadoCita(id, "confirmada", mecanicoId);
}

async function cambiarEstadoCita(id, estado, mecanicoId = null) {
  try {
    const params = new URLSearchParams({ estado });
    if (mecanicoId) params.append("mecanico_id", mecanicoId);
    if (estado === "cancelada") {
      // El motivo se enviará por correo al cliente cuando el taller cancele la cita.
      const motivo = prompt("Motivo de cancelación para notificar al cliente:");
      if (!motivo) return;
      if (motivo.trim().length < 5) {
        alert("Escribe un motivo de cancelación más claro.");
        return;
      }
      params.append("motivo_cancelacion", motivo.trim());
    }

    const res = await fetch(`/api/citas/${id}/estado?${params.toString()}`, {
      method: "PUT",
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Error al actualizar la cita.");
      return;
    }

    const data = await res.json();
    if (estado === "cancelada" && data.correo_enviado === false) {
      alert(data.mensaje || "La cita fue cancelada, pero no se pudo enviar el correo al cliente.");
    }

    const tabActivo = document.querySelector(".tab-btn.active")?.dataset.tab;
    if (tabActivo === "agenda") cargarAgendaHoy();
    else if (tabActivo === "citas") cargarTodasCitas();
  } catch (err) {
    alert("Error al actualizar la cita.");
  }
}

function activarFormularioMecanicos() {
  const form = document.getElementById("mecanicoForm");
  if (!form) return;

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const usuario = usuarioTaller();
    const datos = {
      nombre: document.getElementById("mecanicoNombre").value.trim(),
      telefono: document.getElementById("mecanicoTelefono").value.trim() || null,
      email: document.getElementById("mecanicoEmail").value.trim(),
      password: document.getElementById("mecanicoPassword").value,
      especialidad: document.getElementById("mecanicoEspecialidad").value.trim() || null,
    };

    try {
      const res = await fetch(`/api/mecanicos/taller/${usuario.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      });

      if (!res.ok) {
        const err = await res.json();
        mostrarMensaje("mecanicoAlert", err.detail || "Error al registrar mecánico.", "error");
        return;
      }

      mostrarMensaje("mecanicoAlert", "Mecánico registrado correctamente.", "success");
      form.reset();
      cargarMecanicos();
    } catch (err) {
      mostrarMensaje("mecanicoAlert", "No se pudo conectar con el servidor.", "error");
    }
  });
}

async function cambiarEstadoMecanico(id, activo) {
  const usuario = usuarioTaller();
  try {
    const res = await fetch(`/api/mecanicos/${id}/taller/${usuario.id}/estado?activo=${activo}`, {
      method: "PUT",
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Error al cambiar el estado del mecánico.");
      return;
    }

    cargarMecanicos();
  } catch (err) {
    alert("Error al cambiar el estado del mecánico.");
  }
}

async function cambiarClaveMecanico(id) {
  const nuevaClave = prompt("Nueva contraseña para el mecánico:");
  if (!nuevaClave) return;
  if (nuevaClave.length < 6) {
    alert("La contraseña debe tener al menos 6 caracteres.");
    return;
  }

  const usuario = usuarioTaller();
  try {
    const res = await fetch(`/api/mecanicos/${id}/taller/${usuario.id}/password`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: nuevaClave }),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Error al cambiar la contraseña.");
      return;
    }

    alert("Contraseña actualizada.");
  } catch (err) {
    alert("Error al cambiar la contraseña.");
  }
}

async function eliminarMecanico(id) {
  const usuario = usuarioTaller();
  if (!confirm("¿Eliminar este mecánico? Esta acción no se puede deshacer.")) return;

  try {
    const res = await fetch(`/api/mecanicos/${id}/taller/${usuario.id}`, {
      method: "DELETE",
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Error al eliminar mecánico.");
      return;
    }

    alert("Mecánico eliminado correctamente.");
    cargarMecanicos();
  } catch (err) {
    alert("Error al eliminar mecánico.");
  }
}

function activarFormularioServicios() {
  const form = document.getElementById("servicioForm");
  if (!form) return;

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const usuario = usuarioTaller();
    const datos = {
      nombre: document.getElementById("servicioNombre").value.trim(),
      descripcion: document.getElementById("servicioDescripcion").value.trim() || null,
      precio: parseFloat(document.getElementById("servicioPrecio").value),
      tiempo_estimado: document.getElementById("servicioTiempo").value.trim() || null,
      usuario_id: usuario.id,
    };

    try {
      const res = await fetch("/api/servicios/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      });

      if (!res.ok) {
        const err = await res.json();
        mostrarMensaje("servicioAlert", err.detail || "Error al agregar servicio.", "error");
        return;
      }

      mostrarMensaje("servicioAlert", "Servicio agregado correctamente.", "success");
      form.reset();
      cargarServiciosTaller();
    } catch (err) {
      mostrarMensaje("servicioAlert", "No se pudo conectar con el servidor.", "error");
    }
  });
}

async function eliminarServicio(id) {
  const usuario = usuarioTaller();
  if (!confirm("¿Eliminar este servicio? Esta acción no se puede deshacer.")) return;

  try {
    const res = await fetch(`/api/servicios/${id}/taller-usuario/${usuario.id}`, {
      method: "DELETE",
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "Error al eliminar servicio.");
      return;
    }

    alert("Servicio eliminado correctamente.");
    cargarServiciosTaller();
  } catch (err) {
    alert("Error al eliminar servicio.");
  }
}
