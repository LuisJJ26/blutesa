from django.conf import settings
from django.db import models
from django.utils import timezone

from kardex.models import NumeroSecuencia

TIPO_ORDEN = 'OT'


class OrdenTrabajo(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de ejecutar'
        CERRADA = 'CERRADA', 'Cerrada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    class TipoServicio(models.TextChoices):
        INSTALACION = 'INSTALACION', 'Instalación'
        REPARACION = 'REPARACION', 'Reparación'
        RECONEXION = 'RECONEXION', 'Reconexión'
        TRASLADO = 'TRASLADO', 'Traslado'
        RETIRO = 'RETIRO', 'Retiro de equipos'
        INSPECCION = 'INSPECCION', 'Inspección técnica'
        DERECHO_EXTENSION = 'DERECHO_EXTENSION', 'Derecho de Extensión'
        OTRO = 'OTRO', 'Otro'

    class SiNo(models.TextChoices):
        SI = 'SI', 'Sí'
        NO = 'NO', 'No'

    numero = models.PositiveIntegerField(unique=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha = models.DateField(default=timezone.localdate)

    # --- Cabecera (la digita el Jefe de Operaciones al recibir al cliente, viene del papel) ---
    cliente_nombre = models.CharField('Nombres y Apellidos', max_length=255)
    cliente_codigo = models.CharField('Código de cliente', max_length=50, blank=True)
    barrio = models.CharField(max_length=150, blank=True)
    direccion = models.CharField('Dirección', max_length=255, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    tipo_servicio = models.CharField(max_length=20, choices=TipoServicio.choices)
    tipo_servicio_detalle = models.CharField(
        'Detalle del tipo de servicio', max_length=255, blank=True,
        help_text='Obligatorio si el tipo de servicio es "Otro".',
    )
    observaciones = models.TextField(blank=True)

    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='ordenes_asignadas', limit_choices_to={'rol': 'TECNICO'},
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ordenes_creadas',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # --- Detalle del trabajo a realizar (lo completa el Técnico al cerrar) ---
    reparado = models.CharField(max_length=2, choices=SiNo.choices, blank=True)
    nota_debito_aplica = models.BooleanField('Aplica Nota de Débito', default=False)
    nota_debito_numero = models.CharField('No. de Nota de Débito', max_length=50, blank=True)

    posibilidad_tecnica = models.CharField(max_length=2, choices=SiNo.choices, blank=True)
    tenia_cable_anteriormente = models.CharField(max_length=2, choices=SiNo.choices, blank=True)
    nombre_anterior = models.CharField('A Nombre de Quién', max_length=255, blank=True)
    fecha_elaboracion = models.DateField('Fecha de Elaboración del Trabajo', null=True, blank=True)

    # --- Georreferencia del cierre (RF-OT-06 / RF-OT-14, simplificado a un solo evento: el cierre) ---
    gps_lat = models.FloatField(null=True, blank=True)
    gps_lng = models.FloatField(null=True, blank=True)
    gps_precision_m = models.FloatField(null=True, blank=True)
    sin_georreferencia = models.BooleanField(default=False)
    motivo_sin_gps = models.CharField(max_length=255, blank=True)

    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='ordenes_cerradas',
    )
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    # La autorización del Jefe de Operaciones queda automática al cerrar (mismo criterio que
    # `KardexDocumento.aprobado_por` en kardex/models.py): no hace falta que él haga clic en
    # nada, pero su firma sí se estampa en la impresión como "Autorizado Por", igual que si
    # hubiera revisado y aprobado él mismo.
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='ordenes_autorizadas',
    )
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha', '-numero']

    def __str__(self):
        return self.numero_formateado

    @property
    def numero_formateado(self):
        return f'OT-{self.numero:05d}'

    def puede_cerrar(self, usuario):
        if self.estado != self.Estado.PENDIENTE:
            return False
        if usuario.es_admin():
            return True
        return usuario.rol == 'TECNICO' and self.tecnico_id == usuario.id

    def puede_cancelar(self, usuario):
        return self.estado == self.Estado.PENDIENTE and (
            usuario.es_admin() or usuario.rol == 'JEFE_OPERACIONES'
        )


class OrdenTrabajoLinea(models.Model):
    class Concepto(models.TextChoices):
        INSTALACION = 'INSTALACION', 'Instalación'
        CABLE = 'CABLE', 'Cable'
        CONECTORES = 'CONECTORES', 'Conectores'
        SPLITTER = 'SPLITTER', 'Splitter'
        PUENTE = 'PUENTE', 'Puente'
        CABLE_EXTRA = 'CABLE_EXTRA', 'Cable Extra'
        CONECTORES_EXTRA = 'CONECTORES_EXTRA', 'Conec. Extra'
        SPLITTER_EXTRA = 'SPLITTER_EXTRA', 'Splitter Extra'
        PUENTE_EXTRA = 'PUENTE_EXTRA', 'Puente Extra'

    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name='lineas')
    concepto = models.CharField(max_length=20, choices=Concepto.choices)
    fecha = models.DateField(null=True, blank=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['orden', 'concepto'], name='concepto_unico_por_orden'),
        ]

    def __str__(self):
        return f'{self.orden.numero_formateado} — {self.get_concepto_display()}'


class OrdenTrabajoFoto(models.Model):
    """Evidencia fotográfica del trabajo realizado. Basta con una foto por orden, pero se
    permite más de una por si el técnico quiere agregar otra."""

    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name='fotos')
    ruta_nextcloud = models.CharField(max_length=500)
    url_publica = models.URLField(max_length=500, blank=True)
    subida_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    subida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.orden.numero_formateado} — foto'
