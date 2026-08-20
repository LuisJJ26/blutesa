# Kardex de Almacén — BLUTESA

Aplicación web (Django) para digitalizar el proceso de Entrada y Salida de Almacén, Órdenes de
Trabajo de técnicos y consulta del maestro de clientes: numeración consecutiva, firma
electrónica, control por roles y notificaciones push.

## Funcionalidad

- Kardex de **Entrada** (`EA`) y **Salida** (`SA`) de Almacén, uno por día por tipo, con
  numeración consecutiva sin huecos ni duplicados.
- Flujo por roles: el Bodeguero abre el día y agrega líneas → el documento se aprueba
  automáticamente → Auxiliar Contable revisa, corrige una línea si hace falta, o rechaza con
  motivo (el Bodeguero corrige y reenvía).
- Firma electrónica por usuario, estampada en la impresión según el paso.
- En Salida, cada línea registra su propio "Entregado a" (puede ser un técnico distinto por
  línea el mismo día).
- Órdenes de Trabajo: el Jefe de Operaciones crea la orden con búsqueda de cliente integrada, el
  Técnico la cierra con materiales, foto y georreferencia.
- Maestro de Clientes (Cable/TV y Fibra/Internet) con búsqueda por texto y filtros, autocompletado
  al crear una Orden de Trabajo, y panel de administración restringido por rol.
- Búsqueda con filtros combinables (texto libre, tipo, estado, rango de fechas).
- Informe mensual con totales por tipo/estado y detalle imprimible.
- Instalable como PWA, con notificaciones push en cada paso del flujo.
- Modo claro/oscuro y navegación adaptada a celular.
- Impresión fiel a los formatos originales de Entrada/Salida de Almacén.

Próximos módulos: Comprobante de Pago, Solicitud de Pago, Tarjeta de Mayor, Control de
Inventario.

## Stack

Django 6 · PostgreSQL (SQLite en desarrollo) · Gunicorn + Whitenoise · PWA (service worker +
Web Push/VAPID).

## Cómo correr en local

```bash
cd BlutesaKardex
.venv/Scripts/python.exe manage.py runserver 8030
```
