import os
import re

from django.core.management.base import BaseCommand, CommandError

from clientes.models import Cliente

RUTA_POR_DEFECTO = os.path.expanduser('~/Downloads/MAESTRO.DBF')
TAMANO_LOTE = 500

# Primero busca un número justo después de "TEL"/"CEL" (más confiable, casi siempre
# es el teléfono del cliente); si no hay, cae a buscar cualquier corrida de 7-8 dígitos
# sueltos en la dirección (la mayoría de las direcciones traen el teléfono así, sin
# prefijo). En ambos casos toma solo UN número — si hay varios separados por coma o
# guión (líneas alternas), se queda con el primero después del prefijo, o el último
# de los sueltos.
PATRON_TELEFONO_PREFIJO = re.compile(r'(?:TEL|CEL)[:.\s#]*(\d{5,8})', re.IGNORECASE)
PATRON_TELEFONO_SUELTO = re.compile(r'(?<!\d)(\d{7,8})(?!\d)')


def extraer_telefono(direccion):
    if not direccion:
        return ''
    coincidencia = PATRON_TELEFONO_PREFIJO.search(direccion)
    if coincidencia:
        return coincidencia.group(1)
    sueltos = PATRON_TELEFONO_SUELTO.findall(direccion)
    return sueltos[-1] if sueltos else ''


class Command(BaseCommand):
    help = (
        'Importa (o actualiza) el maestro de clientes desde MAESTRO.DBF del sistema viejo '
        '(BLUFIELDS TELEVICABLE). No copia el .dbf al repo — lo lee directo de su ubicación. '
        'Uso: importar_clientes_dbf [--archivo RUTA]'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo', default=RUTA_POR_DEFECTO,
            help=f'Ruta al .dbf (por defecto: {RUTA_POR_DEFECTO})',
        )

    def handle(self, *args, **options):
        try:
            from dbfread import DBF
        except ImportError:
            raise CommandError('Falta la librería dbfread. Instálala con: pip install dbfread')

        ruta = options['archivo']
        if not os.path.isfile(ruta):
            raise CommandError(f'No se encontró el archivo: {ruta}')

        # cp850, no latin-1/utf-8: es la codificación de página de códigos que usaba
        # el sistema DOS/Clipper original para acentos y la ñ.
        tabla = DBF(ruta, encoding='cp850', ignore_missing_memofile=True)

        creados = 0
        actualizados = 0
        omitidos = 0
        lote = []

        def volcar_lote():
            nonlocal lote
            if not lote:
                return
            Cliente.objects.bulk_create(
                lote,
                update_conflicts=True,
                unique_fields=['codigo'],
                update_fields=[
                    'contrato', 'nombre', 'apellido1', 'apellido2', 'barrio', 'direccion',
                    'telefono', 'activo', 'fecha_instalacion', 'fecha_desconexion',
                    'fecha_desconexion_parcial', 'observaciones',
                ],
            )
            lote = []

        codigos_existentes = set(Cliente.objects.values_list('codigo', flat=True))

        for registro in tabla:
            codigo = (registro.get('MA_CONS') or '').strip()
            if not codigo:
                omitidos += 1
                continue

            direccion = (registro.get('MA_DIREC') or '').strip()

            lote.append(Cliente(
                codigo=codigo,
                contrato=(registro.get('CONTRAT') or '').strip(),
                nombre=(registro.get('MA_NOMBRE') or '').strip(),
                apellido1=(registro.get('MA_APELL1') or '').strip(),
                apellido2=(registro.get('MA_APELL2') or '').strip(),
                barrio=(registro.get('MA_BARRIO') or '').strip(),
                direccion=direccion,
                telefono=extraer_telefono(direccion),
                activo=(registro.get('MA_CLI_ACT') or '').strip().upper() == 'SI',
                fecha_instalacion=registro.get('MA_F_INT') or None,
                fecha_desconexion=registro.get('MA_DESCO') or None,
                fecha_desconexion_parcial=registro.get('MA_DESCO_D') or None,
                observaciones=(registro.get('OBSERVA') or '').strip(),
            ))

            if codigo in codigos_existentes:
                actualizados += 1
            else:
                creados += 1

            if len(lote) >= TAMANO_LOTE:
                volcar_lote()

        volcar_lote()

        self.stdout.write(self.style.SUCCESS(
            f'Importación completa: {creados} clientes nuevos, {actualizados} actualizados, '
            f'{omitidos} omitidos (sin código).'
        ))
