# Runbook de despliegue — VPS Linux propio (bare-metal, sin Docker)

Guía genérica para desplegar en un servidor Linux propio (Ubuntu 22.04+) al que tengas acceso
SSH, en vez de un PaaS como Render. Si el servidor ya corre otros servicios, revisa primero qué
puertos están libres antes de seguir.

## 0. Chequeo previo (no instala nada)

```bash
sudo ss -tlnp | grep -E ':5432|:443'
```

Confirma que el puerto de Postgres (5432) está libre (o elige otro) y si el 443 ya está tomado por
otro servicio del servidor, planea usar un puerto/subdominio distinto para este proyecto.

## 1. Paquetes y usuario de servicio

```bash
sudo apt update
sudo apt install python3-venv postgresql postgresql-contrib
sudo adduser --system --group --home /opt/blutesa-kardex blutesa
```

## 2. Copiar el código

Cualquier mecanismo de transferencia que uses (`scp`, `rsync`, `git clone` directo del repo, etc.)
sirve — solo asegúrate de **no** copiar `.venv/`, `__pycache__/`, `db.sqlite3`, `media/`,
`_respaldos/` ni `staticfiles/` (nada de eso va versionado ni debe viajar entre entornos a mano).

```bash
rsync -av --exclude .venv --exclude __pycache__ --exclude db.sqlite3 --exclude media \
  --exclude _respaldos --exclude staticfiles ./ usuario@tu-servidor:/opt/blutesa-kardex/
```

## 3. Entorno virtual

```bash
sudo -u blutesa python3 -m venv /opt/blutesa-kardex/.venv
sudo -u blutesa /opt/blutesa-kardex/.venv/bin/pip install -r /opt/blutesa-kardex/requirements.txt
```

## 4. PostgreSQL

```bash
sudo -u postgres createuser blutesa_kardex --pwprompt
sudo -u postgres createdb blutesa_kardex --owner=blutesa_kardex
```

## 5. Migración de datos (SQLite → Postgres) — ver plan completo para el detalle y cómo revertir

Resumen: `dumpdata` en SQLite → `.env` con `POSTGRES_DB` seteado → `migrate` → `loaddata` →
`sqlsequencereset` → copiar `media/firmas/` y `.vapid_keys.json` → comparar conteos por modelo
antes de dar de baja el entorno anterior.

## 6. `.env` de producción

Copiar `.env.example` a `/opt/blutesa-kardex/.env` (permisos `600`, dueño `blutesa`) y completar
`DJANGO_SECRET_KEY` real, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS` (tu dominio o hostname real),
credenciales de Postgres, claves VAPID migradas.

```bash
sudo -u blutesa /opt/blutesa-kardex/.venv/bin/python /opt/blutesa-kardex/manage.py collectstatic --noinput
sudo -u blutesa /opt/blutesa-kardex/.venv/bin/python /opt/blutesa-kardex/manage.py check --deploy
```

## 7. Gunicorn (systemd)

```bash
sudo cp /opt/blutesa-kardex/deploy/blutesa-kardex.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now blutesa-kardex
sudo systemctl status blutesa-kardex
curl 127.0.0.1:8030
```

## 8. Exponerlo con HTTPS

Usa el mecanismo que ya tengas disponible para HTTPS en tu servidor/red (proxy reverso con
Nginx/Caddy + certificado, tu VPN/mesh network si administras una, etc.) apuntando a
`http://127.0.0.1:8030`. Si el puerto 443 ya lo usa otro servicio del servidor, expón este
proyecto en un puerto o subdominio alternativo en vez de competir por el mismo puerto.

## 9. Respaldo diario

```bash
sudo chmod +x /opt/blutesa-kardex/deploy/backup.sh
sudo -u blutesa crontab -e
# agregar: 0 2 * * * /opt/blutesa-kardex/deploy/backup.sh
```

Probar una vez a mano y hacer una restauración de prueba antes de confiar en el cron:

```bash
sudo -u blutesa /opt/blutesa-kardex/deploy/backup.sh
sudo -u postgres createdb blutesa_kardex_test
sudo -u postgres pg_restore -d blutesa_kardex_test /opt/blutesa-kardex/backups/blutesa_kardex_*.dump
sudo -u postgres dropdb blutesa_kardex_test
```

## 10. Corte final

Cambiar las contraseñas del equipo por unas reales y fuertes, apagar cualquier entorno de pruebas
anterior, probar desde un celular real (login, kardex del día, notificación push).

## 11. Actualizaciones futuras (agregar módulos, subir cambios)

El paquete se genera limpio con `git archive` en vez de copiar la carpeta a mano — así nunca se
cuela `.venv/`, `db.sqlite3`, `media/` ni nada no versionado:

```bash
# En tu máquina, dentro del proyecto:
git archive -o paquete.zip HEAD
scp paquete.zip usuario@tu-servidor:~/
```

```bash
# En el servidor:
sudo /opt/blutesa-kardex/deploy/update.sh ~/paquete.zip
```

`update.sh` para el servicio, extrae el paquete sobre `/opt/blutesa-kardex` (preserva `.env`,
`media/` y `.venv/` porque ninguno de los tres está versionado), instala dependencias nuevas,
migra, recolecta estáticos y reinicia. Verificar después con `curl -I http://127.0.0.1:8030/` y
desde el navegador — si queda en loop de redirección, ver la nota de `DJANGO_SECURE_SSL_REDIRECT`
en `.env.example`.

**Nota sobre el módulo de Órdenes de Trabajo**: a diferencia de Render (disco efímero), en un
servidor bare-metal el disco es persistente — si `NEXTCLOUD_WEBDAV_URL` no está configurado, las
fotos de evidencia caen al disco local igual, pero ahí **sí se quedan** entre reinicios (no hay
riesgo de perderlas por redeploy). Configurar un WebDAV real (Nextcloud u otro) sigue siendo lo
ideal a mediano plazo, pero no es urgente para empezar a probar con el equipo.
