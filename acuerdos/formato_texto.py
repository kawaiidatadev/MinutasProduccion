from common import *

def formatear_texto(texto, ancho=50):
    """Formatea el texto con saltos de línea cada cierto ancho"""
    if not texto:
        return ""

    # Primero dividir por saltos de línea existentes
    lineas = texto.split('\n')
    resultado = []

    for linea in lineas:
        # Luego dividir cada línea según el ancho deseado
        if len(linea) > ancho:
            palabras = linea.split()
            linea_actual = ""
            for palabra in palabras:
                if len(linea_actual) + len(palabra) + 1 > ancho:
                    resultado.append(linea_actual)
                    linea_actual = palabra
                else:
                    if linea_actual:
                        linea_actual += " " + palabra
                    else:
                        linea_actual = palabra
            if linea_actual:
                resultado.append(linea_actual)
        else:
            resultado.append(linea)

    return "\n".join(resultado)
