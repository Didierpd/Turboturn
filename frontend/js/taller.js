// =============================================================================
// taller.js
// Lógica del panel del taller: agenda, citas, clientes, mecánicos, servicios,
// contadores, gráficas y acciones de estado/facturación.
// =============================================================================

// ── Bloque de configuración: clases visuales y cachés de peticiones ──────────
const badgeClass = {
  pendiente: "badge-pendiente",
  confirmada: "badge-confirmada",
  completada: "badge-completada",
  cancelada: "badge-pendiente"
};

let mecanicosCache = [];
let serviciosTallerCache = [];
let citasTallerCache = null;
let citasTallerPromise = null;
let mecanicosTallerPromise = null;

// ── Bloque utilidades: usuario actual, fechas y escape de HTML ───────────────
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

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

// ── Bloque datos remotos: citas y mecánicos con caché para evitar duplicados ─
async function fetchCitasTaller() {
  if (citasTallerCache) return citasTallerCache;
  if (citasTallerPromise) return citasTallerPromise;

  const usuario = usuarioTaller();
  citasTallerPromise = fetch(`/api/citas/taller/${usuario.id}`)
    .then(res => {
      if (!res.ok) throw new Error("Error al cargar citas");
      return res.json();
    })
    .then(citas => {
      citasTallerCache = citas;
      return citas;
    })
    .finally(() => {
      citasTallerPromise = null;
    });

  return citasTallerPromise;
}

async function fetchMecanicosTaller() {
  if (mecanicosCache.length) return mecanicosCache;
  if (mecanicosTallerPromise) return mecanicosTallerPromise;

  const usuario = usuarioTaller();
  mecanicosTallerPromise = fetch(`/api/mecanicos/taller/${usuario.id}`)
    .then(res => {
      if (!res.ok) throw new Error("Error al cargar mecánicos");
      return res.json();
    })
    .then(mecanicos => {
      mecanicosCache = mecanicos;
      return mecanicos;
    })
    .finally(() => {
      mecanicosTallerPromise = null;
    });

  return mecanicosTallerPromise;
}

// ── Bloque UI de mecánicos: opciones y celda de asignación por cita ──────────
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

// ── Bloque acciones por cita: botones disponibles según estado ───────────────
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
  if (cita.estado === "completada") {
    btns += `<button onclick="enviarFactura(${cita.id})" class="btn-submit" style="background:#0f766e;padding:6px 10px;border-radius:8px;font-size:0.8rem;">Enviar Factura</button>`;
  }
  return `<div style="display:flex;gap:6px;flex-wrap:wrap;">${btns}</div>`;
}

// ── Bloque agenda: muestra solo las citas del día actual ─────────────────────
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

// ── Bloque citas: muestra el historial completo de citas del taller ──────────
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

// ── Bloque clientes: lista clientes que han reservado en el taller ───────────
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

// ── Bloque mecánicos: lista y administra mecánicos del taller ────────────────
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

// ── Bloque servicios: lista servicios creados por el taller ──────────────────
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
    serviciosTallerCache = servicios;
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
          <button onclick="editarServicio(${s.id})" class="btn-submit" style="background:#1d4ed8;padding:6px 10px;border-radius:8px;font-size:0.8rem;margin-right:6px;">
            Editar
          </button>
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

// ── Bloque resumen: actualiza contadores principales de agenda ───────────────
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

