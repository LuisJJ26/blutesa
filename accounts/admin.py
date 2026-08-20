from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import SuscripcionPush, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Rol y firma', {'fields': ('rol', 'firma')}),
    )
    list_display = ('username', 'first_name', 'last_name', 'rol', 'is_staff')
    list_filter = UserAdmin.list_filter + ('rol',)


@admin.register(SuscripcionPush)
class SuscripcionPushAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'navegador', 'creada_en')
    list_filter = ('usuario',)
