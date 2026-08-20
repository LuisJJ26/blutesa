(function () {
  var contenedor = document.getElementById('mapa-ubicacion');
  if (!contenedor || typeof L === 'undefined') return;

  var lat = parseFloat(contenedor.dataset.lat);
  var lng = parseFloat(contenedor.dataset.lng);
  if (isNaN(lat) || isNaN(lng)) return;

  var mapa = L.map(contenedor).setView([lat, lng], 16);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(mapa);
  L.marker([lat, lng]).addTo(mapa);
})();