// ── Bloque gráficas: renderiza barras sin librerías externas ─────────────────
function renderBarChart(id, datos) {
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
          <strong>${total.toLocaleString("es-CO")}</strong>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width:${ancho}%;"></div>
        </div>
      </div>
    `;
  }).join("");
}

// ── Bloque estadísticas: agrupa datos para gráficas cuando falla el endpoint ─
function agruparConteos(items, obtenerLabel) {
  const conteos = new Map();
  items.forEach(item => {
    const label = obtenerLabel(item);
    if (!label) return;
    conteos.set(label, (conteos.get(label) || 0) + 1);
  });

  return Array.from(conteos.entries())
    .map(([label, total]) => ({ label, total }))
    .sort((a, b) => b.total - a.total || a.label.localeCompare(b.label))
    .slice(0, 8);
}

function estadisticasDesdeCitas(citas) {
  const clientesPorMes = new Map();
  const clientesVistosPorMes = new Set();

  citas.forEach(cita => {
    const fecha = cita.cliente_creado_en || cita.fecha_hora;
    if (!fecha || !cita.usuario_id) return;

    const mes = new Date(fecha).toISOString().slice(0, 7);
    const clave = `${mes}-${cita.usuario_id}`;
    if (clientesVistosPorMes.has(clave)) return;

    clientesVistosPorMes.add(clave);
    clientesPorMes.set(mes, (clientesPorMes.get(mes) || 0) + 1);
  });

  return {
    citas_por_estado: agruparConteos(citas, c => c.estado || "Sin estado"),
    servicios_mas_solicitados: agruparConteos(citas, c => c.servicio_nombre || "Revisión general"),
    clientes_por_mes: Array.from(clientesPorMes.entries())
      .map(([label, total]) => ({ label, total }))
      .sort((a, b) => a.label.localeCompare(b.label)),
    mecanicos_con_mas_citas: agruparConteos(citas, c => c.mecanico_nombre || "Sin asignar"),
  };
}

function renderEstadisticasTaller(stats) {
  renderBarChart("tallerCitasEstadoChart", stats.citas_por_estado);
  renderBarChart("tallerServiciosChart", stats.servicios_mas_solicitados);
  renderBarChart("tallerClientesMesChart", stats.clientes_por_mes);
  renderBarChart("tallerMecanicosChart", stats.mecanicos_con_mas_citas);
}

// ── Bloque estadísticas: carga métricas remotas o usa citas como respaldo ────
async function cargarEstadisticasTaller() {
  const usuario = usuarioTaller();
  try {
    const res = await fetch(`/api/citas/estadisticas/taller/${usuario.id}`);
    if (!res.ok) throw new Error("Error al cargar estadísticas");
    const stats = await res.json();
    renderEstadisticasTaller(stats);
  } catch (err) {
    try {
      const citas = await fetchCitasTaller();
      renderEstadisticasTaller(estadisticasDesdeCitas(citas));
    } catch (fallbackErr) {
      ["tallerCitasEstadoChart", "tallerServiciosChart", "tallerClientesMesChart", "tallerMecanicosChart"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = `<p class="chart-empty">Error al cargar estadísticas</p>`;
      });
    }
  }
}

// ── Bloque cambio de estado: confirmar, cancelar y refrescar panel ───────────
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

    citasTallerCache = null;
    const tabActivo = document.querySelector(".tab-btn.active")?.dataset.tab;
    if (tabActivo === "agenda") cargarAgendaHoy();
    else if (tabActivo === "citas") cargarTodasCitas();
    cargarEstadisticasTaller();
  } catch (err) {
    alert("Error al actualizar la cita.");
  }
}

// ── Bloque formulario mecánicos: alta de mecánicos para asignar citas ────────
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

// ── Bloque administración mecánicos: estado, clave y eliminación ─────────────
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

    mecanicosCache = [];
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

// ── Bloque formulario servicios: alta y edición de servicios del taller ──────
function activarFormularioServicios() {
  const form = document.getElementById("servicioForm");
  const cancelarBtn = document.getElementById("servicioCancelarEdicionBtn");
  if (!form) return;

  if (cancelarBtn) {
    cancelarBtn.addEventListener("click", cancelarEdicionServicio);
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const usuario = usuarioTaller();
    const servicioId = document.getElementById("servicioIdEditar").value;
    const datos = {
      nombre: document.getElementById("servicioNombre").value.trim(),
      descripcion: document.getElementById("servicioDescripcion").value.trim() || null,
      precio: parseFloat(document.getElementById("servicioPrecio").value),
      tiempo_estimado: document.getElementById("servicioTiempo").value.trim() || null,
      usuario_id: usuario.id,
    };

    try {
      const url = servicioId
        ? `/api/servicios/${servicioId}/taller-usuario/${usuario.id}`
        : "/api/servicios/";
      const res = await fetch(url, {
        method: servicioId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      });

      if (!res.ok) {
        const err = await res.json();
        mostrarMensaje("servicioAlert", err.detail || "Error al agregar servicio.", "error");
        return;
      }

      mostrarMensaje("servicioAlert", servicioId ? "Servicio actualizado correctamente." : "Servicio agregado correctamente.", "success");
      cancelarEdicionServicio();
      cargarServiciosTaller();
    } catch (err) {
      mostrarMensaje("servicioAlert", "No se pudo conectar con el servidor.", "error");
    }
  });
}

// ── Bloque edición servicios: llena el formulario para modificar un servicio ─
function editarServicio(id) {
  const servicio = serviciosTallerCache.find(s => Number(s.id) === Number(id));
  if (!servicio) return;

  document.getElementById("servicioIdEditar").value = servicio.id;
  document.getElementById("servicioNombre").value = servicio.nombre || "";
  document.getElementById("servicioDescripcion").value = servicio.descripcion || "";
  document.getElementById("servicioPrecio").value = Number(servicio.precio) || 0;
  document.getElementById("servicioTiempo").value = servicio.tiempo_estimado || "";

  document.getElementById("servicioSubmitBtn").textContent = "Guardar cambios";
  document.getElementById("servicioCancelarEdicionBtn").style.display = "inline-flex";
  document.getElementById("servicioForm").scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Bloque edición servicios: limpia el formulario y sale del modo edición ───
function cancelarEdicionServicio() {
  const form = document.getElementById("servicioForm");
  if (!form) return;

  form.reset();
  document.getElementById("servicioIdEditar").value = "";
  document.getElementById("servicioSubmitBtn").textContent = "Agregar servicio";
  document.getElementById("servicioCancelarEdicionBtn").style.display = "none";
}

// ── Bloque eliminación servicios: borra servicios no usados en historiales ───
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

// ── Bloque horario: consulta y actualiza el horario de atención del taller ───
function horaCortaTaller(hora) {
  return String(hora || "").slice(0, 5);
}

function minutosHorarioTaller(hora) {
  const [horas, minutos] = horaCortaTaller(hora).split(":").map(Number);
  if (Number.isNaN(horas) || Number.isNaN(minutos)) return null;
  return horas * 60 + minutos;
}

async function cargarHorarioTaller() {
  const aperturaInput = document.getElementById("tallerHorarioApertura");
  const cierreInput = document.getElementById("tallerHorarioCierre");
  if (!aperturaInput || !cierreInput) return;

  const usuario = usuarioTaller();
  try {
    const res = await fetch(`/api/usuarios/taller/${usuario.id}/horario`);
    if (!res.ok) throw new Error("No se pudo cargar el horario");

    const taller = await res.json();
    aperturaInput.value = horaCortaTaller(taller.horario_apertura || "08:00");
    cierreInput.value = horaCortaTaller(taller.horario_cierre || "18:00");
  } catch (err) {
    mostrarMensaje("horarioTallerAlert", "No se pudo cargar el horario del taller.", "error");
  }
}

function activarFormularioHorarioTaller() {
  const form = document.getElementById("horarioTallerForm");
  if (!form) return;

  form.addEventListener("submit", async function(e) {
    e.preventDefault();

    const usuario = usuarioTaller();
    const datos = {
      horario_apertura: document.getElementById("tallerHorarioApertura").value,
      horario_cierre: document.getElementById("tallerHorarioCierre").value,
    };

    if (minutosHorarioTaller(datos.horario_apertura) >= minutosHorarioTaller(datos.horario_cierre)) {
      mostrarMensaje("horarioTallerAlert", "La hora de apertura debe ser menor que la hora de cierre.", "error");
      return;
    }

    try {
      const res = await fetch(`/api/usuarios/taller/${usuario.id}/horario`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      });

      const data = await res.json();
      if (!res.ok) {
        mostrarMensaje("horarioTallerAlert", data.detail || "Error al guardar el horario.", "error");
        return;
      }

      mostrarMensaje("horarioTallerAlert", "Horario actualizado correctamente.", "success");
    } catch (err) {
      mostrarMensaje("horarioTallerAlert", "No se pudo conectar con el servidor.", "error");
    }
  });
}

// ── Bloque facturación: solicita al backend generar y enviar PDF por correo ──
async function enviarFactura(citaId) {
  if (!confirm("¿Enviar la factura al cliente por correo?")) return;
  try {
    const res = await fetch(`/api/citas/${citaId}/factura`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      alert("Factura enviada correctamente al cliente.");
    } else {
      alert(data.detail || "Error al enviar la factura.");
    }
  } catch (err) {
    alert("Error al enviar la factura.");
  }
}
