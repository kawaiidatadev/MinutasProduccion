import threading
import time
import os
import sys
import locale
import win32gui
import win32con
from common import *
from sql.db import db_create, buscar_minutas_db
from Menu.Menu import show_main_menu
from monitor_test import AcuerdoMonitor


def hide_console_window():
    """Oculta la ventana de consola en Windows"""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)


def is_monitor_running(lockfile="acuerdo_monitor.lock"):
    """Verifica si el monitor ya está en ejecución"""
    if os.path.exists(lockfile):
        try:
            with open(lockfile, 'r') as f:
                pid = int(f.read())
                try:
                    # Windows - intentar enviar señal 0
                    os.kill(pid, 0)
                    return True
                except OSError:
                    # El proceso no existe
                    os.remove(lockfile)
                    return False
        except:
            os.remove(lockfile)
            return False
    return False


def create_lock_file(lockfile="acuerdo_monitor.lock"):
    """Crea el archivo lock con el PID del proceso"""
    with open(lockfile, 'w') as f:
        f.write(str(os.getpid()))


def start_monitor_subprocess():
    """Lanza el monitor como un proceso en segundo plano"""
    if is_monitor_running():
        print("El monitor ya está en ejecución. No se iniciará una nueva instancia.")
        return None

    create_lock_file()
    subprocess.Popen(
        [sys.executable, "monitor_test.py"],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )

def main():
    verificar_imports()

    # Ocultar la ventana de consola inmediatamente
    hide_console_window()

    # Configuración regional
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        locale.setlocale(locale.LC_ALL, '')

    # Crear/verificar la base de datos
    db_create()
    db_path = buscar_minutas_db()

    # Usar subprocess.Popen para ejecutar el monitor en segundo plano
    # Iniciar el monitor como proceso externo
    start_monitor_subprocess()

    # Mostrar el menú principal
    show_main_menu(db_path)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if os.path.exists("acuerdo_monitor.lock"):
            os.remove("acuerdo_monitor.lock")


if __name__ == "__main__":
    main()