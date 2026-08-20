#!/bin/sh
# Aplica un paquete de actualización (zip de `git archive`) sobre el deploy bare-metal.
# Uso: sudo ./update.sh /ruta/al/paquete.zip
# Preserva .env, media/ y .venv/ porque esos nunca están dentro del zip (no son parte del repo).
set -eu

APP_DIR=/opt/blutesa-kardex
ZIP="${1:-}"

if [ -z "$ZIP" ]; then
    echo "Uso: $0 ruta/al/paquete.zip"
    exit 1
fi
if [ ! -f "$ZIP" ]; then
    echo "No existe el archivo: $ZIP"
    exit 1
fi

echo "== Deteniendo el servicio =="
systemctl stop blutesa-kardex

echo "== Extrayendo código nuevo sobre $APP_DIR =="
sudo -u blutesa unzip -o "$ZIP" -d "$APP_DIR"

echo "== Instalando/actualizando dependencias =="
sudo -u blutesa "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "== Migrando base de datos =="
sudo -u blutesa "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" migrate --noinput

echo "== Recolectando estáticos =="
sudo -u blutesa "$APP_DIR/.venv/bin/python" "$APP_DIR/manage.py" collectstatic --noinput

echo "== Reiniciando el servicio =="
systemctl start blutesa-kardex
systemctl status blutesa-kardex --no-pager

echo
echo "Listo. Verifica:"
echo "  curl -I http://127.0.0.1:8030/"
echo "Si la web queda en loop de redirección (ERR_TOO_MANY_REDIRECTS), agrega"
echo "DJANGO_SECURE_SSL_REDIRECT=False a $APP_DIR/.env y reinicia el servicio."
