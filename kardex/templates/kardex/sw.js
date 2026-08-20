// Service Worker — Kardex BLUTESA
// Se sirve desde /sw.js (no desde /static/) para que el scope cubra todo el sitio.

const CACHE_VERSION = 'blutesa-kardex-v3';
const ESTATICOS_A_CACHEAR = [
  '/static/kardex/css/estilo.css',
  '/static/kardex/img/icons/icon-192.png',
  '/static/kardex/img/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(ESTATICOS_A_CACHEAR).catch(() => {}))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((nombres) =>
      Promise.all(
        nombres.filter((n) => n !== CACHE_VERSION).map((n) => caches.delete(n))
      )
    ).then(() => self.clients.claim())
  );
});

// Solo cacheamos archivos estáticos (CSS/íconos), con "stale-while-revalidate": se
// responde de inmediato con lo que haya en caché (rápido, funciona offline), pero
// SIEMPRE se pide también la versión de red en paralelo y se actualiza la caché para
// la próxima vez — así un cambio de CSS/ícono no se queda pegado para siempre.
// Todo lo demás (páginas, formularios, impresión) va siempre directo a la red: es un
// sistema de captura de datos y no queremos arriesgarnos a mostrar un documento
// desactualizado o un formulario con un token CSRF caducado.
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET') return;

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.open(CACHE_VERSION).then((cache) =>
        cache.match(event.request).then((cacheada) => {
          const actualizada = fetch(event.request)
            .then((respuesta) => {
              cache.put(event.request, respuesta.clone());
              return respuesta;
            })
            .catch(() => cacheada);
          return cacheada || actualizada;
        })
      )
    );
  }
});

// ---------- Notificaciones push ----------
self.addEventListener('push', (event) => {
  let datos = {};
  try {
    datos = event.data ? event.data.json() : {};
  } catch (e) {
    datos = { titulo: 'Kardex BLUTESA', cuerpo: event.data ? event.data.text() : '' };
  }
  const titulo = datos.titulo || 'Kardex BLUTESA';
  const opciones = {
    body: datos.cuerpo || '',
    icon: '/static/kardex/img/icons/icon-192.png',
    badge: '/static/kardex/img/icons/icon-192.png',
    tag: datos.tag || 'kardex-blutesa',
    data: { url: datos.url || '/' },
  };
  event.waitUntil(self.registration.showNotification(titulo, opciones));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const destino = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((lista) => {
      for (const cliente of lista) {
        if (cliente.url.includes(destino) && 'focus' in cliente) return cliente.focus();
      }
      for (const cliente of lista) {
        if ('focus' in cliente) {
          cliente.navigate(destino);
          return cliente.focus();
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(destino);
    })
  );
});
