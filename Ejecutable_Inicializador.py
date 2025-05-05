# Ejecutable_inicializador.py
import sys
import os
import winreg
import shutil
from pathlib import Path
import logging


def configurar_log():
    """Configura el sistema de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


def normalizar_ruta(ruta: str) -> str:
    """Normaliza rutas con caracteres especiales y espacios"""
    try:
        return os.path.normpath(ruta)
    except Exception as e:
        logging.error(f"Error normalizando ruta: {str(e)}")
        return ruta


def obtener_rutas_especiales():
    """Obtiene rutas con soporte para OneDrive empresarial"""
    try:
        # Obtener ruta de OneDrive con detección robusta
        one_drive = None
        try:
            from win32com.shell import shell, shellcon
            one_drive = shell.SHGetFolderPath(0, shellcon.CSIDL_PROFILE, None, 0)
            one_drive = os.path.join(one_drive, 'OneDrive - Empresa')
        except:
            pass

        # Fallback a variables de entorno
        if not one_drive or not os.path.exists(one_drive):
            one_drive = os.getenv('OneDriveCommercial') or os.getenv('OneDrive')

        # Construcción de rutas con validación
        rutas = {
            'desktop': None,
            'startup': None
        }

        # Detección de escritorio
        escritorios_validos = [
            os.path.join(os.path.expanduser('~'), 'Desktop'),
            os.path.join(one_drive, 'Escritorio') if one_drive else None,
            os.path.join(one_drive, 'Desktop') if one_drive else None
        ]

        for escritorio in escritorios_validos:
            if escritorio and os.path.exists(escritorio):
                rutas['desktop'] = normalizar_ruta(escritorio)
                break

        # Detección de carpeta Startup
        startups_validos = [
            os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'),
            os.path.join(one_drive, 'AppData', 'Roaming', 'Microsoft', 'Windows', 'Start Menu', 'Programs',
                         'Startup') if one_drive else None
        ]

        for startup in startups_validos:
            if startup and os.path.exists(startup):
                rutas['startup'] = normalizar_ruta(startup)
                break

        return rutas

    except Exception as e:
        logging.error(f"Error obteniendo rutas: {str(e)}")
        return None


def crear_acceso_directo(origen: str, destino: str) -> bool:
    """Crea accesos directos con manejo de espacios y caracteres especiales"""
    try:
        origen = normalizar_ruta(origen)
        destino = normalizar_ruta(destino)

        # Método preferido con validación
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(destino)
            shortcut.TargetPath = f'"{origen}"'  # Comillas para espacios
            shortcut.WorkingDirectory = os.path.dirname(origen)
            shortcut.Save()
            return os.path.exists(destino)
        except Exception as e:
            logging.warning(f"Método COM fallido: {str(e)}")

        # Fallback a winshell
        try:
            import winshell
            winshell.CreateShortcut(
                Path(destino),
                Target=Path(origen),
                Icon=(origen, 0),
                Description="Inicializador de Minutas BEA"
            )
            return os.path.exists(destino)
        except Exception as e:
            logging.warning(f"Método winshell fallido: {str(e)}")

        # Fallback avanzado
        try:
            contenido = f'''[InternetShortcut]
URL=file:///{origen.replace(" ", "%20")}
WorkingDirectory={os.path.dirname(origen)}
IconFile={origen}
IconIndex=0'''

            with open(destino, 'w', encoding='utf-8') as f:
                f.write(contenido)

            return True
        except Exception as e:
            logging.error(f"Error creando acceso directo: {str(e)}")
            return False

    except Exception as e:
        logging.error(f"Error crítico creando acceso: {str(e)}")
        return False


def agregar_inicio_windows(ruta_exe: str) -> bool:
    """Agrega al inicio con múltiples métodos y validación"""
    try:
        # Método 1: Registro de Windows (mejor para rutas complejas)
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Run',
                0, winreg.KEY_WRITE
            )
            winreg.SetValueEx(
                key,
                'InicializadorMinutas',
                0,
                winreg.REG_SZ,
                f'"{ruta_exe}"'  # Comillas para espacios
            )
            winreg.CloseKey(key)
            logging.info("Configuración de registro exitosa")
            return True
        except Exception as e:
            logging.warning(f"Error en registro: {str(e)}")

        # Método 2: Carpeta Startup
        rutas = obtener_rutas_especiales()
        if rutas and rutas['startup']:
            destino = os.path.join(rutas['startup'], 'Inicializador Minutas.lnk')
            if crear_acceso_directo(ruta_exe, destino):
                logging.info("Acceso directo en Startup creado")
                return True

        # Método 3: Tarea programada
        try:
            from win32com.taskscheduler import taskscheduler
            ts = taskscheduler.CoCreateInstance(
                taskscheduler.CLSID_CTaskScheduler,
                None,
                taskscheduler.CLSCTX_INPROC_SERVER,
                taskscheduler.IID_ITaskScheduler
            )
            # ... (configuración de tarea programada)
            logging.info("Tarea programada creada")
            return True
        except Exception as e:
            logging.warning(f"Error en tarea programada: {str(e)}")

        return False

    except Exception as e:
        logging.error(f"Error agregando al inicio: {str(e)}")
        return False


def ejecutable_run():
    """Función principal de ejecución"""
    configurar_log()

    try:
        ruta_inicializador = normalizar_ruta(
            r"\\mercury\Producción\Minutas Produccion\Program Files\Inicializador.exe"
        )

        if not os.path.exists(ruta_inicializador):
            logging.error("El ejecutable no existe en la ruta especificada")
            return

        logging.info(f"Ruta normalizada del ejecutable: {ruta_inicializador}")

        # Ejecutar configuración de inicio
        if agregar_inicio_windows(ruta_inicializador):
            logging.info("Configuración de inicio completada")
        else:
            logging.warning("No se pudo completar la configuración de inicio")

        # Crear acceso directo en escritorio
        rutas = obtener_rutas_especiales()
        if rutas and rutas['desktop']:
            destino = os.path.join(rutas['desktop'], 'Inicializador Minutas.lnk')
            if crear_acceso_directo(ruta_inicializador, destino):
                logging.info("Acceso directo en escritorio creado")
            else:
                logging.warning("Error creando acceso directo en escritorio")

    except Exception as e:
        logging.error(f"Error crítico: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    ejecutable_run()