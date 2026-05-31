let mapaTalleres = null;
let marcadoresTalleres = [];

function coordenadaValida(valor) {
  return valor !== null && valor !== undefined && valor !== "" && !Number.isNaN(Number(valor));
}

function marcadorHtml() {
  return `
    <span class="map-marker">
      <span></span>
    </span>
  `;
}

function crearIconoTaller() {
  return L.divIcon({
    className: "map-marker-shell",
    html: marcadorHtml(),
    iconSize: [34, 34],
    iconAnchor: [17, 34],
    popupAnchor: [0, -30],
  });
}

function popupTaller(taller) {
  return `
    <div class="map-popup">
      <strong>${taller.nombre}</strong>
      <p>${taller.direccion || "Dirección no registrada"}</p>
      <span>${taller.telefono || "Sin teléfono"}</span>
    </div>
  `;
}

function pintarListaTalleres(talleres) {
  const lista = document.getElementById("listaTalleresMapa");
  if (!lista) return;

  if (talleres.length === 0) {
    lista.innerHTML = `<p style="color:#64748b;">No hay talleres activos para mostrar.</p>`;
    return;
  }

  lista.innerHTML = talleres.map((taller, index) => `
    <button type="button" class="map-list-item" onclick="enfocarTaller(${index})">
      <strong>${taller.nombre}</strong>
      <span>${taller.direccion || "Dirección no registrada"}</span>
    </button>
  `).join("");
}

function enfocarTaller(index) {
  const marcador = marcadoresTalleres[index];
  if (!mapaTalleres || !marcador) return;

  mapaTalleres.setView(marcador.getLatLng(), 15, { animate: true });
  marcador.openPopup();
}

async function cargarMapaTalleres() {
  const contenedor = document.getElementById("mapaTalleres");
  if (!contenedor) return;

  mapaTalleres = L.map("mapaTalleres", {
    scrollWheelZoom: true,
    zoomControl: true,
  }).setView([4.6500, -74.0900], 12);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(mapaTalleres);

  try {
    const res = await fetch("/api/citas/talleres-activos");
    if (!res.ok) throw new Error("No se pudieron cargar los talleres");

    const talleres = await res.json();
    const talleresConCoordenadas = talleres.filter(t =>
      coordenadaValida(t.latitud) && coordenadaValida(t.longitud)
    );

    pintarListaTalleres(talleresConCoordenadas);

    if (talleresConCoordenadas.length === 0) {
      document.getElementById("mapaEstado").textContent = "No hay talleres con coordenadas registradas.";
      return;
    }

    const icono = crearIconoTaller();
    marcadoresTalleres = talleresConCoordenadas.map(taller => {
      const marcador = L.marker([Number(taller.latitud), Number(taller.longitud)], { icon: icono })
        .addTo(mapaTalleres)
        .bindPopup(popupTaller(taller));
      return marcador;
    });

    const grupo = L.featureGroup(marcadoresTalleres);
    mapaTalleres.fitBounds(grupo.getBounds().pad(0.18));
    document.getElementById("mapaEstado").textContent = `${talleresConCoordenadas.length} talleres activos en el mapa`;
  } catch (err) {
    document.getElementById("mapaEstado").textContent = "Error al cargar el mapa de talleres.";
  }
}

document.addEventListener("DOMContentLoaded", cargarMapaTalleres);
