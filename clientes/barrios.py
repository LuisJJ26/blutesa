"""Catálogo de códigos de barrio del sistema legado (MAESTRO.DBF). No existe un
archivo fuente aparte para esta tabla; los valores se tomaron directo de la
pantalla "TABLA DE CODIGOS" del sistema original."""

BARRIOS = {
    '01': 'Punta Fría',
    '02': 'Central',
    '03': 'Pointeen',
    '04': 'Beholden',
    '05': 'Old Bank',
    '06': 'Pancasán',
    '07': 'Canal',
    '08': 'Fátima',
    '09': 'Santa Rosa',
    '10': 'Teodoro Martínez',
    '11': 'San Pedro',
    '12': 'San Mateo',
    '13': 'New York',
    '14': 'Ricardo Morales',
    '15': '19 de Julio',
    '16': 'Tres Cruces',
    '17': 'Asentamiento Sandino',
    '18': 'Caño Azul',
}


def nombre_barrio(codigo):
    codigo = (codigo or '').strip()
    return BARRIOS.get(codigo, codigo)
