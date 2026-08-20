import json
import logging

from django.conf import settings

from .models import SuscripcionPush

logger = logging.getLogger(__name__)


def enviar_push(usuarios, titulo, cuerpo, url='/'):
    """Envía una notificación push a todas las suscripciones de los usuarios dados.

    Si pywebpush no está instalado, o no hay claves VAPID configuradas, no hace nada
    (el resto de la app sigue funcionando igual, sin notificaciones).
    """
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return

    try:
        from py_vapid import Vapid
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning('pywebpush no está instalado; no se enviaron notificaciones push.')
        return

    # OJO: pywebpush acepta un string como vapid_private_key, pero internamente lo pasa
    # a Vapid.from_string(), que NO sabe quitarle los encabezados "-----BEGIN...-----" a un
    # PEM (solo le quita saltos de línea) y truena con "invalid length". Por eso construimos
    # el objeto Vapid nosotros mismos con from_pem(), que sí los quita correctamente.
    try:
        vapid_instance = Vapid.from_pem(settings.VAPID_PRIVATE_KEY.encode())
    except Exception:
        logger.exception('La clave privada VAPID configurada no es válida; no se envían push.')
        return

    payload = json.dumps({'titulo': titulo, 'cuerpo': cuerpo, 'url': url})
    suscripciones = SuscripcionPush.objects.filter(usuario__in=usuarios)

    for suscripcion in suscripciones:
        try:
            webpush(
                subscription_info={
                    'endpoint': suscripcion.endpoint,
                    'keys': {'p256dh': suscripcion.p256dh, 'auth': suscripcion.auth},
                },
                data=payload,
                vapid_private_key=vapid_instance,
                vapid_claims={'sub': settings.VAPID_CLAIM_EMAIL},
            )
        except WebPushException as error:
            respuesta = getattr(error, 'response', None)
            if respuesta is not None and respuesta.status_code in (404, 410):
                # El navegador invalidó esa suscripción (desinstaló, borró datos, etc).
                suscripcion.delete()
            else:
                logger.warning('No se pudo enviar push a %s: %s', suscripcion.usuario, error)
        except Exception:
            # Nunca dejamos que un fallo de notificación (red caída, endpoint raro, etc.)
            # reviente la acción real (cerrar/aprobar/rechazar/revisar un documento).
            logger.exception('Error inesperado enviando push a %s', suscripcion.usuario)
