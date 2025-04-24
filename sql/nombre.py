from common import *

def sanitizar_nombre(nombre):
    """Limpia caracteres inválidos para nombres de archivo"""
    nombre = re.sub(r'[\\/*?:"<>|]', '_', nombre)
    nombre = nombre.replace(' ', '_').strip()
    return nombre[:30]  # Limitar a 30 caracteres