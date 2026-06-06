// =============================================================================
// app.js
// Funciones compartidas del frontend de clientes: login, registro, citas,
// vehículos, mensajes de alerta y carga inicial por página.
// =============================================================================

// ── Bloque global: fuerza llamadas API sin caché del navegador ───────────────
function activarFetchSinCache() {
  if (window.__turboTurnFetchSinCache) return;
  window.__turboTurnFetchSinCache = true;

  const fetchOriginal = window.fetch.bind(window);
  window.fetch = function (resource, options = {}) {
    const requestUrl = typeof resource === "string" ? resource : resource.url;
    const esApiLocal = requestUrl && requestUrl.startsWith("/api/");
    const method = (options.method || "GET").toUpperCase();

    if (!esApiLocal) {
      return fetchOriginal(resource, options);
    }

    const headers = new Headers(options.headers || {});
    headers.set("Cache-Control", "no-cache");
    headers.set("Pragma", "no-cache");

    return fetchOriginal(resource, {
      ...options,
      cache: "no-store",
      headers,
      method,
    });
  };
}

activarFetchSinCache();

let talleresReservaCache = [];

// ── Bloque de UI: muestra alertas temporales reutilizables ───────────────────
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

function formatearHoraCorta(hora) {
  return String(hora || "").slice(0, 5);
}

function minutosDesdeHora(hora) {
  const [horas, minutos] = formatearHoraCorta(hora).split(":").map(Number);
  if (Number.isNaN(horas) || Number.isNaN(minutos)) return null;
  return horas * 60 + minutos;
}

function obtenerTallerReservaSeleccionado() {
  const tallerId = Number(document.getElementById("taller")?.value);
  return talleresReservaCache.find(taller => Number(taller.id) === tallerId) || null;
}

function validarFechaDentroHorarioTaller(fechaHora) {
  const taller = obtenerTallerReservaSeleccionado();
  if (!taller || !fechaHora) return { valido: true };

  const apertura = minutosDesdeHora(taller.horario_apertura || "08:00");
  const cierre = minutosDesdeHora(taller.horario_cierre || "18:00");
  const fecha = new Date(fechaHora);
  const minutosCita = fecha.getHours() * 60 + fecha.getMinutes();

  if (apertura === null || cierre === null) return { valido: true };
  if (minutosCita < apertura || minutosCita >= cierre) {
    return {
      valido: false,
      mensaje: `Este taller atiende de ${formatearHoraCorta(taller.horario_apertura)} a ${formatearHoraCorta(taller.horario_cierre)}.`,
    };
  }

  return { valido: true };
}

function actualizarAyudaHorarioTaller() {
  const ayuda = document.getElementById("tallerHorarioHelp");
  if (!ayuda) return;

  const taller = obtenerTallerReservaSeleccionado();
  if (!taller) {
    ayuda.textContent = "Selecciona un taller para ver su horario.";
    return;
  }

  ayuda.textContent = `Horario: ${formatearHoraCorta(taller.horario_apertura)} a ${formatearHoraCorta(taller.horario_cierre)}.`;
}

