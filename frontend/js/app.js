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

function activarFormularioLogin() {
  const form = document.getElementById("loginForm");
  if (!form) return;

  // ── Fase 1: email + contraseña ──
  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const email = document.getElementById("correo").value;
    const contrasena = document.getElementById("contrasena").value;

    try {
      const res = await fetch("/api/usuarios/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: contrasena }),
      });

      if (!res.ok) {
        const err = await res.json();
        const mecanicoRes = await fetch("/api/mecanicos/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password: contrasena }),
        });

        if (mecanicoRes.ok) {
          const mecanicoData = await mecanicoRes.json();
          localStorage.setItem("usuario", JSON.stringify(mecanicoData.usuario));
          window.location.href = "./pantalladeInicio.html";
          return;
        }

        mostrarMensaje("loginAlert", "Correo o contraseña incorrectos.", "error");
        return;
      }

      const data = await res.json();
      if (data.mfa_requerido) {
        window.location.href = `./mfa-login.html?usuario_id=${data.usuario_id}`;
        return;
      }
      localStorage.setItem("usuario", JSON.stringify(data.usuario));
      window.location.href = "./pantalladeInicio.html";

    } catch (err) {
      mostrarMensaje("loginAlert", "No se pudo conectar con el servidor.", "error");
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
        window.location.href = "./pantalladeInicio.html";

      } catch (err) {
        mostrarMensaje("mfaAlert", "No se pudo conectar con el servidor.", "error");
      }
    });
  }
}

async function cargarTalleresEnSelect() {
  const select = document.getElementById("taller");
  if (!select) return;
  try {
    const res = await fetch("/api/citas/talleres-activos");
    const talleres = await res.json();
    if (talleres.length === 0) {
      select.innerHTML = `<option value="">No hay talleres disponibles</option>`;
      return;
    }
    select.innerHTML = `<option value="">Selecciona un taller</option>` +
      talleres.map(t => `<option value="${t.id}">${t.nombre} — ${t.direccion}</option>`).join("");
  } catch (err) {
    select.innerHTML = `<option value="">Error al cargar talleres</option>`;
  }
}

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

function activarFormularioCitas() {
  const form = document.getElementById("citaForm");
  if (!form) return;

  const fechaInput = document.getElementById("fecha");

  fechaInput.addEventListener("invalid", function () {
    if (!fechaInput.value) {
      fechaInput.setCustomValidity("Selecciona o escribe la fecha y la hora completa.");
    }
  });

  fechaInput.addEventListener("input", function () {
    fechaInput.setCustomValidity("");
  });

  cargarTalleresEnSelect();
  cargarVehiculosEnSelect();

  document.getElementById("taller").addEventListener("change", function() {
    const tallerId = this.value;
    const grupo = document.getElementById("servicioGroup");
    const select = document.getElementById("servicio");
    if (!tallerId) {
      grupo.style.display = "none";
      select.innerHTML = '<option value="">Revisión general (sin servicio específico)</option>';
      return;
    }
    fetch("/api/servicios/taller/" + tallerId)
      .then(r => r.json())
      .then(servicios => {
        grupo.style.display = "block";
        select.innerHTML = '<option value="">Revisión general (sin servicio específico)</option>' +
          servicios.map(s => '<option value="' + s.id + '">' + s.nombre + ' — $' + Number(s.precio).toLocaleString("es-CO") + '</option>').join("");
      })
      .catch(() => { grupo.style.display = "none"; });
  });

    form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const usuario = JSON.parse(localStorage.getItem("usuario"));
    if (!usuario) return;

    const datos = {
      usuario_id: usuario.id,
      taller_id: parseInt(document.getElementById("taller").value),
      vehiculo_id: parseInt(document.getElementById("vehiculo").value),
      fecha_hora: document.getElementById("fecha").value,
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

    if (!document.getElementById("fecha").value) {
      mostrarMensaje("citaAlert", "Selecciona o escribe la fecha y la hora completa.", "error");
      return;
    }

    try {
      const res = await fetch("/api/citas/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      });

      if (!res.ok) {
        mostrarMensaje("citaAlert", "Error al reservar la cita.", "error");
        return;
      }

      mostrarMensaje("citaAlert", "Cita reservada correctamente.", "success");
      form.reset();
      cargarCitasUsuario();
    } catch (err) {
      mostrarMensaje("citaAlert", "No se pudo conectar con el servidor.", "error");
    }
  });
}

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
    };

    if (rol === "taller") {
      datos.nombre_taller = document.getElementById("nombre_taller").value;
      datos.direccion_taller = document.getElementById("direccion_taller").value;
      if (!datos.nombre_taller || !datos.direccion_taller) {
        mostrarMensaje("registroAlert", "Ingresa el nombre y la dirección del taller.", "error");
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

document.addEventListener("DOMContentLoaded", function () {
  activarFormularioLogin();
  activarFormularioRegistro();
  cargarCitasUsuario();
  activarFormularioCitas();
  activarFormularioVehiculos();
  cargarVehiculos();
});
