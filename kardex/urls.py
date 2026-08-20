from django.urls import path

from . import views

app_name = 'kardex'

urlpatterns = [
    path('bodega/', views.panel_bodega, name='panel_bodega'),
    path('bodega/abrir/<str:tipo>/', views.abrir_hoy, name='abrir_hoy'),
    path('jefe/', views.panel_jefe, name='panel_jefe'),
    path('contable/', views.panel_contable, name='panel_contable'),
    path('admin-general/', views.panel_admin, name='panel_admin'),
    path('informe-mensual/', views.informe_mensual, name='informe_mensual'),
    path('buscar/', views.buscar, name='buscar'),

    path('documento/<int:pk>/', views.detalle, name='detalle'),
    path('documento/<int:pk>/cabecera/', views.actualizar_cabecera, name='actualizar_cabecera'),
    path('documento/<int:pk>/linea/', views.agregar_linea, name='agregar_linea'),
    path('documento/<int:pk>/linea/<int:linea_pk>/editar/', views.editar_linea, name='editar_linea'),
    path('documento/<int:pk>/enviar/', views.cerrar_enviar, name='cerrar_enviar'),
    path('documento/<int:pk>/corregir/', views.corregir, name='corregir'),
    path('documento/<int:pk>/rechazar/', views.rechazar, name='rechazar'),
    path('documento/<int:pk>/revisar/', views.revisar, name='revisar'),
    path('documento/<int:pk>/imprimir/', views.imprimir, name='imprimir'),
]
