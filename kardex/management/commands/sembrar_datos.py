import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from kardex.models import KardexDocumento, NumeroSecuencia

Usuario = get_user_model()

EQUIPO = [
    dict(username='luis', prefix='LUIS', rol='ADMIN', is_staff=True, is_superuser=True),
    dict(username='daymalis', prefix='DAYMALIS', rol='AUX_CONTABLE'),
    dict(username='julio', prefix='JULIO', rol='BODEGUERO'),
    dict(username='elmer', prefix='ELMER', rol='JEFE_OPERACIONES'),
]


class Command(BaseCommand):
    help = (
        'Crea los usuarios iniciales del equipo (uno por rol) y siembra la numeración inicial '
        'para EA y SA. Nombre y contraseña se leen de variables de entorno por prefijo '
        '(<PREFIJO>_PASSWORD, <PREFIJO>_NOMBRE, <PREFIJO>_APELLIDO) — nada de datos personales '
        'hardcodeados en el código.'
    )

    def handle(self, *args, **options):
        for datos in EQUIPO:
            datos = dict(datos)
            username = datos.pop('username')
            prefix = datos.pop('prefix')

            if Usuario.objects.filter(username=username).exists():
                self.stdout.write(f'Usuario ya existía: {username}')
                continue

            password = os.environ.get(f'{prefix}_PASSWORD')
            if not password:
                self.stdout.write(self.style.WARNING(
                    f'Omitido "{username}": falta la variable de entorno {prefix}_PASSWORD'
                ))
                continue

            datos['first_name'] = os.environ.get(f'{prefix}_NOMBRE', '')
            datos['last_name'] = os.environ.get(f'{prefix}_APELLIDO', '')

            usuario = Usuario.objects.create(username=username, **datos)
            usuario.set_password(password)
            usuario.save()
            self.stdout.write(self.style.SUCCESS(f'Usuario creado: {username}'))

        for tipo in KardexDocumento.Tipo.values:
            secuencia, creada = NumeroSecuencia.objects.get_or_create(tipo=tipo)
            if creada:
                self.stdout.write(self.style.SUCCESS(
                    f'Numeración {tipo} sembrada: el próximo documento será {tipo}-{secuencia.ultimo_numero + 1}'
                ))
            else:
                self.stdout.write(f'Numeración {tipo} ya existía (último: {secuencia.ultimo_numero})')
