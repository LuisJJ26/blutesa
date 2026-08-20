from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('perfil/', views.perfil, name='perfil'),
    path('push/suscribir/', views.guardar_suscripcion_push, name='guardar_suscripcion_push'),
    path('push/desuscribir/', views.eliminar_suscripcion_push, name='eliminar_suscripcion_push'),
]