// ── Bloque login: inicia sesión y redirige según MFA/rol ─────────────────────
function activarFormularioLogin() {
  const form = document.getElementById("loginForm");
  if (!form) return;

  // ── Fase 1: email + contraseña ──
  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const email = document.getElementById("correo").value;
    const contrasena = document.getElementById("contrasena").value;
    const submitBtn = form.querySelector("button[type='submit']");
    const textoOriginal = submitBtn ? submitBtn.textContent : "";
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Ingresando...";
    }

    try {
      const res = await fetch("/api/usuarios/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: contrasena }),
      });

      if (!res.ok) {
        const err = await res.json();
        mostrarMensaje("loginAlert", err.detail || "Correo o contraseña incorrectos.", "error");
        return;
      }

      const data = await res.json();
      if (data.mfa_requerido) {
        const cuentaTipo = data.cuenta_tipo || "usuario";
        window.location.href = `./mfa-login.html?usuario_id=${data.usuario_id}&cuenta_tipo=${cuentaTipo}`;
        return;
      }
      localStorage.setItem("usuario", JSON.stringify(data.usuario));
      window.location.href = "./pantalladeInicio.html?v=10";

    } catch (err) {
      mostrarMensaje("loginAlert", "No se pudo conectar con el servidor.", "error");
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = textoOriginal;
      }
    }
  });

  // ── Fase 2: validar código MFA ──
  const mfaForm = document.getElementById("mfaForm");
  if (mfaForm) {
    mfaForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const usuario_id = sessionStorage.getItem("mfa_usuario_id");
      const codigo = document.getElementById("codigoMFA").value.trim();

      try {
        const res = await fetch("/api/mfa/validar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ usuario_id: parseInt(usuario_id), codigo }),
        });

        if (!res.ok) {
          mostrarMensaje("mfaAlert", "Código incorrecto. Inténtalo de nuevo.", "error");
          return;
        }

        // Código correcto → cargar datos del usuario y entrar
        const userRes = await fetch(`/api/usuarios/${usuario_id}`);
        const usuario = await userRes.json();
        sessionStorage.removeItem("mfa_usuario_id");
        localStorage.setItem("usuario", JSON.stringify(usuario));
        window.location.href = "./pantalladeInicio.html?v=10";

      } catch (err) {
        mostrarMensaje("mfaAlert", "No se pudo conectar con el servidor.", "error");
      }
    });
  }
}

// ── Bloque select de talleres: carga talleres activos para reservar cita ─────
async function cargarTalleresEnSelect() {
  const select = document.getElementById("taller");
  if (!select) return;
  try {
    const res = await fetch("/api/citas/talleres-activos");
    const talleres = await res.json();
    talleresReservaCache = talleres;
    if (talleres.length === 0) {
      select.innerHTML = `<option value="">No hay talleres disponibles</option>`;
      return;
    }
    select.innerHTML = `<option value="">Selecciona un taller</option>` +
      talleres.map(t => `
        <option value="${t.id}">
          ${t.nombre} — ${t.direccion} (${formatearHoraCorta(t.horario_apertura)} a ${formatearHoraCorta(t.horario_cierre)})
        </option>
      `).join("");
    actualizarAyudaHorarioTaller();
  } catch (err) {
    select.innerHTML = `<option value="">Error al cargar talleres</option>`;
  }
}

// ── Bloque select de vehículos: carga vehículos del usuario actual ───────────
async function cargarVehiculosEnSelect() {
  const select = document.getElementById("vehiculo");
  if (!select) return;

  const usuario = JSON.parse(localStorage.getItem("usuario"));
  if (!usuario) return;

  try {
    const res = await fetch(`/api/vehiculos/${usuario.id}`);
    const vehiculos = await res.json();
    if (vehiculos.length === 0) {
      select.innerHTML = `<option value="">No tienes vehículos registrados</option>`;
      return;
    }
    select.innerHTML = `<option value="">Selecciona un vehículo</option>` +
      vehiculos.map(v => `<option value="${v.id}">${v.tipo_vehiculo} ${v.marca} - ${v.placa}</option>`).join("");
  } catch (err) {
    select.innerHTML = `<option value="">Error al cargar vehículos</option>`;
  }
}

