from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from kardex.views import rol_requerido

from .models import Cliente, ClienteFibra

LIMITE_AJAX = 15
FILAS_POR_PAGINA = 25
LIMITE_COMBINADO = 100


def _condiciones_cable(texto):
    condiciones = Q()
    for termino in texto.split():
        condiciones &= (
            Q(nombre__icontains=termino)
            | Q(apellido1__icontains=termino)
            | Q(apellido2__icontains=termino)
            | Q(codigo__icontains=termino)
            | Q(contrato__icontains=termino)
            | Q(direccion__icontains=termino)
            | Q(telefono__icontains=termino)
        )
    return condiciones


def _condiciones_fibra(texto):
    condiciones = Q()
    for termino in texto.split():
        condiciones &= (
            Q(nombre__icontains=termino)
            | Q(cedula__icontains=termino)
            | Q(barrio__icontains=termino)
            | Q(telefono__icontains=termino)
        )
    return condiciones


def _fila_cable(cliente):
    return {
        'tipo': 'CABLE_TV', 'tipo_display': 'Cable/TV',
        'nombre': cliente.nombre_completo, 'identificador': cliente.codigo,
        'barrio': cliente.barrio_nombre, 'telefono': cliente.telefono,
        'estado': 'Activo' if cliente.activo else 'Inactivo', 'activo': cliente.activo,
        'pk': cliente.pk,
    }


def _fila_fibra(cliente):
    return {
        'tipo': 'FIBRA', 'tipo_display': cliente.get_tipo_display(),
        'nombre': cliente.nombre, 'identificador': cliente.cedula,
        'barrio': cliente.barrio, 'telefono': cliente.telefono,
        'estado': '—', 'activo': None,
        'pk': cliente.pk,
    }


@rol_requerido('JEFE_OPERACIONES')
@require_GET
def buscar_ajax(request):
    """Autocompletado usado al crear una Orden de Trabajo (ordenes/crear.html) — busca
    en los dos maestros de clientes (Cable/TV y Fibra/Internet) a la vez, o solo en uno
    si se manda ?tipo=CABLE_TV o ?tipo=FIBRA (mismos botones de filtro que /clientes/)."""
    texto = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    if len(texto) < 2:
        return JsonResponse({'resultados': []})

    cable = Cliente.objects.filter(_condiciones_cable(texto))[:LIMITE_AJAX] \
        if tipo in ('', 'CABLE_TV') else Cliente.objects.none()
    fibra = ClienteFibra.objects.filter(_condiciones_fibra(texto))[:LIMITE_AJAX] \
        if tipo in ('', 'FIBRA') else ClienteFibra.objects.none()

    resultados = [
        {
            'tipo': 'CABLE_TV',
            'nombre_completo': c.nombre_completo,
            'codigo': c.codigo,
            'barrio': c.barrio_nombre,
            'direccion': c.direccion,
            'telefono': c.telefono,
            'activo': c.activo,
        }
        for c in cable
    ] + [
        {
            'tipo': 'FIBRA',
            'nombre_completo': c.nombre,
            'codigo': c.cedula,
            'barrio': c.barrio,
            'direccion': c.barrio,
            'telefono': c.telefono,
            'activo': True,
        }
        for c in fibra
    ]
    resultados.sort(key=lambda r: r['nombre_completo'])

    return JsonResponse({'resultados': resultados[:LIMITE_AJAX]})


@rol_requerido('JEFE_OPERACIONES')
def buscar(request):
    """Sección propia de Clientes — separada del Kardex y de Órdenes de Trabajo a
    propósito, con su propio link de navegación. Filtros por botones (no <select>,
    para que sea más resistente en navegadores viejos) y, para quien tenga permiso de
    administración, un botón directo al admin de Django."""
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')

    if tipo == 'FIBRA':
        fibra_qs = ClienteFibra.objects.all()
        if q:
            fibra_qs = fibra_qs.filter(_condiciones_fibra(q))
        pagina = Paginator(fibra_qs, FILAS_POR_PAGINA).get_page(request.GET.get('pagina'))
        filas = [_fila_fibra(c) for c in pagina]

    elif tipo == '' and q:
        # Búsqueda de texto sin filtrar por tipo: se combinan ambos maestros. Se
        # acotan las consultas (LIMITE_COMBINADO) porque acá sí se materializan en
        # Python para poder ordenarlas juntas antes de paginar.
        cable_qs = Cliente.objects.filter(_condiciones_cable(q))
        if estado == 'ACTIVO':
            cable_qs = cable_qs.filter(activo=True)
        elif estado == 'INACTIVO':
            cable_qs = cable_qs.filter(activo=False)
        fibra_qs = ClienteFibra.objects.filter(_condiciones_fibra(q))

        combinadas = [_fila_cable(c) for c in cable_qs[:LIMITE_COMBINADO]]
        combinadas += [_fila_fibra(c) for c in fibra_qs[:LIMITE_COMBINADO]]
        combinadas.sort(key=lambda f: f['nombre'])

        pagina = Paginator(combinadas, FILAS_POR_PAGINA).get_page(request.GET.get('pagina'))
        filas = pagina.object_list

    else:
        # tipo == 'CABLE_TV', o tipo == '' sin texto de búsqueda (~12 mil filas —
        # se pagina la queryset directo en la base de datos, sin traerla a memoria).
        cable_qs = Cliente.objects.all()
        if q:
            cable_qs = cable_qs.filter(_condiciones_cable(q))
        if estado == 'ACTIVO':
            cable_qs = cable_qs.filter(activo=True)
        elif estado == 'INACTIVO':
            cable_qs = cable_qs.filter(activo=False)
        pagina = Paginator(cable_qs, FILAS_POR_PAGINA).get_page(request.GET.get('pagina'))
        filas = [_fila_cable(c) for c in pagina]

    parametros = request.GET.copy()
    parametros.pop('pagina', None)

    return render(request, 'clientes/buscar.html', {
        'filas': filas,
        'pagina': pagina,
        'q': q,
        'tipo': tipo,
        'estado': estado,
        'querystring': parametros.urlencode(),
        'puede_administrar': request.user.es_admin(),
    })
