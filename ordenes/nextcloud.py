"""Sube evidencia (fotos del trabajo realizado) al Nextcloud de la empresa por WebDAV, en vez de
guardarla en el servidor de esta app. El Nextcloud real solo es accesible por VPN, así que en
desarrollo local (o si las variables de entorno no están configuradas) se cae de forma automática
a guardar el archivo en el almacenamiento local de Django — mismo criterio que ya usan las claves
VAPID de este proyecto (funciona sin configurar nada en local; en producción hace falta el .env).
"""
import uuid
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.files.storage import default_storage


class SubidaNextcloudError(Exception):
    """La subida a Nextcloud falló (red, credenciales, permisos, etc.)."""


def _configurado():
    return bool(settings.NEXTCLOUD_WEBDAV_URL and settings.NEXTCLOUD_USERNAME and settings.NEXTCLOUD_APP_PASSWORD)


def _nombre_unico(nombre_original):
    extension = ''
    if '.' in nombre_original:
        extension = '.' + nombre_original.rsplit('.', 1)[-1].lower()
    return f'{uuid.uuid4().hex}{extension}'


def _subir_webdav(nombre, contenido, content_type):
    base_url = settings.NEXTCLOUD_WEBDAV_URL.rstrip('/')
    carpeta = settings.NEXTCLOUD_UPLOAD_FOLDER.strip('/')
    auth = (settings.NEXTCLOUD_USERNAME, settings.NEXTCLOUD_APP_PASSWORD)

    # Crea la carpeta si no existe todavía (MKCOL sobre una carpeta existente solo responde 405,
    # no es un error real).
    requests.request('MKCOL', f'{base_url}/{quote(carpeta)}', auth=auth, timeout=10)

    ruta = f'{carpeta}/{nombre}'
    respuesta = requests.put(
        f'{base_url}/{quote(ruta)}',
        data=contenido,
        auth=auth,
        headers={'Content-Type': content_type or 'application/octet-stream'},
        timeout=30,
    )
    if respuesta.status_code not in (200, 201, 204):
        raise SubidaNextcloudError(f'Nextcloud respondió {respuesta.status_code} al subir {nombre}.')
    return ruta


def _crear_enlace_publico(ruta):
    """Genera un link público de solo lectura vía la OCS Share API. Si falla, no es fatal —
    el archivo ya quedó guardado en Nextcloud, simplemente no habrá vista previa embebida."""
    base_url = settings.NEXTCLOUD_WEBDAV_URL.rstrip('/')
    # NEXTCLOUD_WEBDAV_URL tiene forma .../remote.php/dav/files/<usuario> — la Share API vive
    # en la raíz del servidor, no bajo /remote.php/dav.
    raiz = base_url.split('/remote.php/')[0]
    auth = (settings.NEXTCLOUD_USERNAME, settings.NEXTCLOUD_APP_PASSWORD)
    try:
        respuesta = requests.post(
            f'{raiz}/ocs/v2.php/apps/files_sharing/api/v1/shares',
            auth=auth,
            headers={'OCS-APIRequest': 'true'},
            data={'path': f'/{ruta}', 'shareType': 3, 'permissions': 1},
            timeout=15,
        )
        respuesta.raise_for_status()
        import xml.etree.ElementTree as ET
        url = ET.fromstring(respuesta.content).findtext('.//url')
        return url or ''
    except Exception:
        return ''


def subir_evidencia(nombre_original, contenido_bytes, content_type, subcarpeta):
    """Sube bytes crudos (una foto) y devuelve (ruta_o_path, url_publica).

    Si Nextcloud no está configurado (desarrollo local), lo guarda con el storage local de
    Django bajo media/ordenes_evidencia_DEV_SIN_NEXTCLOUD/ y devuelve esa ruta como si fuera la
    "ruta remota" — dejando clara la diferencia en el nombre de carpeta para no confundirlo con
    producción real.
    """
    from django.core.files.base import ContentFile

    nombre = _nombre_unico(nombre_original)

    if not _configurado():
        ruta_local = default_storage.save(
            f'ordenes_evidencia_DEV_SIN_NEXTCLOUD/{subcarpeta}/{nombre}', ContentFile(contenido_bytes)
        )
        return ruta_local, default_storage.url(ruta_local)

    ruta = _subir_webdav(f'{subcarpeta}/{nombre}', contenido_bytes, content_type)
    url_publica = _crear_enlace_publico(ruta)
    return ruta, url_publica
