from collections import Counter
from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_GET

from accounts.push import enviar_push

from .forms import KardexCabeceraForm, KardexLineaForm, RechazoForm
from .models import KardexDocumento, KardexLinea, NumeroSecuencia

Usuario = get_user_model()

MESES_ES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]


def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            usuario = request.user
            if usuario.es_admin() or usuario.rol in roles:
                return vista(request, *args, **kwargs)
            messages.error(request, 'No tienes permiso para realizar esta acción.')
            return redirect('inicio')
        return envoltura
    return decorador


@login_required
def inicio(request):
    rol = request.user.rol
    if rol == 'BODEGUERO':
        return redirect('kardex:panel_bodega')
    if rol == 'JEFE_OPERACIONES':
        return redirect('kardex:panel_jefe')
    if rol == 'AUX_CONTABLE':
        return redirect('kardex:panel_contable')
    if rol == 'TECNICO':
        return redirect('ordenes:panel_tecnico')
    return redirect('kardex:panel_admin')


@rol_requerido('BODEGUERO')
def panel_bodega(request):
    hoy = timezone.localdate()
    documentos_hoy = {}
    for tipo in KardexDocumento.Tipo.values:
        documentos_hoy[tipo] = KardexDocumento.objects.filter(tipo=tipo, fecha=hoy).first()

    recientes = KardexDocumento.objects.exclude(fecha=hoy)[:15]

    return render(request, 'kardex/panel_bodega.html', {
        'documentos_hoy': documentos_hoy,
        'tipos': KardexDocumento.Tipo,
        'recientes': recientes,
    })


@rol_requerido('BODEGUERO')
def abrir_hoy(request, tipo):
    if tipo not in KardexDocumento.Tipo.values:
        raise Http404
    if request.method != 'POST':
        return redirect('kardex:panel_bodega')
    hoy = timezone.localdate()
    documento = KardexDocumento.objects.filter(tipo=tipo, fecha=hoy).first()
    if documento is None:
        try:
            numero = NumeroSecuencia.siguiente_numero(tipo)
            documento = KardexDocumento.objects.create(
                tipo=tipo, numero=numero, fecha=hoy, creado_por=request.user
            )
        except IntegrityError:
            # Dos peticiones simultáneas abriendo el mismo día: la otra ya ganó.
            documento = KardexDocumento.objects.get(tipo=tipo, fecha=hoy)
    return redirect('kardex:detalle', pk=documento.pk)


@rol_requerido('BODEGUERO', 'JEFE_OPERACIONES', 'AUX_CONTABLE')
def detalle(request, pk):
    documento = get_object_or_404(KardexDocumento, pk=pk)
    usuario = request.user

    if usuario.rol == 'JEFE_OPERACIONES':
        # Jefe de Operaciones ya no aprueba ni edita nada a mano — solo ve el historial
        # como control. Se le renderiza una plantilla propia, sin ningún form de acción,
        # en vez de confiar en que cada flag de la plantilla completa evalúe False.
        return render(request, 'kardex/detalle_lectura.html', {
            'documento': documento,
            'lineas': documento.lineas.all(),
        })

    linea_form = None
    cabecera_form = None
    rechazo_form = None

    puede_gestionar_cabecera = documento.puede_agregar_linea() and (
        usuario.es_admin() or usuario.rol == 'BODEGUERO'
    )
    if puede_gestionar_cabecera:
        cabecera_form = KardexCabeceraForm(instance=documento)
        linea_form = KardexLineaForm(tipo=documento.tipo)

    puede_editar_lineas = documento.puede_editar_lineas(usuario)

    puede_rechazar_ahora = documento.puede_rechazar() and (
        usuario.es_admin() or usuario.rol == 'AUX_CONTABLE'
    )
    if puede_rechazar_ahora:
        rechazo_form = RechazoForm()

    puede_corregir_ahora = documento.puede_corregir() and (
        usuario.es_admin() or usuario.rol == 'BODEGUERO'
    )
    puede_revisar_ahora = documento.puede_revisar() and (
        usuario.es_admin() or usuario.rol == 'AUX_CONTABLE'
    )

    return render(request, 'kardex/detalle.html', {
        'documento': documento,
        'lineas': documento.lineas.all(),
        'linea_form': linea_form,
        'cabecera_form': cabecera_form,
        'rechazo_form': rechazo_form,
        'puede_gestionar_cabecera': puede_gestionar_cabecera,
        'puede_editar_lineas': puede_editar_lineas,
        'puede_corregir_ahora': puede_corregir_ahora,
        'puede_rechazar_ahora': puede_rechazar_ahora,
        'puede_revisar_ahora': puede_revisar_ahora,
    })


