from django.core.management.base import BaseCommand

from config.vapid_utils import generar_par_claves


class Command(BaseCommand):
    help = (
        'Genera un par de claves VAPID nuevo para notificaciones push, listo para pegar en tu '
        '.env de producción (VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY). No toca las claves que ya '
        'estén en uso — si defines estas variables, las suscripciones existentes seguirán '
        'funcionando; si generas unas nuevas, los navegadores ya suscritos deberán volver a '
        'activar las notificaciones.'
    )

    def handle(self, *args, **options):
        clave_publica, clave_privada = generar_par_claves()
        privada_una_linea = clave_privada.replace('\n', '\\n')
        self.stdout.write(self.style.SUCCESS('Claves VAPID generadas. Pégalas en tu .env:'))
        self.stdout.write('')
        self.stdout.write(f'VAPID_PUBLIC_KEY={clave_publica}')
        self.stdout.write(f'VAPID_PRIVATE_KEY={privada_una_linea}')
        self.stdout.write('VAPID_CLAIM_EMAIL=mailto:admin@blutesa.local')
