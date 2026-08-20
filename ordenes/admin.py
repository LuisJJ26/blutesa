from django.contrib import admin

from .models import OrdenTrabajo, OrdenTrabajoFoto, OrdenTrabajoLinea


class OrdenTrabajoLineaInline(admin.TabularInline):
    model = OrdenTrabajoLinea
    extra = 0


class OrdenTrabajoFotoInline(admin.TabularInline):
    model = OrdenTrabajoFoto
    extra = 0
    readonly_fields = ('ruta_nextcloud', 'url_publica', 'subida_por', 'subida_en')


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ('numero_formateado', 'cliente_nombre', 'tipo_servicio', 'estado', 'tecnico', 'fecha')
    list_filter = ('estado', 'tipo_servicio', 'fecha')
    search_fields = ('numero', 'cliente_nombre', 'cliente_codigo', 'barrio', 'telefono')
    inlines = [OrdenTrabajoLineaInline, OrdenTrabajoFotoInline]
