from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from kardex import views as kardex_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', kardex_views.inicio, name='inicio'),
    path('cuentas/', include('accounts.urls')),
    path('kardex/', include('kardex.urls')),
    path('ordenes/', include('ordenes.urls')),
    path('clientes/', include('clientes.urls')),
    path('sw.js', kardex_views.service_worker, name='service_worker'),
]

# Volumen de esta app es chico (pocas firmas y fotos de evidencia) — Django sirve media/
# directo en vez de sumar un servidor aparte solo para esto. `django.conf.urls.static.static()`
# no sirve acá porque solo registra la ruta cuando DEBUG=True; se usa la vista de bajo nivel
# directo para que también funcione en producción (DEBUG=False).
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