// ── Bloque selector fecha/hora: arma un valor ISO uniforme para la reserva ───
function activarSelectorFechaHora() {
  const fechaInput = document.getElementById("fecha");
  const diaSelect = document.getElementById("fechaDia");
  const mesSelect = document.getElementById("fechaMes");
  const anioSelect = document.getElementById("fechaAnio");
  const horaSelect = document.getElementById("fechaHora");
  const minutoSelect = document.getElementById("fechaMinuto");
  const periodoSelect = document.getElementById("fechaPeriodo");
  const ayuda = document.getElementById("fechaHelp");

  if (!fechaInput || !diaSelect || !mesSelect || !anioSelect || !horaSelect || !minutoSelect || !periodoSelect) return;

  const meses = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
  ];
  const ahora = new Date();
  const anioActual = ahora.getFullYear();

  function opcion(valor, texto) {
    return `<option value="${valor}">${texto}</option>`;
  }

  function dosDigitos(valor) {
    return String(valor).padStart(2, "0");
  }

  function cargarOpcionesBase() {
    mesSelect.innerHTML = '<option value="">Mes</option>' +
      meses.map((mes, index) => opcion(index + 1, mes)).join("");

    anioSelect.innerHTML = '<option value="">Año</option>' +
      [anioActual, anioActual + 1].map(anio => opcion(anio, anio)).join("");

    horaSelect.innerHTML = '<option value="">Hora</option>' +
      Array.from({ length: 12 }, (_, i) => opcion(i + 1, i + 1)).join("");

    minutoSelect.innerHTML = '<option value="">Min</option>' +
      [0, 15, 30, 45].map(minuto => opcion(dosDigitos(minuto), dosDigitos(minuto))).join("");
  }

  function actualizarDias() {
    const diaActual = diaSelect.value;
    const mes = Number(mesSelect.value);
    const anio = Number(anioSelect.value);
    const diasDelMes = mes && anio ? new Date(anio, mes, 0).getDate() : 31;

    const hoy = new Date();
    const esHoy = anio === hoy.getFullYear() && mes === (hoy.getMonth() + 1);
    const diaMinimo = esHoy ? hoy.getDate() : 1;

    diaSelect.innerHTML = '<option value="">Día</option>' +
      Array.from({ length: diasDelMes }, (_, i) => i + 1)
        .filter(dia => dia >= diaMinimo)
        .map(dia => opcion(dia, dia)).join("");

    if (diaActual && Number(diaActual) <= diasDelMes && Number(diaActual) >= diaMinimo) {
      diaSelect.value = diaActual;
    }
  }

  function limpiarErrorFecha() {
    document.querySelectorAll(".datetime-picker select").forEach(select => select.classList.remove("field-error"));
    if (ayuda) {
      ayuda.classList.remove("field-help-error");
      ayuda.textContent = "Selecciona fecha y hora para reservar.";
    }
  }

  function sincronizarFechaHora() {
    const dia = Number(diaSelect.value);
    const mes = Number(mesSelect.value);
    const anio = Number(anioSelect.value);
    const hora = Number(horaSelect.value);
    const minuto = minutoSelect.value;
    const periodo = periodoSelect.value;

    limpiarErrorFecha();

    if (!dia || !mes || !anio || !hora || minuto === "" || !periodo) {
      fechaInput.value = "";
      return "";
    }

    let hora24 = hora % 12;
    if (periodo === "PM") hora24 += 12;

    const fechaSeleccionada = new Date(`${anio}-${dosDigitos(mes)}-${dosDigitos(dia)}T${dosDigitos(hora24)}:${minuto}`);
    if (fechaSeleccionada <= new Date()) {
      fechaInput.value = "";
      if (ayuda) {
        ayuda.classList.add("field-help-error");
        ayuda.textContent = "No puedes reservar en una fecha u hora que ya pasó.";
      }
      return "";
    }

    fechaInput.value = `${anio}-${dosDigitos(mes)}-${dosDigitos(dia)}T${dosDigitos(hora24)}:${minuto}`;
    return fechaInput.value;
  }

  function marcarErrorFecha() {
    document.querySelectorAll(".datetime-picker select").forEach(select => {
      if (!select.value) select.classList.add("field-error");
    });
    if (ayuda) {
      ayuda.classList.add("field-help-error");
      ayuda.textContent = "Completa la fecha y la hora antes de reservar.";
    }
  }

  function resetearSelectorFechaHora() {
    [diaSelect, mesSelect, anioSelect, horaSelect, minutoSelect, periodoSelect].forEach(select => {
      select.value = "";
    });
    fechaInput.value = "";
    actualizarDias();
    limpiarErrorFecha();
  }

  cargarOpcionesBase();
  actualizarDias();

  [diaSelect, mesSelect, anioSelect, horaSelect, minutoSelect, periodoSelect].forEach(select => {
    select.addEventListener("change", function () {
      if (select === mesSelect || select === anioSelect) actualizarDias();
      sincronizarFechaHora();
    });
  });

  window.obtenerFechaHoraCita = sincronizarFechaHora;
  window.marcarErrorFechaHoraCita = marcarErrorFecha;
  window.resetearFechaHoraCita = resetearSelectorFechaHora;
}

