from django.db import models

from .barrios import nombre_barrio


class Cliente(models.Model):
    """Maestro de clientes de Cable/TV heredado del sistema viejo (MAESTRO.DBF).

    Se usa solo para búsqueda/autocompletado al crear una Orden de Trabajo — no es un
    módulo de facturación. `codigo` es el identificador único del sistema viejo (ej.
    "HEB-WOO-000000-1201"); `contrato` es el número corto que también aparece ahí.
    """

    codigo = models.CharField('Código', max_length=50, unique=True)
    contrato = models.CharField('Contrato', max_length=20, blank=True, db_index=True)
    nombre = models.CharField(max_length=150, blank=True)
    apellido1 = models.CharField(max_length=100, blank=True)
    apellido2 = models.CharField(max_length=100, blank=True)
    barrio = models.CharField('Código de barrio', max_length=150, blank=True, db_index=True)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    activo = models.BooleanField(default=False, db_index=True)
    fecha_instalacion = models.DateField(null=True, blank=True)
    fecha_desconexion = models.DateField('Fecha de desconexión', null=True, blank=True)
    fecha_desconexion_parcial = models.DateField('Fecha de desconexión parcial', null=True, blank=True)
    observaciones = models.CharField(max_length=255, blank=True)

    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre', 'apellido1']
        indexes = [
            models.Index(fields=['nombre', 'apellido1']),
        ]

    def __str__(self):
        return f'{self.nombre_completo} ({self.codigo})'

    @property
    def nombre_completo(self):
        return ' '.join(parte for parte in [self.nombre, self.apellido1, self.apellido2] if parte)

    @property
    def barrio_nombre(self):
        return nombre_barrio(self.barrio)


class ClienteFibra(models.Model):
    """Maestro de clientes de Internet (fibra/inalámbrico) desde CLIENTES INTERNET.xlsx.

    A diferencia de Cliente (cable/TV), aquí `barrio` viene como texto libre del propio
    Excel (no hay un código de 2 dígitos que mapear) y sí incluye datos técnicos del
    equipo instalado (PON/ONU/serie/modelo) — no incluye historial de pagos, eso queda
    fuera de este módulo por ahora.
    """

    class Tipo(models.TextChoices):
        CABLE = 'CABLE', 'Internet por Cable'
        INALAMBRICO_5G = '5G', 'Internet Inalámbrico 5G'

    tipo = models.CharField(max_length=10, choices=Tipo.choices, db_index=True)
    ip = models.GenericIPAddressField('IP asignada', null=True, blank=True)
    nombre = models.CharField(max_length=200, blank=True)
    cedula = models.CharField('Cédula', max_length=30, blank=True, db_index=True)
    barrio = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=50, blank=True)

    pon = models.PositiveSmallIntegerField('PON', null=True, blank=True)
    onu_id = models.PositiveSmallIntegerField('ID de ONU', null=True, blank=True)
    serie = models.CharField('N° de Serie', max_length=50, blank=True)
    modelo = models.CharField(max_length=50, blank=True)
    bw_mbps = models.PositiveSmallIntegerField('Ancho de banda (Mbps)', null=True, blank=True)

    costo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    costo_nota = models.CharField(
        'Nota de costo', max_length=50, blank=True,
        help_text='Para casos como "SOCIO" que no son un monto en córdobas.',
    )
    fecha_activacion = models.DateField(null=True, blank=True)

    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cliente de fibra/internet'
        verbose_name_plural = 'Clientes de fibra/internet'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre']),
        ]
        constraints = [
            # La IP asignada (columna "Total de BW" del Excel, mal rotulada) es la llave
            # natural de cada fila en el Excel original — se usa para poder re-importar
            # sin duplicar filas.
            models.UniqueConstraint(fields=['tipo', 'ip'], name='ip_unica_por_tipo'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.get_tipo_display()})'
