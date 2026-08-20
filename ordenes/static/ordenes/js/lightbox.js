(function () {
  var overlay = document.getElementById('lightbox-overlay');
  var imagenGrande = document.getElementById('lightbox-imagen');
  var botonCerrar = document.getElementById('lightbox-cerrar');
  var enlaces = document.querySelectorAll('[data-lightbox]');
  if (!overlay || !imagenGrande || !enlaces.length) return;

  function abrir(url) {
    imagenGrande.src = url;
    overlay.classList.add('abierto');
  }

  function cerrar() {
    overlay.classList.remove('abierto');
    imagenGrande.src = '';
  }

  for (var i = 0; i < enlaces.length; i++) {
    enlaces[i].addEventListener('click', function (evento) {
      evento.preventDefault();
      abrir(evento.currentTarget.href);
    });
  }

  botonCerrar.addEventListener('click', cerrar);
  overlay.addEventListener('click', function (evento) {
    if (evento.target === overlay) cerrar();
  });
  document.addEventListener('keydown', function (evento) {
    if (evento.key === 'Escape') cerrar();
  });
})();
