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

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const email = document.getElementById("correo").value;
    const contrasena = document.getElementById("contrasena").value;

    try {
      const res = await fetch("http://localhost:8000/api/usuarios/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, contrasena }),
      });

      if (!res.ok) {
        mostrarMensaje("loginAlert", "Correo o contraseña incorrectos.", "error");
        return;
      }

      const usuario = await res.json();
      localStorage.setItem("usuario", JSON.stringify(usuario));
      window.location.href = "./pantalladeInicio.html";

    } catch (err) {
      mostrarMensaje("loginAlert", "No se pudo conectar con el servidor.", "error");
    }
  });
}

function activarFormularioCitas() {
  const form = document.getElementById("citaForm");
  if (!form) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    mostrarMensaje("citaAlert", "Cita reservada correctamente.");
    form.reset();
  });
}

async function cargarVehiculos() {
  const usuario = JSON.parse(localStorage.getItem("usuario"));
  if (!usuario) return;

  const tbody = document.getElementById("vehiculosBody");
  if (!tbody) return;

  try {
    const res = await fetch(`http://localhost:8000/api/vehiculos/${usuario.id}`);
    const vehiculos = await res.json();

    tbody.innerHTML = vehiculos.map(v => `
      <tr>
        <td>${v.tipo_vehiculo}</td>
        <td>${v.marca}</td>
        <td>${v.anio}</td>
        <td>${v.placa}</td>
        <td>${v.color || "-"}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">Error al cargar vehículos</td></tr>`;
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
      const res = await fetch("http://localhost:8000/api/vehiculos/", {
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

document.addEventListener("DOMContentLoaded", function () {
  activarFormularioLogin();
  activarFormularioCitas();
  activarFormularioVehiculos();
  cargarVehiculos();
});