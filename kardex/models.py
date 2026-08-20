from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


NUMERO_INICIAL = 5850


class NumeroSecuencia(models.Model):
    """Contador consecutivo independiente por tipo de documento (EA, SA, ...)."""

    tipo = models.CharField(max_length=5, unique=True)
    ultimo_numero = models.PositiveIntegerField(default=NUMERO_INICIAL - 1)

    def __str__(self):
        return f'{self.tipo}: {self.ultimo_numero}'

    @classmethod
    def siguiente_numero(cls, tipo):
        with transaction.atomic():
            secuencia, _ = cls.objects.select_for_update().get_or_create(
                tipo=tipo, defaults={'ultimo_numero': NUMERO_INICIAL - 1}
            )
            secuencia.ultimo_numero += 1
            secuencia.save(update_fields=['ultimo_numero'])
            return secuencia.ultimo_numero


class KardexDocumento(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'EA', 'Entrada de Almacén'
        SALIDA = 'SA', 'Salida de Almacén'

    class Estado(models.TextChoices):
        ABIERTO = 'ABIERTO', 'Abierto'
        RECHAZADO = 'RECHAZADO', 'Rechazado por Auxiliar Contable'
        APROBADO = 'APROBADO', 'Aprobado automáticamente (pendiente revisión contable)'
        REVISADO = 'REVISADO', 'Revisado'

    tipo = models.CharField(max_length=2, choices=Tipo.choices)
    numero = models.PositiveIntegerField()
    fecha = models.DateField(default=timezone.localdate)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTO)

    # Campo 1: "Proveedor:" en Entrada / "Entregado a:" en Salida
    parte = models.CharField(max_length=255, blank=True)
    # Campo 2: "Factura:" en Entrada / "Solicitud No.:" en Salida
    referencia = models.CharField(max_length=100, blank=True)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='kardex_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    fecha_envio = models.DateTimeField(null=True, blank=True)

    # La aprobación de Jefe de Operaciones quedó automática (ver cerrar_enviar en views.py):
    # se asigna solo, sin que nadie haga clic, al único usuario con rol Jefe de Operaciones —
    # pero su firma sí se estampa en la impresión, como si hubiera aprobado él mismo.
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='kardex_aprobados'
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)

    rechazado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='kardex_rechazados'
    )
    fecha_rechazo = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True)

    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='kardex_revisados'
    )
    fecha_revision = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tipo', 'fecha'], name='un_documento_por_dia_y_tipo'),
            models.UniqueConstraint(fields=['tipo', 'numero'], name='numero_unico_por_tipo'),
        ]
        ordering = ['-fecha', '-numero']

    def __str__(self):
        return self.numero_formateado

    @property
    def numero_formateado(self):
        return f'{self.tipo}-{self.numero:04d}'

    @property
    def titulo(self):
        return 'ENTRADA DE ALMACÉN' if self.tipo == self.Tipo.ENTRADA else 'SALIDA DE ALMACÉN'

    @property
    def etiqueta_parte(self):
        return 'Proveedor:' if self.tipo == self.Tipo.ENTRADA else 'Entregado a:'

    @property
    def etiqueta_referencia(self):
        return 'Factura:' if self.tipo == self.Tipo.ENTRADA else 'Solicitud No.:'

    @property
    def total_importe(self):
        return self.lineas.aggregate(total=models.Sum('importe'))['total'] or 0

    def puede_agregar_linea(self):
        return self.estado in (self.Estado.ABIERTO,)

    def puede_enviar(self):
        return self.estado == self.Estado.ABIERTO and self.lineas.exists()

    def puede_corregir(self):
        return self.estado == self.Estado.RECHAZADO

    def puede_revisar(self):
        return self.estado == self.Estado.APROBADO

    def puede_rechazar(self):
        return self.estado == self.Estado.APROBADO

    def puede_editar_lineas(self, usuario):
        """Bodeguero corrige mientras está Abierto; Auxiliar Contable (o Admin) corrige
        mientras está Aprobado, antes de marcarlo como Revisado o rechazarlo."""
        if usuario.es_admin():
            return self.estado in (self.Estado.ABIERTO, self.Estado.APROBADO)
        if usuario.rol == 'BODEGUERO':
            return self.estado == self.Estado.ABIERTO
        if usuario.rol == 'AUX_CONTABLE':
            return self.estado == self.Estado.APROBADO
        return False


class KardexLinea(models.Model):
    documento = models.ForeignKey(KardexDocumento, on_delete=models.CASCADE, related_name='lineas')
    orden = models.PositiveIntegerField(default=0)

    clasif = models.CharField('Clasif.', max_length=20, blank=True)
    loc_e = models.CharField('E', max_length=5, blank=True)
    loc_l = models.CharField('L', max_length=5, blank=True)
    loc_c = models.CharField('C', max_length=5, blank=True)
    descripcion = models.CharField('Descripción', max_length=255)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unidad = models.CharField('Unidad', max_length=30, blank=True)
    precio_unitario = models.DecimalField('Precio Unit.', max_digits=12, decimal_places=2, null=True, blank=True)
    importe = models.DecimalField('Importe', max_digits=12, decimal_places=2, null=True, blank=True)
    # Solo aplica a Salida: quién se lleva ese material específico (puede variar por línea/técnico).
    entregado_a = models.CharField('Entregado a', max_length=255, blank=True)

    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'id']

    def __str__(self):
        return f'{self.documento.numero_formateado} - {self.descripcion}'
