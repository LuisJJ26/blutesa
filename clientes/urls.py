from django.urls import path

from . import views

app_name = 'clientes'

urlpatterns = [
    path('', views.buscar, name='buscar'),
    path('buscar-ajax/', views.buscar_ajax, name='buscar_ajax'),
]
