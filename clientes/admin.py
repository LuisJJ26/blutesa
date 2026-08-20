from django.contrib import admin

from .models import Cliente, ClienteFibra


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'codigo', 'contrato', 'barrio_nombre', 'telefono', 'activo')
    list_filter = ('activo', 'barrio')
    search_fields = ('nombre', 'apellido1', 'apellido2', 'codigo', 'contrato', 'direccion', 'telefono')
    ordering = ('nombre', 'apellido1')


@admin.register(ClienteFibra)
class ClienteFibraAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'cedula', 'barrio', 'telefono', 'bw_mbps', 'modelo')
    list_filter = ('tipo', 'modelo')
    search_fields = ('nombre', 'cedula', 'barrio', 'telefono', 'serie', 'ip')
    ordering = ('nombre',)