// ── Bloque formulario de citas: reserva cita y carga servicios por taller ────
function activarFormularioCitas() {
  const form = document.getElementById("citaForm");
  if (!form) return;

  activarSelectorFechaHora();
  cargarTalleresEnSelect();
  cargarVehiculosEnSelect();

  document.getElementById("taller").addEventListener("change", async function() {
    const tallerId = this.value;
    const grupo = document.getElementById("servicioGroup");
    const select = document.getElementById("servicio");

    if (!tallerId) {
      grupo.style.display = "none";
      select.disabled = false;
      select.innerHTML = '<option value="">Selecciona primero un taller</option>';
      actualizarAyudaHorarioTaller();
      return;
    }

    actualizarAyudaHorarioTaller();

    grupo.style.display = "block";
    select.disabled = true;
    select.innerHTML = '<option value="">Cargando servicios del taller...</option>';

    try {
      const res = await fetch("/api/servicios/taller/" + tallerId);
      if (!res.ok) throw new Error("No se pudieron cargar los servicios");

      const servicios = await res.json();
      select.disabled = false;

      if (!servicios.length) {
        select.innerHTML = '<option value="">Revisión general (este taller no tiene servicios publicados)</option>';
        return;
      }

      select.innerHTML = '<option value="">Selecciona un servicio o revisión general</option>' +
        servicios.map(s => {
          const precio = Number(s.precio || 0).toLocaleString("es-CO");
          return '<option value="' + s.id + '">' + s.nombre + ' — $' + precio + '</option>';
        }).join("");
    } catch (err) {
      select.disabled = false;
      select.innerHTML = '<option value="">No se pudieron cargar los servicios</option>';
    }
  });

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const usuario = JSON.parse(localStorage.getItem("usuario"));
    if (!usuario) return;

    const fechaHora = window.obtenerFechaHoraCita ? window.obtenerFechaHoraCita() : document.getElementById("fecha").value;

    const datos = {
      usuario_id: usuario.id,
      taller_id: parseInt(document.getElementById("taller").value),
      vehiculo_id: parseInt(document.getElementById("vehiculo").value),
      fecha_hora: fechaHora,
      notas: document.getElementById("notas").value,
      servicio_id: parseInt(document.getElementById("servicio").value) || null,
    };

    if (!datos.taller_id) {
      mostrarMensaje("citaAlert", "Selecciona un taller.", "error");
      return;
    }
    if (!datos.vehiculo_id) {
      mostrarMensaje("citaAlert", "Selecciona un vehículo.", "error");
      return;
    }

    if (!datos.fecha_hora) {
      const dia = document.getElementById("fechaDia")?.value;
      const mes = document.getElementById("fechaMes")?.value;
      const anio = document.getElementById("fechaAnio")?.value;
      const hora = document.getElementById("fechaHora")?.value;
      const minuto = document.getElementById("fechaMinuto")?.value;
      const periodo = document.getElementById("fechaPeriodo")?.value;
      const todosLlenos = dia && mes && anio && hora && minuto !== "" && periodo;
      if (todosLlenos) {
        mostrarMensaje("citaAlert", "No puedes reservar en una fecha u hora que ya pasó.", "error");
      } else {
        if (window.marcarErrorFechaHoraCita) window.marcarErrorFechaHoraCita();
        mostrarMensaje("citaAlert", "Completa la fecha y la hora antes de reservar.", "error");
      }
      return;
    }

    const validacionHorario = validarFechaDentroHorarioTaller(datos.fecha_hora);
    if (!validacionHorario.valido) {
      mostrarMensaje("citaAlert", validacionHorario.mensaje, "error");
      return;
    }

    try {
      const res = await fetch("/api/citas/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      });

      if (!res.ok) {
        const err = await res.json();
        mostrarMensaje("citaAlert", err.detail || "Error al reservar la cita.", "error");
        return;
      }

      mostrarMensaje("citaAlert", "Cita reservada correctamente.", "success");
      form.reset();
      if (window.resetearFechaHoraCita) window.resetearFechaHoraCita();
      cargarCitasUsuario();
    } catch (err) {
      mostrarMensaje("citaAlert", "No se pudo conectar con el servidor.", "error");
    }
  });
}

