function mostrarMensaje(id, mensaje) {
  const alertBox = document.getElementById(id);
  if (!alertBox) return;

  alertBox.textContent = mensaje;
  alertBox.style.display = "block";

  setTimeout(() => {
    alertBox.style.display = "none";
  }, 3000);
}

function activarFormularioLogin() {
  const form = document.getElementById("loginForm");
  if (!form) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    mostrarMensaje("loginAlert", "Inicio de sesión simulado correctamente.");
    setTimeout(() => {
      window.location.href = "./pantalladeInicio.html";
    }, 1200);
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

function activarFormularioVehiculos() {
  const form = document.getElementById("vehiculoForm");
  if (!form) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    mostrarMensaje("vehiculoAlert", "Vehículo agregado correctamente.");
    form.reset();
  });
}

document.addEventListener("DOMContentLoaded", function () {
  activarFormularioLogin();
  activarFormularioCitas();
  activarFormularioVehiculos();
});