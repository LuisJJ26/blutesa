from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.push import enviar_push
from kardex.models import NumeroSecuencia
from kardex.views import rol_requerido

from . import nextcloud
from .forms import LineasOrdenForm, OrdenTrabajoCierreForm, OrdenTrabajoCrearForm
from .models import OrdenTrabajo, OrdenTrabajoFoto, OrdenTrabajoLinea

Usuario = get_user_model()

TIPO_SECUENCIA = 'OT'


@rol_requerido('JEFE_OPERACIONES')
def crear(request):
    if request.method == 'POST':
        form = OrdenTrabajoCrearForm(request.POST)
        if form.is_valid():
            orden = form.save(commit=False)
            orden.numero = NumeroSecuencia.siguiente_numero(TIPO_SECUENCIA)
            orden.creado_por = request.user
            orden.save()
            messages.success(request, f'{orden.numero_formateado} creada.')
            if orden.tecnico_id:
                enviar_push(
                    [orden.tecnico],
                    titulo=f'Nueva orden {orden.numero_formateado}',
                    cuerpo=f'{orden.get_tipo_servicio_display()} — {orden.cliente_nombre} ({orden.barrio})',
                    url=f'/ordenes/orden/{orden.pk}/',
                )
            return redirect('ordenes:detalle', pk=orden.pk)
        messages.error(request, 'Revisa los datos de la orden.')
    else:
        form = OrdenTrabajoCrearForm()

    recientes = OrdenTrabajo.objects.select_related('tecnico').filter(creado_por=request.user)[:20]
    return render(request, 'ordenes/crear.html', {'form': form, 'recientes': recientes})


@rol_requerido('TECNICO')
def panel_tecnico(request):
    usuario = request.user
    pendientes = OrdenTrabajo.objects.filter(
        tecnico=usuario, estado=OrdenTrabajo.Estado.PENDIENTE
    )
    cerradas = OrdenTrabajo.objects.filter(tecnico=usuario, estado=OrdenTrabajo.Estado.CERRADA)[:15]
    return render(request, 'ordenes/panel_tecnico.html', {
        'pendientes': pendientes,
        'cerradas': cerradas,
    })


@login_required
def detalle(request, pk):
    orden = get_object_or_404(
        OrdenTrabajo.objects.select_related('tecnico', 'creado_por', 'cerrado_por'), pk=pk
    )
    usuario = request.user
    if not (
        usuario.es_admin()
        or usuario.rol == 'JEFE_OPERACIONES'
        or (usuario.rol == 'TECNICO' and orden.tecnico_id == usuario.id)
    ):
        messages.error(request, 'No tienes permiso para ver esta orden.')
        return redirect('inicio')

    return render(request, 'ordenes/detalle.html', {
        'orden': orden,
        'lineas': orden.lineas.all(),
        'fotos': orden.fotos.all(),
        'puede_cerrar': orden.puede_cerrar(usuario),
        'puede_cancelar': orden.puede_cancelar(usuario),
    })


@rol_requerido('JEFE_OPERACIONES')
def cancelar(request, pk):
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    if request.method == 'POST' and orden.puede_cancelar(request.user):
        orden.estado = OrdenTrabajo.Estado.CANCELADA
        orden.save(update_fields=['estado'])
        messages.info(request, f'{orden.numero_formateado} cancelada.')
    return redirect('ordenes:detalle', pk=pk)


