import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import FirmaForm
from .models import SuscripcionPush


@login_required
def perfil(request):
    if request.method == 'POST':
        form = FirmaForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Firma electrónica actualizada.')
            return redirect('perfil')
    else:
        form = FirmaForm(instance=request.user)
    return render(request, 'accounts/perfil.html', {
        'form': form,
        'vapid_public_key': settings.VAPID_PUBLIC_KEY,
    })


@login_required
@require_POST
def guardar_suscripcion_push(request):
    try:
        datos = json.loads(request.body)
        endpoint = datos['endpoint']
        p256dh = datos['keys']['p256dh']
        auth = datos['keys']['auth']
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Datos de suscripción inválidos.'}, status=400)

    SuscripcionPush.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            'usuario': request.user,
            'p256dh': p256dh,
            'auth': auth,
            'navegador': datos.get('navegador', '')[:255],
        },
    )
    return JsonResponse({'ok': True})


@login_required
@require_POST
def eliminar_suscripcion_push(request):
    try:
        datos = json.loads(request.body)
        endpoint = datos['endpoint']
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)

    request.user.suscripciones_push.filter(endpoint=endpoint).delete()
    return JsonResponse({'ok': True})
