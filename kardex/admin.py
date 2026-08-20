from django.contrib import admin

from .models import KardexDocumento, KardexLinea, NumeroSecuencia


class KardexLineaInline(admin.TabularInline):
    model = KardexLinea
    extra = 0


@admin.register(KardexDocumento)
class KardexDocumentoAdmin(admin.ModelAdmin):
    list_display = ('numero_formateado', 'tipo', 'fecha', 'estado', 'creado_por')
    list_filter = ('tipo', 'estado', 'fecha')
    inlines = [KardexLineaInline]


@admin.register(NumeroSecuencia)
class NumeroSecuenciaAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'ultimo_numero')
