from django import forms

from .models import Usuario


class FirmaForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['firma']
        widgets = {
            'firma': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
