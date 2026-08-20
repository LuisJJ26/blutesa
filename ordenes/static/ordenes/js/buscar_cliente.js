(function () {
  var entrada = document.getElementById('buscador-cliente-input');
  var panel = document.getElementById('buscador-cliente-resultados');
  var filtros = document.getElementById('buscador-cliente-filtros');
  if (!entrada || !panel) return;

  var url = entrada.dataset.url;
  var tipoSeleccionado = '';
  var campos = {
    nombre: document.getElementById(entrada.dataset.campoNombre),
    codigo: document.getElementById(entrada.dataset.campoCodigo),
    barrio: document.getElementById(entrada.dataset.campoBarrio),
    direccion: document.getElementById(entrada.dataset.campoDireccion),
    telefono: document.getElementById(entrada.dataset.campoTelefono),
  };

  var ETIQUETA_TIPO = { CABLE_TV: 'Cable/TV', FIBRA: 'Fibra/Internet' };

  var temporizador = null;
  var controlador = null;
  var resaltado = -1;

  function cerrarPanel() {
    panel.classList.remove('abierto');
    panel.innerHTML = '';
    resaltado = -1;
  }

  function seleccionarCliente(cliente) {
    campos.nombre.value = cliente.nombre_completo;
    campos.codigo.value = cliente.codigo;
    campos.barrio.value = cliente.barrio;
    campos.direccion.value = cliente.direccion;
    campos.telefono.value = cliente.telefono;
    entrada.value = cliente.nombre_completo;
    cerrarPanel();
  }

  function renderResultados(resultados) {
    panel.innerHTML = '';
    if (!resultados.length) {
      var vacio = document.createElement('div');
      vacio.className = 'resultado-cliente-vacio';
      vacio.textContent = 'Sin coincidencias. Puedes llenar los datos abajo para un cliente nuevo.';
      panel.appendChild(vacio);
      panel.classList.add('abierto');
      return;
    }

    resultados.forEach(function (cliente) {
      var boton = document.createElement('button');
      boton.type = 'button';
      boton.className = 'resultado-cliente';

      var titulo = document.createElement('strong');
      titulo.textContent = cliente.nombre_completo || '(sin nombre)';
      if (!cliente.activo) {
        var estado = document.createElement('span');
        estado.className = 'badge-inactivo';
        estado.textContent = ' · inactivo';
        titulo.appendChild(estado);
      }

      var detalle = document.createElement('span');
      var etiquetaTipo = ETIQUETA_TIPO[cliente.tipo] || cliente.tipo;
      var partes = [etiquetaTipo, cliente.codigo, cliente.barrio && ('Barrio ' + cliente.barrio), cliente.direccion]
        .filter(Boolean);
      detalle.textContent = partes.join(' — ');

      boton.appendChild(titulo);
      boton.appendChild(detalle);
      boton.addEventListener('click', function () { seleccionarCliente(cliente); });
      panel.appendChild(boton);
    });
    panel.classList.add('abierto');

    // En celular, el teclado en pantalla puede tapar el panel si queda muy abajo —
    // esto lo trae a la vista sin necesidad de que el usuario haga scroll a ciegas.
    if (panel.scrollIntoView) panel.scrollIntoView({ block: 'nearest' });
  }

  function buscar(texto) {
    // AbortController no existe en navegadores antiguos — sin él simplemente no
    // se cancelan búsquedas anteriores, pero sigue funcionando.
    var senal;
    if (typeof AbortController !== 'undefined') {
      if (controlador) controlador.abort();
      controlador = new AbortController();
      senal = controlador.signal;
    }

    var parametros = '?q=' + encodeURIComponent(texto) + '&tipo=' + encodeURIComponent(tipoSeleccionado);
    fetch(url + parametros, senal ? { signal: senal } : undefined)
      .then(function (resp) { return resp.ok ? resp.json() : Promise.reject(); })
      .then(function (datos) { renderResultados(datos.resultados); })
      .catch(function (error) {
        if (error && error.name === 'AbortError') return;
      });
  }

  entrada.addEventListener('input', function () {
    var texto = entrada.value.trim();
    clearTimeout(temporizador);
    if (texto.length < 2) {
      cerrarPanel();
      return;
    }
    temporizador = setTimeout(function () { buscar(texto); }, 300);
  });

  entrada.addEventListener('keydown', function (evento) {
    var opciones = panel.querySelectorAll('.resultado-cliente');
    if (!opciones.length) return;

    if (evento.key === 'ArrowDown') {
      evento.preventDefault();
      resaltado = Math.min(resaltado + 1, opciones.length - 1);
    } else if (evento.key === 'ArrowUp') {
      evento.preventDefault();
      resaltado = Math.max(resaltado - 1, 0);
    } else if (evento.key === 'Enter' && resaltado >= 0) {
      evento.preventDefault();
      opciones[resaltado].click();
      return;
    } else if (evento.key === 'Escape') {
      cerrarPanel();
      return;
    } else {
      return;
    }

    for (var i = 0; i < opciones.length; i++) {
      opciones[i].classList.toggle('resaltado', i === resaltado);
    }
    opciones[resaltado].scrollIntoView({ block: 'nearest' });
  });

  if (filtros) {
    var botonesFiltro = filtros.querySelectorAll('.btn-filtro');
    for (var f = 0; f < botonesFiltro.length; f++) {
      botonesFiltro[f].addEventListener('click', function (evento) {
        tipoSeleccionado = evento.currentTarget.dataset.tipo;
        for (var g = 0; g < botonesFiltro.length; g++) {
          botonesFiltro[g].classList.toggle('activo', botonesFiltro[g] === evento.currentTarget);
        }
        var texto = entrada.value.trim();
        if (texto.length >= 2) buscar(texto);
      });
    }
  }

  document.addEventListener('click', function (evento) {
    var dentroDeFiltros = filtros && filtros.contains(evento.target);
    if (!panel.contains(evento.target) && evento.target !== entrada && !dentroDeFiltros) {
      cerrarPanel();
    }
  });
})();
