from django.urls import path

from . import views

app_name = 'ordenes'

urlpatterns = [
    path('crear/', views.crear, name='crear'),
    path('tecnico/', views.panel_tecnico, name='panel_tecnico'),
    path('buscar/', views.buscar, name='buscar'),

    path('orden/<int:pk>/', views.detalle, name='detalle'),
    path('orden/<int:pk>/cerrar/', views.cerrar, name='cerrar'),
    path('orden/<int:pk>/cancelar/', views.cancelar, name='cancelar'),
    path('orden/<int:pk>/imprimir/', views.imprimir, name='imprimir'),
]
