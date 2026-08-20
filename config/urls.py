from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

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

# Volumen de esta app es chico (3 usuarios, pocas firmas subidas) — Django sirve media/ directo
# incluso con DEBUG=False, en vez de sumar un servidor aparte solo para esto.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