@rol_requerido('TECNICO')
def cerrar(request, pk):
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    if not orden.puede_cerrar(request.user):
        messages.error(request, 'Esta orden ya no se puede cerrar (o no es tuya).')
        return redirect('ordenes:detalle', pk=pk)

    if request.method == 'POST':
        cierre_form = OrdenTrabajoCierreForm(request.POST, instance=orden)
        lineas_form = LineasOrdenForm(request.POST)

        formularios_validos = cierre_form.is_valid() and lineas_form.is_valid()
        if formularios_validos and not request.FILES.getlist('foto_reparacion'):
            cierre_form.add_error(None, 'Falta la foto del trabajo realizado.')
            formularios_validos = False

        if formularios_validos:
            ahora = timezone.now()
            orden = cierre_form.save(commit=False)
            # gps_lat/gps_lng/gps_precision_m son campos del form pero no del ModelForm
            # (Meta.fields no los incluye), así que save(commit=False) no los copia solo.
            orden.gps_lat = cierre_form.cleaned_data.get('gps_lat')
            orden.gps_lng = cierre_form.cleaned_data.get('gps_lng')
            orden.gps_precision_m = cierre_form.cleaned_data.get('gps_precision_m')
            orden.estado = OrdenTrabajo.Estado.CERRADA
            orden.cerrado_por = request.user
            orden.fecha_cierre = ahora
            # Autorización automática del Jefe de Operaciones (ver comentario en el modelo).
            orden.autorizado_por = Usuario.objects.filter(rol='JEFE_OPERACIONES').first()
            orden.fecha_autorizacion = ahora
            orden.save()

            for concepto, _etiqueta, campo_cant, campo_valor in lineas_form.filas():
                cantidad = lineas_form.cleaned_data.get(f'cantidad_{concepto}')
                valor = lineas_form.cleaned_data.get(f'valor_{concepto}')
                if cantidad is None and valor is None:
                    continue
                OrdenTrabajoLinea.objects.update_or_create(
                    orden=orden, concepto=concepto,
                    defaults={'fecha': orden.fecha_elaboracion or orden.fecha, 'cantidad': cantidad, 'valor': valor},
                )

            errores_fotos = 0
            for archivo in request.FILES.getlist('foto_reparacion'):
                try:
                    ruta, url_publica = nextcloud.subir_evidencia(
                        archivo.name, archivo.read(), archivo.content_type, orden.numero_formateado,
                    )
                    OrdenTrabajoFoto.objects.create(
                        orden=orden, ruta_nextcloud=ruta,
                        url_publica=url_publica, subida_por=request.user,
                    )
                except nextcloud.SubidaNextcloudError:
                    errores_fotos += 1

            if errores_fotos:
                messages.warning(request, f'{errores_fotos} foto(s) no se pudieron subir. Puedes agregarlas luego.')
            messages.success(request, f'{orden.numero_formateado} cerrada correctamente.')
            enviar_push(
                Usuario.objects.filter(rol='JEFE_OPERACIONES'),
                titulo=f'{orden.numero_formateado} culminada',
                cuerpo=f'{request.user.get_full_name() or request.user.username} culminó la orden — '
                       f'{orden.cliente_nombre} ({orden.barrio}).',
                url=f'/ordenes/orden/{orden.pk}/',
            )
            return redirect('ordenes:detalle', pk=orden.pk)
    else:
        cierre_form = OrdenTrabajoCierreForm(instance=orden)
        lineas_form = LineasOrdenForm()

    return render(request, 'ordenes/cerrar.html', {
        'orden': orden, 'cierre_form': cierre_form, 'lineas_form': lineas_form,
    })


@login_required
def imprimir(request, pk):
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    return render(request, 'ordenes/print/orden_print.html', {
        'orden': orden,
        'lineas': {linea.concepto: linea for linea in orden.lineas.all()},
        'conceptos': OrdenTrabajoLinea.Concepto.choices,
    })


@rol_requerido('JEFE_OPERACIONES')
def buscar(request):
    ordenes = OrdenTrabajo.objects.select_related('tecnico', 'creado_por')

    texto = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    tipo_servicio = request.GET.get('tipo_servicio', '')
    desde = request.GET.get('desde', '')
    hasta = request.GET.get('hasta', '')

    if texto:
        digitos = ''.join(ch for ch in texto if ch.isdigit())
        condiciones = (
            Q(cliente_nombre__icontains=texto)
            | Q(cliente_codigo__icontains=texto)
            | Q(barrio__icontains=texto)
            | Q(telefono__icontains=texto)
        )
        if digitos:
            condiciones |= Q(numero=int(digitos))
        ordenes = ordenes.filter(condiciones).distinct()

    if estado in OrdenTrabajo.Estado.values:
        ordenes = ordenes.filter(estado=estado)
    if tipo_servicio in OrdenTrabajo.TipoServicio.values:
        ordenes = ordenes.filter(tipo_servicio=tipo_servicio)

    try:
        if desde:
            ordenes = ordenes.filter(fecha__gte=desde)
        if hasta:
            ordenes = ordenes.filter(fecha__lte=hasta)
    except (ValidationError, ValueError):
        messages.error(request, 'La fecha ingresada no es válida.')

    paginador = Paginator(ordenes, 25)
    pagina = paginador.get_page(request.GET.get('pagina'))

    parametros = request.GET.copy()
    parametros.pop('pagina', None)

    return render(request, 'ordenes/buscar.html', {
        'pagina': pagina,
        'q': texto,
        'estado': estado,
        'tipo_servicio': tipo_servicio,
        'desde': desde,
        'hasta': hasta,
        'querystring': parametros.urlencode(),
        'estados': OrdenTrabajo.Estado,
        'tipos_servicio': OrdenTrabajo.TipoServicio,
        'hay_filtros': bool(texto or estado or tipo_servicio or desde or hasta),
    })
