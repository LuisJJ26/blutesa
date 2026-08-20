# Desplegar en Render (para pruebas)

Esto es un camino **separado** del `Dockerfile`/`entrypoint.sh` del repo (esos son a propósito
para probar en la red local de la oficina, con el servidor de desarrollo de Django). En Render se
usa el `Procfile` con Gunicorn.

## 0. Subir el repo a GitHub

Render despliega desde un repositorio de GitHub/GitLab conectado, no recibe el código directo. Si
todavía no lo has subido:

```bash
git remote add origin https://github.com/TU-USUARIO/TU-REPO.git
git push -u origin main
```

(Crea el repo vacío antes en github.com/new — sin README, sin .gitignore, para que no choque con
el historial que ya existe en este proyecto.)

## 1. Servicio web

En Render: **New → Web Service**, conectar este repo.

- **Runtime**: Python 3 (Render lee `.python-version` del repo y usa esa versión exacta; si esa
  build específica no está disponible en Render, el build falla con un mensaje claro — ajusta el
  archivo a la versión más cercana que sí tengan)
- **Build Command**: `./build.sh` (el script ya en el repo hace `pip install`, `collectstatic` y
  `migrate` en ese orden — equivalente a escribir los 3 comandos seguidos a mano)
- **Start Command**: (la toma sola del `Procfile`, o a mano) `gunicorn config.wsgi --bind 0.0.0.0:$PORT`

⚠️ El `Procfile` trae una línea `release: python manage.py migrate` a propósito por si algún día se
despliega en Heroku (ahí sí la ejecuta sola antes de cada release) — **Render la ignora**, no tiene
fase de "release" para servicios nativos. Por eso `migrate` va explícito en el Build Command de
arriba; sin eso, el primer deploy arranca con la base de datos vacía y todo falla al primer query.

## 2. Variables de entorno (pestaña Environment)

Obligatorias:
- `DJANGO_SECRET_KEY` — una clave larga y aleatoria (nunca la de `.env.example`).
- `DJANGO_DEBUG` = `False`

Para crear los 4 usuarios iniciales del equipo (incluye el superusuario `luis`) sin necesitar
Shell — `build.sh` corre `python manage.py sembrar_datos` en cada deploy, y ese comando lee
usuario y contraseña de variables de entorno por prefijo (usuario sin su contraseña definida se
omite, no falla el build):
- `LUIS_PASSWORD` (superusuario/Admin)
- `DAYMALIS_PASSWORD` (Auxiliar Contable)
- `JULIO_PASSWORD` (Bodeguero)
- `ELMER_PASSWORD` (Jefe de Operaciones)

Opcionalmente, `<PREFIJO>_NOMBRE` y `<PREFIJO>_APELLIDO` (ej. `LUIS_NOMBRE`, `LUIS_APELLIDO`)
para que el usuario quede con nombre completo — si no se definen, se crea sin nombre y se puede
completar después desde `/admin/`. Ningún dato personal del equipo vive en el código.

Usa contraseñas reales y fuertes acá. El comando es idempotente: si el usuario ya existe, no lo
toca aunque cambies la variable después (para cambiar una contraseña ya creada, hazlo desde
`/admin/`, no desde acá).

El resto tiene default seguro para probar rápido, pero lee la sección 3 antes de subir datos
reales.

## 3. ⚠️ Persistencia — importante antes de probar en serio

El disco de un Web Service de Render (plan Free/Starter, sin "Persistent Disk" pagado) se borra
en cada redeploy y cada vez que el servicio se duerme por inactividad y despierta de nuevo. Sin
configurar lo de abajo, **vas a perder datos** entre pruebas:

- **Base de datos**: si no defines nada, la app usa SQLite local — se borra en cada redeploy. Para
  probar más de una sesión, crea un **Postgres** en Render (New → PostgreSQL) y copia el valor
  **Internal Database URL** (pestaña Info de la base) a la variable `DATABASE_URL` del Web
  Service — más simple que copiar 5 campos sueltos (esa alternativa también existe: `POSTGRES_DB`/
  `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_HOST`/`POSTGRES_PORT`, ver `.env.example`).
- **Fotos y firma de perfil**: las fotos de Órdenes de Trabajo van a Nextcloud si configuras
  `NEXTCLOUD_WEBDAV_URL`/`NEXTCLOUD_USERNAME`/`NEXTCLOUD_APP_PASSWORD` (ver `.env.example`) — si
  no las configuras, caen al disco local de Render y se pierden igual que la base SQLite. La
  firma de perfil (`Usuario.firma`, la de cada usuario en "Mi firma") **siempre** se guarda en
  disco local sin importar Nextcloud — se perderá en cada redeploy a menos que agregues un
  Persistent Disk de Render montado en `/app/media`.
- **Claves push (VAPID)**: si no seteas `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`, se generan solas
  y se guardan en un archivo local — se pierden en cada redeploy, lo que invalida las
  notificaciones push de todos los que ya instalaron la PWA (tendrían que reinstalarla). Genera
  las claves una vez (`python manage.py generar_claves_vapid`) y pégalas como variables de
  entorno para que sean estables entre redeploys.

Para una prueba rápida y desechable (crear un par de usuarios, ver que todo funciona, tirar los
datos después) no hace falta nada de esto — SQLite + fallback local alcanzan. Para que el equipo
la use varios días seguidos probándola de verdad, sí conviene Postgres + VAPID fijo como mínimo
(Nextcloud si van a probar fotos).

## 4. Después del primer deploy

Con las 4 variables `*_PASSWORD` del paso 2 definidas, `sembrar_datos` ya creó a los 4 usuarios
(incluido el superusuario `luis`) durante el build — no hace falta Shell (el plan Free/Starter de
Render no la incluye). Entra directo a `/admin/` con `luis` y la contraseña que pusiste en
`LUIS_PASSWORD`.

## 5. Checklist rápido antes de compartir la URL con el equipo

```bash
python manage.py check --deploy
```

Debería salir limpio salvo el aviso de HSTS (opcional, léelo con cuidado antes de activarlo —
Django avisa que mal configurado puede ser difícil de revertir para los navegadores que ya lo
cachearon).
