from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

FIRMA_TAMANO_MAXIMO_MB = 3


def validar_tamano_firma(archivo):
    limite = FIRMA_TAMANO_MAXIMO_MB * 1024 * 1024
    if archivo.size > limite:
        raise ValidationError(f'La imagen no puede pesar más de {FIRMA_TAMANO_MAXIMO_MB} MB.')


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        BODEGUERO = 'BODEGUERO', 'Bodeguero'
        JEFE_OPERACIONES = 'JEFE_OPERACIONES', 'Jefe de Operaciones'
        AUX_CONTABLE = 'AUX_CONTABLE', 'Auxiliar Contable'
        TECNICO = 'TECNICO', 'Técnico'
        ADMIN = 'ADMIN', 'Administrador'

    rol = models.CharField(max_length=20, choices=Rol.choices)
    firma = models.ImageField(upload_to='firmas/', blank=True, null=True, validators=[validar_tamano_firma])

    def es_admin(self):
        return self.rol == self.Rol.ADMIN or self.is_superuser

    def __str__(self):
        return self.get_full_name() or self.username


class SuscripcionPush(models.Model):
    """Un endpoint de notificaciones push por dispositivo/navegador de un usuario."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='suscripciones_push')
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    navegador = models.CharField(max_length=255, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.usuario} — {self.navegador or self.endpoint[:40]}'
