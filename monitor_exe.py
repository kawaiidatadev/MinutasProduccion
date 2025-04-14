import os
import subprocess
from time import sleep


def ejecutar_monitor():
    # Ruta de la carpeta compartida
    ruta_carpeta = r"\\mercury\Producción\Minutas Produccion\Monitor"
    # Nombre del ejecutable
    nombre_exe = "Monitor.exe"

    try:
        # Construir la ruta completa
        ruta_completa = os.path.join(ruta_carpeta, nombre_exe)

        # Verificar si el archivo existe
        if not os.path.exists(ruta_completa):
            raise FileNotFoundError(f"No se encontró el archivo: {ruta_completa}")

        # Ejecutar el programa una sola vez
        subprocess.Popen(ruta_completa, shell=True)

        print(f"Se ha ejecutado {nombre_exe} correctamente")
        return True

    except Exception as e:
        print(f"Error al ejecutar {nombre_exe}: {str(e)}")
        return False


# Ejemplo de uso
if __name__ == "__main__":
    ejecutar_monitor()