@rol_requerido('BODEGUERO')
def agregar_linea(request, pk):
    documento = get_object_or_404(KardexDocumento, pk=pk)
    if request.method == 'POST' and documento.puede_agregar_linea():
        form = KardexLineaForm(request.POST, tipo=documento.tipo)
        if form.is_valid():
            linea = form.save(commit=False)
            linea.documento = documento
            linea.orden = documento.lineas.count() + 1
            linea.save()
            messages.success(request, 'Línea agregada.')
        else:
            messages.error(request, 'Revisa los datos de la línea.')
    return redirect('kardex:detalle', pk=pk)


@rol_requerido('BODEGUERO', 'AUX_CONTABLE')
def editar_linea(request, pk, linea_pk):
    documento = get_object_or_404(KardexDocumento, pk=pk)
    linea = get_object_or_404(KardexLinea, pk=linea_pk, documento=documento)

    if not documento.puede_editar_lineas(request.user):
        messages.error(request, 'Este documento no se puede editar en su estado actual.')
        return redirect('kardex:detalle', pk=pk)

    if request.method == 'POST':
        form = KardexLineaForm(request.POST, instance=linea, tipo=documento.tipo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Línea actualizada.')
            return redirect('kardex:detalle', pk=pk)
    else:
        form = KardexLineaForm(instance=linea, tipo=documento.tipo)

    return render(request, 'kardex/linea_editar.html', {
        'documento': documento,
        'linea': linea,
        'form': form,
    })


@rol_requerido('BODEGUERO')
def actualizar_cabecera(request, pk):
    documento = get_object_or_404(KardexDocumento, pk=pk)
    if request.method == 'POST' and documento.puede_agregar_linea():
        form = KardexCabeceraForm(request.POST, instance=documento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos del documento actualizados.')
    return redirect('kardex:detalle', pk=pk)


@rol_requerido('BODEGUERO')
def cerrar_enviar(request, pk):
    documento = get_object_or_404(KardexDocumento, pk=pk)
    if request.method == 'POST' and documento.puede_enviar():
        # La aprobación de Jefe de Operaciones quedó automática: cerrar y enviar pasa
        # directo a Aprobado sin que nadie tenga que hacer clic — pero la firma del rol
        # sí queda estampada, como si hubiera aprobado a mano.
        ahora = timezone.now()
        documento.estado = KardexDocumento.Estado.APROBADO
        documento.fecha_envio = ahora
        documento.aprobado_por = Usuario.objects.filter(rol='JEFE_OPERACIONES').first()
        documento.fecha_aprobacion = ahora
        documento.save(update_fields=['estado', 'fecha_envio', 'aprobado_por', 'fecha_aprobacion'])
        messages.success(
            request,
            f'{documento.numero_formateado} enviado y aprobado automáticamente. '
            'Pendiente de revisión contable.'
        )
        enviar_push(
            Usuario.objects.filter(rol='AUX_CONTABLE'),
            titulo=f'{documento.numero_formateado} pendiente de revisión',
            cuerpo=f'{documento.creado_por} cerró {documento.titulo.lower()}, listo para tu revisión.',
            url=f'/kardex/documento/{documento.pk}/',
        )
    elif request.method == 'POST':
        messages.error(request, 'El documento necesita al menos una línea para poder enviarse.')
    return redirect('kardex:detalle', pk=pk)


@rol_requerido('BODEGUERO')
def corregir(request, pk):
    documento = get_object_or_404(KardexDocumento, pk=pk)
    if request.method == 'POST' and documento.puede_corregir():
        documento.estado = KardexDocumento.Estado.ABIERTO
        documento.save(update_fields=['estado'])
        messages.info(request, 'Documento reabierto para corrección.')
    return redirect('kardex:detalle', pk=pk)


@rol_requerido('JEFE_OPERACIONES')
def panel_jefe(request):
    # Jefe de Operaciones ya no aprueba/rechaza a mano (eso quedó automático) — este panel
    # es solo para que siga viendo lo que se mueve, como control.
    historial = KardexDocumento.objects.all()[:30]
    return render(request, 'kardex/panel_jefe.html', {
        'historial': historial,
    })


@rol_requerido('AUX_CONTABLE')
def rechazar(request, pk):
    documento = get_object_or_404(KardexDocumento, pk=pk)
    if request.method == 'POST' and documento.puede_rechazar():
        form = RechazoForm(request.POST)
        if form.is_valid():
            documento.estado = KardexDocumento.Estado.RECHAZADO
            documento.rechazado_por = request.user
            documento.fecha_rechazo = timezone.now()
            documento.motivo_rechazo = form.cleaned_data['motivo_rechazo']
            documento.save(update_fields=[
                'estado', 'rechazado_por', 'fecha_rechazo', 'motivo_rechazo'
            ])
            messages.info(request, f'{documento.numero_formateado} rechazado.')
            enviar_push(
                [documento.creado_por],
                titulo=f'{documento.numero_formateado} rechazado',
                cuerpo=f'{request.user}: {documento.motivo_rechazo}',
                url=f'/kardex/documento/{documento.pk}/',
            )
        else:
            messages.error(request, 'Debes indicar el motivo del rechazo.')
    return redirect('kardex:detalle', pk=pk)


@rol_requerido('AUX_CONTABLE')
def panel_contable(request):
    pendientes = KardexDocumento.objects.filter(estado=KardexDocumento.Estado.APROBADO)
    historial = KardexDocumento.objects.exclude(estado=KardexDocumento.Estado.APROBADO)[:20]
    return render(request, 'kardex/panel_contable.html', {
        'pendientes': pendientes,
        'historial': historial,
    })


@rol_requerido('AUX_CONTABLE')
def revisar(request, pk):
    documento = get_object_or_404(KardexDocumento, pk=pk)
    if request.method == 'POST' and documento.puede_revisar():
        documento.estado = KardexDocumento.Estado.REVISADO
        documento.revisado_por = request.user
        documento.fecha_revision = timezone.now()
        documento.save(update_fields=['estado', 'revisado_por', 'fecha_revision'])
        messages.success(request, f'{documento.numero_formateado} revisado.')
        enviar_push(
            [documento.creado_por],
            titulo=f'{documento.numero_formateado} revisado',
            cuerpo=f'{request.user} completó la revisión contable. El documento quedó cerrado.',
            url=f'/kardex/documento/{documento.pk}/',
        )
    return redirect('kardex:detalle', pk=pk)


@login_required
def panel_admin(request):
    if not request.user.es_admin():
        messages.error(request, 'No tienes permiso para ver esta página.')
        return redirect('inicio')
    documentos = KardexDocumento.objects.all()[:100]
    return render(request, 'kardex/panel_admin.html', {'documentos': documentos})


@login_required
def imprimir(request, pk):
    documento = get_object_or_404(KardexDocumento, pk=pk)
    plantilla = (
        'kardex/print/kardex_print_salida.html'
        if documento.tipo == KardexDocumento.Tipo.SALIDA
        else 'kardex/print/kardex_print_entrada.html'
    )
    return render(request, plantilla, {
        'documento': documento,
        'lineas': documento.lineas.all(),
    })


@require_GET
def service_worker(request):
    contenido = render_to_string('kardex/sw.js')
    return HttpResponse(contenido, content_type='application/javascript')


@rol_requerido('AUX_CONTABLE')
def informe_mensual(request):
    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get('anio', hoy.year))
        mes = int(request.GET.get('mes', hoy.month))
        if not 1 <= mes <= 12:
            raise ValueError
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month

    documentos = list(
        KardexDocumento.objects.filter(fecha__year=anio, fecha__month=mes)
        .select_related('creado_por', 'aprobado_por', 'revisado_por', 'rechazado_por')
        .order_by('tipo', 'numero')
    )

    resumen_tipo = {
        KardexDocumento.Tipo.ENTRADA: {'cantidad': 0, 'total_importe': Decimal('0')},
        KardexDocumento.Tipo.SALIDA: {'cantidad': 0, 'total_importe': Decimal('0')},
    }
    conteo_estado = Counter()
    for documento in documentos:
        resumen_tipo[documento.tipo]['cantidad'] += 1
        resumen_tipo[documento.tipo]['total_importe'] += documento.total_importe
        conteo_estado[documento.estado] += 1

    mes_anterior, anio_anterior = (12, anio - 1) if mes == 1 else (mes - 1, anio)
    mes_siguiente, anio_siguiente = (1, anio + 1) if mes == 12 else (mes + 1, anio)

    en_tramite = (
        conteo_estado.get(KardexDocumento.Estado.ABIERTO, 0)
        + conteo_estado.get(KardexDocumento.Estado.APROBADO, 0)
    )

    return render(request, 'kardex/informe_mensual.html', {
        'anio': anio,
        'mes': mes,
        'nombre_mes': MESES_ES[mes],
        'documentos': documentos,
        'total_documentos': len(documentos),
        'resumen_entrada': resumen_tipo[KardexDocumento.Tipo.ENTRADA],
        'resumen_salida': resumen_tipo[KardexDocumento.Tipo.SALIDA],
        'conteo_estado': dict(conteo_estado),
        'en_tramite': en_tramite,
        'anio_anterior': anio_anterior,
        'mes_anterior': mes_anterior,
        'anio_siguiente': anio_siguiente,
        'mes_siguiente': mes_siguiente,
        'es_mes_actual': anio == hoy.year and mes == hoy.month,
    })


@login_required
def buscar(request):
    documentos = KardexDocumento.objects.select_related(
        'creado_por', 'aprobado_por', 'revisado_por', 'rechazado_por'
    ).order_by('-fecha', '-numero')

    texto = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')
    desde = request.GET.get('desde', '')
    hasta = request.GET.get('hasta', '')

    if texto:
        digitos = ''.join(ch for ch in texto if ch.isdigit())
        condiciones = (
            Q(creado_por__first_name__icontains=texto)
            | Q(creado_por__last_name__icontains=texto)
            | Q(creado_por__username__icontains=texto)
            | Q(parte__icontains=texto)
            | Q(referencia__icontains=texto)
            | Q(motivo_rechazo__icontains=texto)
        )
        if digitos:
            condiciones |= Q(numero=int(digitos))
        documentos = documentos.filter(condiciones).distinct()

    if tipo in KardexDocumento.Tipo.values:
        documentos = documentos.filter(tipo=tipo)

    if estado in KardexDocumento.Estado.values:
        documentos = documentos.filter(estado=estado)

    try:
        if desde:
            documentos = documentos.filter(fecha__gte=desde)
        if hasta:
            documentos = documentos.filter(fecha__lte=hasta)
    except (ValidationError, ValueError):
        messages.error(request, 'La fecha ingresada no es válida.')

    paginador = Paginator(documentos, 25)
    pagina = paginador.get_page(request.GET.get('pagina'))

    parametros = request.GET.copy()
    parametros.pop('pagina', None)

    return render(request, 'kardex/buscar.html', {
        'pagina': pagina,
        'q': texto,
        'tipo': tipo,
        'estado': estado,
        'desde': desde,
        'hasta': hasta,
        'querystring': parametros.urlencode(),
        'tipos': KardexDocumento.Tipo,
        'estados': KardexDocumento.Estado,
        'hay_filtros': bool(texto or tipo or estado or desde or hasta),
    })
