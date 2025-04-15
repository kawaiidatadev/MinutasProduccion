import os
import subprocess
import sys
from time import sleep

# Configuración
RUTA_CARPETA = r"\\mercury\Producción\Minutas Produccion\Monitor"
NOMBRE_EXE = "Monitor.exe"


def is_process_running(process_name):
    """Verifica si el proceso está en ejecución"""
    try:
        # Ejecutar tasklist y capturar salida
        output = subprocess.check_output(
            ['tasklist', '/fi', f'imagename eq {process_name}'],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return process_name.lower() in output.lower()
    except subprocess.CalledProcessError:
        return False


def ejecutar_monitor():
    try:
        print("Verificando estado del monitor...")

        # Verificar si el proceso ya está en ejecución
        if is_process_running(NOMBRE_EXE):
            print("El monitor ya está en ejecución.")
            return False

        # Construir ruta completa
        ruta_completa = os.path.join(RUTA_CARPETA, NOMBRE_EXE)

        # Verificar si el ejecutable existe
        if not os.path.exists(ruta_completa):
            raise FileNotFoundError(f"Archivo no encontrado: {ruta_completa}")

        # Iniciar el proceso
        subprocess.Popen(ruta_completa, shell=True)
        print(f"{NOMBRE_EXE} iniciado correctamente.")
        return True

    except Exception as e:
        print(f"Error: {str(e)}")
        return False