// ── Bloque tabla de citas: lista citas del usuario en paneles cliente ────────
async function cargarCitasUsuario() {
  const tbody = document.getElementById("citasBody");
  if (!tbody) return;

  const usuario = JSON.parse(localStorage.getItem("usuario"));
  if (!usuario) return;

  try {
    const res = await fetch(`/api/citas/${usuario.id}`);
    const citas = await res.json();

    if (citas.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:#64748b;">No tienes citas registradas</td></tr>`;
      return;
    }

    const badgeClass = {
      pendiente: "badge-pendiente",
      confirmada: "badge-confirmada",
      completada: "badge-completada",
      cancelada: "badge-pendiente"
    };

    tbody.innerHTML = citas.map(c => `
      <tr>
        <td>${new Date(c.fecha_hora).toLocaleString("es-CO", {
          dateStyle: "short",
          timeStyle: "short",
        })}</td>
        <td>${c.marca} (${c.placa})</td>
        <td>${c.taller || "-"}</td>
        <td><span class="badge ${badgeClass[c.estado] || ''}">${c.estado}</span></td>
        <td>${c.notas || "-"}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">Error al cargar citas</td></tr>`;
  }
}

// ── Bloque vehículos: lista vehículos registrados por el usuario ─────────────
async function cargarVehiculos() {
  const usuario = JSON.parse(localStorage.getItem("usuario"));
  if (!usuario) return;

  const tbody = document.getElementById("vehiculosBody");
  if (!tbody) return;

  try {
    const res = await fetch(`/api/vehiculos/${usuario.id}`);
    const vehiculos = await res.json();

    if (vehiculos.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#64748b;">No tienes vehículos registrados</td></tr>`;
      return;
    }

    tbody.innerHTML = vehiculos.map(v => `
      <tr>
        <td>${v.tipo_vehiculo}</td>
        <td>${v.marca}</td>
        <td>${v.anio}</td>
        <td>${v.placa}</td>
        <td>${v.color || "-"}</td>
        <td>
          <button onclick="eliminarVehiculo(${v.id})" class="btn-submit" style="background:#dc2626;padding:6px 10px;border-radius:8px;font-size:0.8rem;">
            Eliminar
          </button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6">Error al cargar vehículos</td></tr>`;
  }
}

// ── Bloque vehículos: elimina un vehículo del usuario con confirmación ───────
async function eliminarVehiculo(id) {
  const usuario = JSON.parse(localStorage.getItem("usuario"));
  if (!usuario) return;

  if (!confirm("¿Eliminar este vehículo? Esta acción no se puede deshacer.")) return;

  try {
    const res = await fetch(`/api/vehiculos/${id}?usuario_id=${usuario.id}`, {
      method: "DELETE",
    });

    if (!res.ok) {
      const err = await res.json();
      mostrarMensaje("vehiculoAlert", err.detail || "Error al eliminar vehículo.", "error");
      return;
    }

    mostrarMensaje("vehiculoAlert", "Vehículo eliminado correctamente.", "success");
    cargarVehiculos();
  } catch (err) {
    mostrarMensaje("vehiculoAlert", "No se pudo conectar con el servidor.", "error");
  }
}

// ── Bloque formulario vehículos: registra nuevos vehículos del usuario ───────
function activarFormularioVehiculos() {
  const form = document.getElementById("vehiculoForm");
  if (!form) return;

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const usuario = JSON.parse(localStorage.getItem("usuario"));
    if (!usuario) return;

    const datos = {
      usuario_id: usuario.id,
      tipo_vehiculo: document.getElementById("tipo_vehiculo").value,
      marca: document.getElementById("marca").value,
      anio: document.getElementById("anio").value,
      placa: document.getElementById("placa").value,
      color: document.getElementById("color").value,
    };

    try {
      const res = await fetch("/api/vehiculos/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      });

      if (!res.ok) {
        mostrarMensaje("vehiculoAlert", "Error al guardar el vehículo.", "error");
        return;
      }

      mostrarMensaje("vehiculoAlert", "Vehículo agregado correctamente.", "success");
      form.reset();
      cargarVehiculos();
    } catch (err) {
      mostrarMensaje("vehiculoAlert", "No se pudo conectar con el servidor.", "error");
    }
  });
}

// ── Bloque registro: crea cuentas de usuario o taller con ubicación ──────────
function activarFormularioRegistro() {
  const form = document.getElementById("registroForm");
  if (!form) return;

  const rolSelect = document.getElementById("rol");
  const camposTaller = document.getElementById("camposTaller");

  function toggleCamposTaller() {
    const esTaller = rolSelect.value === "taller";
    camposTaller.style.display = esTaller ? "block" : "none";
    document.getElementById("nombre_taller").required = esTaller;
    document.getElementById("direccion_taller").required = esTaller;
  }

  rolSelect.addEventListener("change", toggleCamposTaller);
  toggleCamposTaller();

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const rol = document.getElementById("rol").value;
    const datos = {
      nombre: document.getElementById("nombre").value,
      email: document.getElementById("email").value,
      telefono: document.getElementById("telefono").value,
      password: document.getElementById("contrasena").value,
      rol,
       genero: document.getElementById("genero").value || null,

    };

    if (rol === "taller") {
      datos.nombre_taller = document.getElementById("nombre_taller").value;
      datos.direccion_taller = document.getElementById("direccion_taller").value;
      const lat = document.getElementById("latitud_taller").value;
      const lng = document.getElementById("longitud_taller").value;
      if (!datos.nombre_taller || !datos.direccion_taller) {
        mostrarMensaje("registroAlert", "Ingresa el nombre y la dirección del taller.", "error");
        return;
      }
      if (!lat || !lng) {
        mostrarMensaje("registroAlert", "Ubica tu taller en el mapa antes de registrarte.", "error");
        return;
      }
      datos.latitud = parseFloat(lat);
      datos.longitud = parseFloat(lng);
      datos.horario_apertura = document.getElementById("horario_apertura").value;
      datos.horario_cierre = document.getElementById("horario_cierre").value;
      if (!datos.horario_apertura || !datos.horario_cierre) {
        mostrarMensaje("registroAlert", "Ingresa el horario de atención del taller.", "error");
        return;
      }
      if (minutosDesdeHora(datos.horario_apertura) >= minutosDesdeHora(datos.horario_cierre)) {
        mostrarMensaje("registroAlert", "La hora de apertura debe ser menor que la hora de cierre.", "error");
        return;
      }
    }

    try {
      const res = await fetch("/api/usuarios/registro", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      });

      const data = await res.json();

      if (!res.ok) {
        mostrarMensaje("registroAlert", data.detail || "Error al registrarse.", "error");
        return;
      }

      mostrarMensaje("registroAlert", "Registro exitoso. Te enviamos un código a tu correo.", "success");
      const emailVal = document.getElementById("email").value;
      setTimeout(() => {
        window.location.href = `./verificar.html?email=${encodeURIComponent(emailVal)}`;
      }, 2000);
    } catch (err) {
      mostrarMensaje("registroAlert", "No se pudo conectar con el servidor.", "error");
    }
  });
}

// ── Bloque arranque: activa solo los formularios presentes en cada vista ─────
document.addEventListener("DOMContentLoaded", function () {
  activarFormularioLogin();
  activarFormularioRegistro();
  cargarCitasUsuario();
  activarFormularioCitas();
  activarFormularioVehiculos();
  cargarVehiculos();
});
