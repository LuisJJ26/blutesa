(function () {
  'use strict';

  // ---------- GPS ----------
  var estadoGps = document.getElementById('estado-gps');
  var campoLat = document.getElementById('id_gps_lat');
  var campoLng = document.getElementById('id_gps_lng');
  var campoPrecision = document.getElementById('id_gps_precision_m');
  var checkSinGps = document.getElementById('id_sin_georreferencia');
  var campoMotivoSinGps = document.getElementById('id_motivo_sin_gps');

  function marcarSinGps(motivo) {
    checkSinGps.checked = true;
    if (motivo && !campoMotivoSinGps.value) { campoMotivoSinGps.value = motivo; }
  }

  function capturarGps() {
    if (!('geolocation' in navigator)) {
      estadoGps.textContent = 'Este dispositivo no soporta GPS.';
      marcarSinGps('Dispositivo sin soporte de geolocalización.');
      return;
    }
    estadoGps.textContent = 'Obteniendo ubicación…';
    navigator.geolocation.getCurrentPosition(
      function (posicion) {
        campoLat.value = posicion.coords.latitude;
        campoLng.value = posicion.coords.longitude;
        campoPrecision.value = posicion.coords.accuracy;
        checkSinGps.checked = false;
        estadoGps.textContent = 'Ubicación capturada (±' + Math.round(posicion.coords.accuracy) + ' m).';
      },
      function (error) {
        estadoGps.textContent = 'No se pudo obtener la ubicación: ' + error.message;
        marcarSinGps('GPS no disponible: ' + error.message);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
    );
  }

  var btnReintentarGps = document.getElementById('btn-reintentar-gps');
  if (btnReintentarGps) { btnReintentarGps.addEventListener('click', capturarGps); }
  capturarGps();
})();
