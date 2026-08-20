from django import forms

from .models import KardexDocumento, KardexLinea


class KardexLineaForm(forms.ModelForm):
    class Meta:
        model = KardexLinea
        fields = [
            'clasif', 'loc_e', 'loc_l', 'loc_c', 'descripcion',
            'cantidad', 'unidad', 'precio_unitario', 'importe', 'entregado_a',
        ]
        widgets = {
            'clasif': forms.TextInput(attrs={'class': 'campo-corto'}),
            'loc_e': forms.TextInput(attrs={'class': 'campo-corto'}),
            'loc_l': forms.TextInput(attrs={'class': 'campo-corto'}),
            'loc_c': forms.TextInput(attrs={'class': 'campo-corto'}),
        }

    def __init__(self, *args, tipo=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tipo == KardexDocumento.Tipo.ENTRADA:
            del self.fields['entregado_a']


class KardexCabeceraForm(forms.ModelForm):
    class Meta:
        model = KardexDocumento
        fields = ['parte', 'referencia']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.tipo == KardexDocumento.Tipo.SALIDA:
            del self.fields['parte']


class RechazoForm(forms.Form):
    motivo_rechazo = forms.CharField(
        label='Motivo del rechazo', widget=forms.Textarea(attrs={'rows': 3}), required=True
    )
