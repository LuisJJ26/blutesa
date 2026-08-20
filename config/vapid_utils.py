import json
from pathlib import Path


def generar_par_claves():
    """Genera un par de claves VAPID nuevo. Devuelve (clave_publica, clave_privada_pem)."""
    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid02, b64urlencode

    vapid = Vapid02()
    vapid.generate_keys()
    clave_publica_bytes = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return b64urlencode(clave_publica_bytes), vapid.private_pem().decode()


def obtener_o_generar_claves_vapid(base_dir: Path):
    """Devuelve (clave_publica, clave_privada) reutilizando un archivo local si ya existe.

    Solo se usa cuando no se definieron VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY por variable de
    entorno — así el proyecto funciona con notificaciones push sin configurar nada a mano en
    desarrollo, pero sigue permitiendo claves fijas en producción vía .env.
    """
    archivo = Path(base_dir) / '.vapid_keys.json'
    if archivo.exists():
        datos = json.loads(archivo.read_text())
        return datos['public_key'], datos['private_key']

    clave_publica, clave_privada = generar_par_claves()
    archivo.write_text(json.dumps({'public_key': clave_publica, 'private_key': clave_privada}, indent=2))
    return clave_publica, clave_privada
