from django import forms
from django.contrib.auth import get_user_model

from .models import OrdenTrabajo, OrdenTrabajoLinea

Usuario = get_user_model()


class OrdenTrabajoCrearForm(forms.ModelForm):
    class Meta:
        model = OrdenTrabajo
        fields = [
            'cliente_nombre', 'cliente_codigo', 'barrio', 'direccion', 'telefono',
            'tipo_servicio', 'tipo_servicio_detalle', 'observaciones', 'tecnico', 'fecha',
            'posibilidad_tecnica',
        ]
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 2}),
            'fecha': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tecnico'].queryset = Usuario.objects.filter(rol='TECNICO').order_by('first_name')
        self.fields['tecnico'].required = True
        self.fields['posibilidad_tecnica'].required = True
        self.fields['posibilidad_tecnica'].label = 'Posibilidad Técnica'

    def clean(self):
        datos = super().clean()
        if datos.get('tipo_servicio') == OrdenTrabajo.TipoServicio.OTRO and not datos.get('tipo_servicio_detalle'):
            self.add_error('tipo_servicio_detalle', 'Describe el tipo de servicio.')
        return datos


class OrdenTrabajoCierreForm(forms.ModelForm):
    gps_lat = forms.FloatField(required=False, widget=forms.HiddenInput)
    gps_lng = forms.FloatField(required=False, widget=forms.HiddenInput)
    gps_precision_m = forms.FloatField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = OrdenTrabajo
        fields = [
            'reparado', 'nota_debito_aplica', 'nota_debito_numero',
            'tenia_cable_anteriormente', 'nombre_anterior',
            'fecha_elaboracion', 'sin_georreferencia', 'motivo_sin_gps',
        ]
        widgets = {
            'fecha_elaboracion': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        datos = super().clean()
        if datos.get('sin_georreferencia') and not datos.get('motivo_sin_gps'):
            self.add_error('motivo_sin_gps', 'Indica por qué no se pudo capturar la ubicación.')
        if not datos.get('sin_georreferencia') and datos.get('gps_lat') is None:
            self.add_error(None, 'No se recibió la ubicación GPS. Actívala o marca "Sin georreferencia".')
        if datos.get('tenia_cable_anteriormente') == OrdenTrabajo.SiNo.SI and not datos.get('nombre_anterior'):
            self.add_error('nombre_anterior', 'Indica a nombre de quién estaba el cable anterior.')
        return datos


class LineasOrdenForm(forms.Form):
    """Un par cantidad/valor por cada concepto fijo de la tabla Mantenimiento del papel."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for valor, etiqueta in OrdenTrabajoLinea.Concepto.choices:
            self.fields[f'cantidad_{valor}'] = forms.DecimalField(
                label=etiqueta, required=False, min_value=0, max_digits=10, decimal_places=2,
            )
            self.fields[f'valor_{valor}'] = forms.DecimalField(
                required=False, min_value=0, max_digits=10, decimal_places=2,
            )

    def filas(self):
        """[(concepto, etiqueta, campo_cantidad, campo_valor), ...] para iterar en la plantilla."""
        for valor, etiqueta in OrdenTrabajoLinea.Concepto.choices:
            yield valor, etiqueta, self[f'cantidad_{valor}'], self[f'valor_{valor}']
