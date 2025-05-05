import sys
import io
from rutas import icon_bea
from common import *
import subprocess
import os
import threading
import psutil
from PIL import Image
from io import BytesIO
import base64
from time import sleep
import pystray

# Configuración de codificación segura
if hasattr(sys.stdout, "buffer") and sys.stdout.buffer is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configuración básica
RUTA_EXE = r"\\mercury\Producción\Minutas Produccion\Tests\Minutas Beta 2.2\Minutas Beta 2.2.exe"
APP_NAME = "Minutas BEA"
NOMBRE_PROCESO = "Minutas Beta 2.2.exe"

def terminar_proceso_force():
    """Termina el proceso y todos sus subprocesos de forma forzada"""
    try:
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == NOMBRE_PROCESO.lower() or proc.info['pid'] == current_pid:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except (psutil.TimeoutExpired, psutil.NoSuchProcess):
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        print(f"Error terminando procesos: {str(e)}")

def proceso_ya_en_ejecucion() -> bool:
    for proc in psutil.process_iter(['name']):
        if proc.info['name'].lower() == NOMBRE_PROCESO.lower():
            return True
    return False

def iniciar_aplicacion():
    try:
        if proceso_ya_en_ejecucion():
            print(f"{NOMBRE_PROCESO} ya está en ejecución")
            return
        # Modificación clave: CREATE_NEW_CONSOLE para mostrar la ventana
        subprocess.Popen(
            RUTA_EXE,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        print(f"Iniciando {NOMBRE_PROCESO}...")
    except Exception as e:
        print(f"Error al iniciar: {str(e)}")

def salir_app(icon: pystray.Icon, item):
    """Acción de salida forzada"""
    print("Cerrando todos los procesos...")
    terminar_proceso_force()
    icon.stop()
    os._exit(0)

def crear_icono_bandeja():
    try:
        icono_img = Image.open(BytesIO(base64.b64decode(icon_bea)))
        menu = pystray.Menu(
            pystray.MenuItem('Abrir', iniciar_aplicacion),
            pystray.MenuItem('Salir', salir_app)
        )
        icono = pystray.Icon(APP_NAME, icono_img, APP_NAME, menu)
        threading.Thread(target=icono.run, daemon=True).start()
    except Exception as e:
        print(f"Error creando icono: {str(e)}")

def main():
    crear_icono_bandeja()
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        salir_app(None, None)

if __name__ == "__main__":
    main()