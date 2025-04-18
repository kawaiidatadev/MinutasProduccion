import sys
import os
import io
import time
import threading
import sqlite3
import win32api
import win32con
import win32event
import winerror
from PIL import Image
import pystray

# Configuración de paths
from rutas import DB_PATH
DB_PATH = DB_PATH
APP_NAME = "AcuerdoMonitor"
MUTEX_NAME = f"Global\\{APP_NAME}_Mutex"


class AcuerdoMonitor:
    def __init__(self, db_path, check_interval=5):
        self.db_path = db_path
        self.check_interval = check_interval
        self.running = False
        self.last_checked_id = 0
        self.tray_icon = None
        self.mutex = None
        self._initialize()

    def _initialize(self):
        """Inicializa componentes críticos"""
        try:
            # Verificar si ya hay una instancia en ejecución
            self._create_mutex()

            # Configurar rutas y autostart
            self._setup_autostart()

            # Obtener último ID de acuerdo
            self.last_checked_id = self._get_last_agreement_id()

            # Configurar el directorio de trabajo
            self._set_working_directory()

        except Exception as e:
            self._log_error(f"Error en inicialización: {e}")
            raise

    def _set_working_directory(self):
        """Configura el directorio de trabajo correcto para .exe"""
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            os.chdir(base_path)
        except Exception as e:
            self._log_error(f"Error configurando directorio: {e}")

    def _create_mutex(self):
        """Crea un mutex para evitar múltiples instancias"""
        self.mutex = win32event.CreateMutex(None, False, MUTEX_NAME)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            self._log_error("Ya hay una instancia en ejecución. Saliendo...")
            sys.exit(0)

    def _setup_autostart(self):
        """Configura el autoinicio usando rutas absolutas"""
        try:
            if getattr(sys, 'frozen', False):
                app_path = f'"{sys.executable}"'
            else:
                app_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'

            key = win32api.RegOpenKeyEx(
                win32con.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                win32con.KEY_SET_VALUE
            )
            win32api.RegSetValueEx(key, APP_NAME, 0, win32con.REG_SZ, app_path)
            win32api.RegCloseKey(key)
        except Exception as e:
            self._log_error(f"Error autoinicio: {str(e)[:200]}")

    def _get_last_agreement_id(self):
        """Obtiene el ID más reciente para comenzar el monitoreo"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id) FROM historial_acuerdos")
            last_id = cursor.fetchone()[0] or 0
            conn.close()
            return last_id
        except Exception as e:
            self._log_error(f"Error obteniendo último ID: {e}")
            return 0
    def _log_error(self, message):
        """Registra mensajes de error en la consola (y opcionalmente en un archivo)"""
        print(f"[ERROR] {message}", file=sys.stderr)

    def _show_notification(self, title, message, pdf_path=None):
        """Muestra notificación con capacidad para abrir PDF"""
        try:
            print(f"\n[NOTIFICACIÓN] Preparando notificación - Título: {title}")
            print(f"[NOTIFICACIÓN] Mensaje: {message}")

            if pdf_path:
                print(f"[NOTIFICACIÓN] PDF asociado: {pdf_path}")
            else:
                print("[NOTIFICACIÓN] No hay PDF asociado")

            # Verificar si estamos en modo .exe
            if getattr(sys, 'frozen', False):
                print("[NOTIFICACIÓN] Modo .exe - Usando notificaciones nativas de Windows")
                # Usar notificaciones nativas de Windows en .exe
                self._show_windows_notification(title, message)
            else:
                print("[NOTIFICACIÓN] Modo desarrollo - Usando plyer para notificaciones")
                # Usar plyer en modo desarrollo
                notification.notify(
                    title=title,
                    message=message,
                    app_name=APP_NAME,
                    timeout=10
                )

            # Abrir PDF si existe
            if pdf_path and os.path.exists(pdf_path):
                print("[NOTIFICACIÓN] Intentando abrir PDF...")
                self._open_pdf(pdf_path)
            elif pdf_path:
                print(f"[ADVERTENCIA] El PDF no existe en la ruta: {pdf_path}")

            print("[NOTIFICACIÓN] Proceso de notificación completado\n")

        except Exception as e:
            self._log_error(f"Error mostrando notificación: {e}")

    def _show_windows_notification(self, title, message):
        """Sistema de notificaciones usando solo módulos nativos de Windows"""
        methods = [
            self._try_shell_notify_icon,  # Método más moderno
            self._try_message_box_ctypes,  # Método tradicional 1
            self._try_message_box_win32api,  # Método tradicional 2
            self._try_console_notification  # Último recurso
        ]

        for method in methods:
            try:
                method(title, message)
                return  # Salir si tuvo éxito
            except Exception as e:
                error_msg = f"Error con {method.__name__}: {str(e)[:200]}"
                self._log_error(error_msg)
                continue

        # Si todo falla absolutamente
        print(f"* Notificación * {title}: {message}")

    def _try_shell_notify_icon(self, title, message):
        """Intenta con Shell_NotifyIcon (funciona desde Windows 2000)"""
        import ctypes
        from ctypes import wintypes

        # Constantes necesarias
        NIM_ADD = 0
        NIF_INFO = 0x10
        NIF_MESSAGE = 0x01

        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [
                ('cbSize', wintypes.DWORD),
                ('hWnd', wintypes.HWND),
                ('uID', wintypes.UINT),
                ('uFlags', wintypes.UINT),
                ('uCallbackMessage', wintypes.UINT),
                ('hIcon', wintypes.HICON),
                ('szTip', wintypes.WCHAR * 128),
                ('dwState', wintypes.DWORD),
                ('dwStateMask', wintypes.DWORD),
                ('szInfo', wintypes.WCHAR * 256),
                ('szInfoTitle', wintypes.WCHAR * 64),
                ('uTimeout', wintypes.UINT),
            ]

        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = 0
        nid.uFlags = NIF_INFO | NIF_MESSAGE
        nid.szInfo = message[:255]
        nid.szInfoTitle = title[:63]
        nid.uTimeout = 10000  # 10 segundos

        # Intenta cargar shell32.dll
        shell32 = ctypes.windll.shell32
        if not shell32.Shell_NotifyIcon(NIM_ADD, ctypes.byref(nid)):
            raise Exception("Shell_NotifyIcon falló")

    def _try_message_box_ctypes(self, title, message):
        """MessageBox usando ctypes directamente"""
        import ctypes
        MB_ICONINFORMATION = 0x40

        # Versión Unicode (MessageBoxW)
        ctypes.windll.user32.MessageBoxW(0, message, title, MB_ICONINFORMATION)

    def _try_message_box_win32api(self, title, message):
        """MessageBox usando win32api (pywin32)"""
        import win32api
        win32api.MessageBox(0, message, title, 0x40)

    def _try_console_notification(self, title, message):
        """Notificación en consola con sonido de sistema"""
        import winsound
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except:
            pass  # Si falla el sonido, continuamos igual

        print(f"! NOTIFICACIÓN ! {title.upper()}: {message}")

    def _show_message_box(self, title, message):
        """Método tradicional de MessageBox"""
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)  # MB_ICONINFORMATION

    def _open_pdf(self, pdf_path):
        """Abre el PDF con el visor predeterminado"""
        try:
            if os.path.exists(pdf_path):
                # Verificar si es una ruta UNC (red)
                if pdf_path.startswith(r'\\'):
                    # Mapear unidad de red temporal si es necesario
                    self._map_network_drive_if_needed()

                os.startfile(pdf_path)
        except Exception as e:
            self._log_error(f"Error abriendo PDF: {e}")

    def _map_network_drive_if_needed(self):
        """Mapea unidad de red con credenciales persistentes"""
        try:
            if not os.path.exists(r"\\mercury\Producción"):
                win32api.WNetAddConnection2(
                    win32con.RESOURCETYPE_DISK,
                    None,
                    r"\\mercury\Producción",
                    None,
                    None,
                    win32con.CONNECT_UPDATE_PROFILE
                )
        except Exception as e:
            self._log_error(f"Error mapeando unidad: {str(e)[:200]}")

    def _check_closed_agreements(self):
        """Busca acuerdos recién cerrados"""
        try:
            print(f"\n[CHECK] Verificando acuerdos cerrados desde ID: {self.last_checked_id}")

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, acuerdo, usuario_modifico, ruta_pdf 
                FROM historial_acuerdos 
                WHERE id > ? AND estatus = 'Cerrado'
                ORDER BY id DESC
            """, (self.last_checked_id,))

            new_closed = cursor.fetchall()
            print(f"[CHECK] Encontrados {len(new_closed)} acuerdos cerrados nuevos")

            for agreement in new_closed:
                id_, acuerdo, usuario, ruta_pdf = agreement
                self.last_checked_id = max(self.last_checked_id, id_)

                print(f"\n[ACUERDO] Nuevo acuerdo cerrado detectado:")
                print(f"  ID: {id_}")
                print(f"  Usuario: {usuario}")
                print(f"  Acuerdo: {acuerdo[:50]}...")
                print(f"  Ruta PDF: {ruta_pdf if ruta_pdf else 'Ninguna'}")

                # Mostrar notificación
                self._show_notification(
                    "Acuerdo Cerrado",
                    f"El usuario {usuario} ha cerrado el acuerdo: {acuerdo[:50]}...",
                    ruta_pdf
                )

            conn.close()
            return len(new_closed)

        except Exception as e:
            self._log_error(f"Error verificando acuerdos: {str(e)[:200]}")
            return 0

    def _monitor_changes(self):
        """Monitorea cambios en la base de datos"""
        print("[MONITOR] Iniciando bucle de monitoreo...")
        while self.running:
            try:
                print(f"\n[MONITOR] Verificando cambios ({time.strftime('%Y-%m-%d %H:%M:%S')})...")
                changes = self._check_closed_agreements()
                if changes > 0:
                    self._log_info(f"[MONITOR] Detectados {changes} acuerdos cerrados nuevos")
                else:
                    print("[MONITOR] No se detectaron cambios")
            except Exception as e:
                self._log_error(f"Error en monitor: {str(e)[:200]}")

            print(f"[MONITOR] Esperando {self.check_interval} segundos...")
            time.sleep(self.check_interval)

    def start(self):
        """Inicia el monitor en segundo plano"""
        if not self.running:
            print("\n[INICIO] Iniciando AcuerdoMonitor...")
            self.running = True

            # Iniciar el icono en la bandeja
            print("[INICIO] Creando icono en bandeja del sistema...")
            self._create_tray_icon()

            # Iniciar el monitor de cambios
            print("[INICIO] Iniciando hilo de monitoreo...")
            monitor_thread = threading.Thread(
                target=self._monitor_changes,
                daemon=True
            )
            monitor_thread.start()

            self._log_info(f"[INICIO] Monitor iniciado. Observando acuerdos cerrados en: {self.db_path}")
            print(f"[INICIO] Último ID verificado: {self.last_checked_id}")

    def _exit_app(self, icon=None, item=None):
        """Cierra la aplicación y detiene el ícono de la bandeja"""
        if hasattr(self, "tray_icon"):
            self.tray_icon.stop()
        print("Saliendo de la aplicación...")
        sys.exit(0)

    # En el método _create_tray_icon:

    def _create_tray_icon(self):
        """Crea un ícono en la bandeja del sistema"""
        try:
            import pystray
            import base64
            from io import BytesIO

            # Cargar imagen del icono
            icon_data = base64.b64decode("""iVBORw0KGgoAAAANSUhEUgAABYoAAAZ2CAYAAAAFUJJ+AAAACXBIWXMAAC4jAAAuIwF4pT92AAAgAElEQVR4nOzdXYwn2Xkf5lMrSiIt2zMFQ7GYZTxtWpC/AHeThhAgRjC9BnKjC03vRYCVDWN6IMQBfMOmw8AuwMD2wnDqJgBnYV8oF8H0BEKwsAWzh4C/giDsseVcxLDZHURATNhIt62FZZncmtZyP7j0qoIaniabw5nu/2fVqTrPAzRmKVHkzPuOuv/1q/e8p2jbNgAAAAAAkK+X9B4AAAAAIG+CYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzAmKAQAAAAAyJygGAAAAAMicoBgAAAAAIHOCYgAAAACAzH0i9wIAADA9TV1shBA21vkHK6v2yF8dAACmomjbVjMBAEhOUxdbIYSb8fe1fen392wI3P37biTy+3/8zL++HCYfhxCeBCEzAAAJEhQDANC7pi4ugt+LXy9C4S4AvpVRR85jgBwuhcoXgfJpWbWnA/7eAADIiKAYAICVu7T64SIAvgiEb6v23M660PhSgNwFyk/Kqj1e8X8PAAAZExQDALCwuB7iIhC+CIWFwf25CJGP4q+n1loAALAIQTEAANdq6uJmDIK3LwXDmyqXrMsBcjd5fGyNBQAAVxEUAwDwQ54JhS8mhXPaGzxljy+C4y5EFh4DAHBBUAwAkLl4sdzlYFgonI+Ly/SOLqaPy6p9kntRAAByJCgGAMhInBa+HAzbJ8yzTi6Hx6aOAQDyICgGAJiwS8HwxZe9wszr7NLEseAYAGCiBMUAABMTV0nsCIZZk8vB8aFVFQAA0yAoBgAYuaYuti5NDN/RT3p2cik0PlJ8AIBxEhQDAIxQUxc7l6aGXT5HKs4vQmNrKgAAxkVQDAAwAk1dbMRQeMfUMCNyEkPjbtr4WOMAANIlKAYASFQMh7tgeNeuYSbgLIbGB0JjAID0CIoBABIiHCYT55cmjQ81HQBgeIJiAICBCYfJ3PmlSWOX4QEADERQDAAwAOEwPJf1FAAAAxEUAwD0pKmLmzEcdiEdXK8Lje/H9RSn6gUAsF6CYgCANWvqYjtODncB8Q31hrk97qaMY2j8RPkAAFZPUAwAsAaXVkvshRBuqTGsxMU+4/tWUwAArJagGABghZq6uNg7bLUErNfJpdUUpowBAJYkKAYAWFKcHt6NX6aHoV+mjAEAVkBQDACwoEu7h++qISThJAbGB9oBADAfQTEAwByaurgZdw/vmx6GZJ3HtRQHZdWeahMAwPUExQAAM7i0XqK7nO6GmsFoPIyB8ZGWAQC8mKAYAOAKTV1sxXDYegkYt8cxMLaWAgDgOQTFAADPEfcPd+slbqsPTMpZ/P/tw7Jqn2gtAMD3CIoBAC5p6mLX/mHIwsUe4/sCYwAAQTEAwFMCYsiWi+8AgOwFQTEAkLOmLm6GEHYExEDUXXy3LzAGAHIkKAYAshMD4r34dcPfAOAZAmMAIDuCYgAgGwJiYE4CYwAgG4JiACALdhADSxAYAwCTJygGACZNQAysyMWld/fLqn2iqADA1AiKAYBJaupiJ4Y6AmJglQTGAMAkCYoBgElp6mI7ThDf1llgjbrAeK+s2gNFBgCmQFAMAExCUxcbccrvjo4CPTqLgfGhogMAYyYoBgBGramLm3GC+As6CQzocQyMjzUBABgjQTEAMFpNXezFkPiGLgKJeBgDY/uLAYBRERQDAKMT9xAfuKgOSNR5vOxuX4MAgLEQFAMAoxH3EB+4qA4YiW5/8W5ZtUcaBgCkTlAMACQv7iHu1ky8rlvACD2OgfGp5gEAqXpJZwCAlDV1sRNCOBYSAyPWnYL4/5q6sIoCAEiWiWIAIElxzcT9EMIdHQImxDoKACBJgmIAIDlx6q5bNXFDd4CJehQD4ycaDACkQFAMACSjqYuteFndpq4AGTgPIeyXVXtfswGAoQmKAYDBxcvquiniL+gGkCGX3QEAg3OZHQAwqKYutuNldUJiIFcuuwMABmeiGAAYhCligOc6idPFx8oDAPTJRDEA0DtTxAAv1O1o/7rpYgCgbyaKAYDemCIGmIvpYgCgN4JiAKAXcYr4IIRwS8UB5vLFsmrvKxkAsE6CYgBg7Zq6uG+KGGApj+N08akyAgDrICgGANamqYutOEW8qcoASzsPIeyVVXuglADAqgmKAYC1aOpiL4TwZdUFWLlHcbr4idICAKsiKAYAVipeWHcYQritsgBrcxbD4iMlBgBW4SVVBABWJV5YdyokBli77mLQrzV1sa/UAMAqmCgGAFbChXUAg3HRHQCwNEExALCUpi424qoJF9YBDOc8hsWHegAALMLqCQBgYU1d7IQQjoXEAIO7EUL4SjzdAQAwNxPFAMBCrJoASFa3imKnrNonWgQAzEpQDADMpamLm3HVhAvrANJ1HsPiIz0CAGZh9QQAMLOmLrZCCKdCYoDkdasovtbUxZ5WAQCzMFEMAMwkhg1fVi2A0XkUL7qzigIAeCFBMQBwpbhqottHfFelAEbrJIbFx1oIADyPoBgAeKEYEnf7LTdVCWD07C0GAF7IjmIA4Lku7SMWEgNMg73FAMALCYoBgB/R1MVuCOHrMVQAYFq+3NTFgZ4CAJdZPQEA/JCmLrp9xF9QFYDJ6/YWb7vkDgAIgmIA4ELcR9xNmN1RFIBsnMW9xS65A4DMCYoBAJfWAeStu+Rut6zaw9wLAQA5s6MYADLn0jqA7HX76L8S99MDAJkSFANAxpq62ImTxC6tA+CBS+4AIF9WTwBApuLk2AP9B+AZD0MIey65A4C8CIoBIENNXdwPIXxB7wF4gZMQwrawGADyISgGgMzEY8V39R2AawiLASAjgmIAyERTFzdDCF1IfEfPAZjReQyLjxUMAKZNUAwAGYghcXdp3aZ+AzAnYTEAZOAlTQaAaRMSA7CkG93PkaYudhQSAKZLUAwAE9bUxVYI4VhIDMCSurD4K01d7CokAEyT1RMAMFExJD6KD/cAsCr3yqo9UE0AmBYTxQAwQUJiANbogcliAJgeQTEATIyQGIAedGHxnkIDwHRYPQEAEyIkBqBnD8uqNV0MABNgohgAJkJIDMAA7jZ1YV8xAEyAoBgAJiDuihQSAzAEYTEATIDVEwAwcjEkfqCPAAzMGgoAGDFBMQCMWFMXOyGEr+ghAIkQFgPASAmKAWCk7CQGIFHCYgAYITuKAWCEhMQAJMzOYgAYIUExAIyMkBiAEejC4j2NAoDxsHoCAEZESAzAyNwrq9Z0MQCMgIliABgJITEAI/SgqQv7igFgBATFADACQmIARkxYDAAjYPUEACSuqYubMSTe1CsARuzVsmoPNRAA0iQoBoCECYkBmJDzEMJ2WbXHmgoA6bF6AgASJSQGYGK69UlHcZ0SAJAYQTEApOtASAzAxFyExRsaCwBpERQDQIKauuhC4jt6A8AEdWHxYTw5AwAkQlAMAIlp6mI/hHBXXwCYsM04WSwsBoBECIoBICFNXeyGEF7XEwAy0IXF9zUaANJQtG2rFQCQgKYudkIIX9ELADLzsKzaXU0HgGEJigEgAfEG+KO4txEAcnOvrNoDXQeA4QiKAWBgcT/jqZAYgMy9WlbtYe5FAICh2FEMAAOKIbFJYgAI4SCesAEABiAoBoBhHcTLfAAgd91L06P4EhUA6JmgGAAG0tRFd9P7HfUHgO8TFgPAQATFADCApi66292/oPYA8CO6kzb3lQUA+iUoBoCexf2LHoAB4MXuNnWxrz4A0J+ibVvlBoCexKO0py6vA4CZvFpW7aFSAcD6mSgGgH4dCYkBYGYH8SQOALBmgmIA6ElTFwdx7yIAMJsbMSx2uR0ArJmgGAB6EC+vu6vWADC37iXrgbIBwHoJigFgzeKR2QfqDAALu+NyOwBYL5fZAcAaxaOyxyGEW+oMAEt7pazaI2UEgNUzUQwA63UoJAaAlTls6mJDOQFg9QTFALAm8YjsbfUFgJW5EV/CAgArJigGgDVo6mI7hPC62gLAym02dXFfWQFgtewoBoAVi3uJT+PUEwCwHq+WVWu6GABWxEQxAKzeoZAYANbuwL5iAFgdQTEArJC9xADQG/uKAWCFBMUAsCL2EgNA7+wrBoAVsaMYAFbAXmIAGNQrZdUeaQEALM5EMQCsxoGQGAAGcxhf2gIACxIUA8CSmrrYCyHcUUcAGMyN+NIWAFiQ1RMAsISmLrZCCEemiQEgCV8sq9bOYgBYgIliAFiOlRMAkI79+BIXAJiToBgAFtTUxX5327r6AUAyrKAAgAUJigFgAXFa6XW1A4DkbMaXuQDAHOwoBoA5xVvVj0MIt9QOAJL1ubJqj7UHAGZjohgA5rcvJAaA5B3El7sAwAwExQAwh6YutkMIX1AzAEjeZny5CwDMwOoJAJiRlRMAMEqvlFV7pHUAcDUTxQAwOysnAGB8DvQMAK4nKAaAGVg5AQCjdaupCysoAOAaVk8AwAyaujg1TQzJexx/g0/impgLx/F/9jzHZdX+0P+uqYutEMKLLsDavvTPG/Hr4p99j4C0fa6s2mM9AoDnExQDwDXiFNLr6gSDOo+B7+mzX2XVnqbSmrjLfCv+y+0YOG8JkiEJJ2XVbmkFADyfoBgArhAnC7+uRtCbi0D4IhQ+ft7U71jF7ykbMTzeFiBD794oq9YaCgB4DkExAFyhqYvulvTbagRr062LOLoUCCczHdyXS1PI2/HXLeExrE33Mmorx+81AHAdQTEAvEBTF3shhC+rD6zMeQyFn37ZFfpiTV1sXAqOu183U/29wgg9Lqt2W+MA4IcJigHgOeKEXzdtdEN9YGGC4RWJ35N2Ymi8beIYlvZqWbWHyggAPyAoBoDnaOqie3i8ozYwt5MYDB+WVXukfOsRJ4534pf1ODC/7kXWxlT2nwPAKgiKAeAZTV1003pfUxeYWRcOH8Rw2N7Pnj0zbbzjJATM7M2yaveUCwC+R1AMAM9o6uLUsW64lnA4UU1d7FyaNhYaw9U+Zy0OAHyPoBgALmnqYj+E8LqawHMJh0emqYvdGBhbpQPP52I7AIgExQAQxZ2fxybw4Iecx3D4wNTdeMX1FLvxazP3esAz7pVVe6AoAOROUAwAUVMX3UPiXfWApx7HcFh4MjFNXWyFEPaspoDvc7EdANkLgmIA+B4X2MFTF9PD962WmL5Ll+Dt28sO4Y2yaveVAYCcCYoB4HuBybHj2GTsLIaFhybq8hRflu3ZZUzm/rCXZADkTFAMQPbiZU8Pcq8DWerWS+yXVXuk/YQf7Grft4aHTD0qq3ZH8wHIlaAYgKzFo9en9nSSmYdx/7CAmOeK3xv34pfvj+TkFd8bAcjVSzoPQOaEIOTkYTxavSsI4SrdCpK4r7WbMH4j7q+GHNzXZQByZaIYgGzFI9bHgmIy8DCumLB7k4WYMCYz98qqPdB0AHIjKAYgW01dHNjDycQ96oI9ATGrIjAmE90Fn1su9wQgN4JiALLU1MVWCOHrus9EuaSOtYqB8X0v25iwN+L6FQDIhqAYgCw1ddEFaLd1n4k5ixPEhxpLH+IKny4wvqPgTEy3l3vDVDEAOREUA5Cdpi62Qwhf03km5DxOELuEiUHE76vd379NHWBC3iyrdk9DAciFoBiA7JgmZmIexiliU28MrqmLLlTbt7+YCfnD9rwDkIuXdBqAnDR1sSMkZiJOQgivlFW7KyQmFXGqfSO+wIApsKcYgGyYKAYgK01ddFNBt3SdEbNmglGwjoIJMVUMQBZMFAOQjaYudoXEjNyjEMKWkJgxKKv2qKzarRDCGxrGyJkqBiALJooByIZpYkasmyLuVkwcaiJj1NRFFxgfmC5mxEwVAzB5JooByIJpYkasmyLeEBIzZmXVHpsuZuRMFQMweSaKAciCaWJGyBQxk2S6mBHrLhA90kAApspEMQCTZ5qYEXocdxELiZkc08WM2J7mATBlJooBmDzTxIzMF11WRy6autiO08W+RzMWdhUDMFkmigGYNNPEjMhZCOFzQmJyEo/xb8Vd3DAGdhUDMFkmigGYNNPEjMSjuI/4iYaRq6YuumP9X/YXgBEwVQzAJJkoBmCyTBMzEt2qiR0hMbmL0/Sfi9P1kDJTxQBMkqAYgClz6QwpO7dqAn5Yd9FdXEXxWGlI2N2mLjY0CICpERQDMEnxgqRN3SVRJyGEjRiKAZd00/Vl1Xbfw99UFxJmqhiAybGjGIBJauqiuyDptu6SoIdl1e5qDFwvrhDqpu5vKBcJKq0NAmBKTBQDMDlxmlhITIruCYlhdmXVHoQQtuOqFkiNFVcATIqgGIApEsSRmi7kejWGXsAc4oqWjbiyBVKy19TFTR0BYCoExQBMSrxc5q6ukpAuJN4uq/ZQU2Ax8Xh/N1n8SAlJSLcSZUdDAJgKQTEAU+NyGVLi0jpYkXjJXRfKPVRTEuJzBwCTISgGYDLi8U+TPaTiJE4Su+gIViju+X5DTUnErXjpIgCMnqAYgCnZdTM+iXhYVu2WkBjWo6zaborznvKSCEExAJMgKAZgStw+TgoexolHYI3i5ZDCYlJwu6mLLZ0AYOwExQBMQjz2eUs3GZiQGHoUw+JX46WRMCQvqwEYPUExAFMhnGNoQmIYQFm1h90+cGExA7sb70oAgNESFAMwek1dbHTHPnWSAd0TEsNwyqo9FhaTAFPFAIyaoBiAKdjXRQZ0Lx5/BwYkLCYBXhgCMGqCYgBGLR7z3NFFBiIkhoQIixnYraYufCYBYLQExQCMXfdAdkMXGcBDITGkR1jMwEwVAzBagmIAxs4+QIbg4jpIWAyLTXYyhDvx7gQAGB1BMQCj1dTFVghhUwfpmZAYRqCs2qNuPYxeMQA/IwAYJUExAGNmmpi+CYlhROJ6GGExffNzAoBRKtq21TkARideYndqPzE9OimrdkvBYXyauuheLH5Z6+jRq2XVHio4AGNiohiAsXKJHX06iZdjASNUVu397kSA3tEjU8UAjI6gGICxsnaCvpx3IXFZtU9UHMYrro15pIX0xKV2AIyOoBiA0YkPXi6xow9CYpiW3XhCAPqwo8oAjImgGIAxMk1MX3bLqj1WbZiG+NJnO74EgnXzeQWAUREUAzBGJnTowxddRATTIyymR7eaunAJKgCjISgGYFSauuhC4lu6xpo9jJdfARMUTwqY9qQP/p4BMBqCYgDGxjQx63biwR6mr6zagxDCG1rNmvncAsBoFG3b6hYAo9DUxc0QwmkI4YaOsSbdUfStsmpPFRjy0NRFt2LmjnazRq9aZQTAGJgoBmBMdoTErNmOkBiysxtCONN21shUMQCjICgGYEw8aLFO3eV1RyoMeYmX2+243I41uhtPRQFA0gTFAIxCfMByNJh1eeTyOsiXy+3ogZfdACRPUAzAWHjAYl3O4tFzIGPxcrtH/g6wJj7HAJA8QTEAY+EBi3XZjUfPAewrZl3uWD8BQOoExQAkz9oJ1ugNe4mBC5f2FcM6+LsFQNIExQCMgQcr1uGkrNp9lQUui/uK31AU1sDnGQCSJigGYAw8WLFq5/5eAS8SXyI9ViBWzPoJAJImKAYgadZOsCb7ZdWeKi5whd34UglWyUtKAJIlKAYgdR6oWLXHZdXeV1XgKvFlkvU0rJrPNQAkS1AMQOo8ULFK53FKEOBa8aWSFRSs0rZqApAqQTEAqbN2glWycgKYlxUUrNKNpi68BAcgSYJiAJLlQYoVs3ICmJsVFKyBzzcAJElQDEDKPEixKlZOAAuLL5lOVJAV8fkGgCQJigFImQcpVuW+lRPAkrxsYlW69RNbqglAagTFACQpPkDd0B1W4KysWsfGgaWUVXscQnhTFVkRL8MBSI6gGIBUeYBiVUwBAquy72I7VsTnHACSIygGIFUeoFiFR2XVHqkksApl1T4JIewpJiuw2dTFhkICkBJBMQDJaeriZvcApTMs6VygA6xaWbUHIYTHCssKbCsiACkRFAOQItPErIIL7IB18RKKVRAUA5AUQTEAKfLgxLLOuqBYFYF1iBfbPVRcluTFOABJERQDkCIPTixrP+4SBVgXF9uxrBtNXWypIgCpEBQDkJT4wHRDV1jCSdwhCrA2cbWNkwssy8txAJIhKAYgNdZOsCy7Q4G+3DdVzJJ87gEgGYJiAFLjgYllPC6r9kgFgT7EFTemilnGbdUDIBWCYgBSIyhmGfuqB/SprNr9eIEmLKSpC599AEiCoBiAZNhPzJJMEwND8ZKKZQiKAUiCoBiAlLjQhWUIaoBBxAs0TRWzKEExAEkQFAOQki3dYEGmiYGheVnFouwpBiAJgmIAUmKihkUJaIBBmSpmGfYUA5ACQTEASbCfmCWYJgZScV8nWJCgGIDBCYoBSIUHJBZlmhhIRTdVfK4bLMDnIAAGJygGIBUekFjEiWliIBVl1T4xVcyC7CkGYHCCYgBS4SI7FiGQAVLj+xILiWu4AGAwgmIABtfUxUYI4ZZOMKezeHkUQDLiVPFDHWEBTlcBMChBMQApMEHDIoTEQKrsTmcRPg8BMChBMQApMEHDIhzvBpJUVu1pCOGx7jAnn4cAGJSgGIAUmKBhXg/j8W6AVDn1wLxuNXVxU9UAGIqgGIAUuOmbeZkmBpIWd6if6RJz8vIcgMEIigEYlBu+WcBJWbXHCgeMgKli5mX9BACDERQDMDRBMfMyTQyMhaCYeflcBMBgBMUADM0DEfM6VDFgDOKldo80izn4XATAYATFAAzNAxHzcIkdMDZebjEPF9oBMBhBMQBDc5Ed8xC4AKMSL7U71zXm4CU6AIMQFAMwGBfZMaezsmoFxcAY+d7FPFxoB8AgBMUADElQzDwELcBYuYSTefh8BMAgBMUADGlD9ZnDgWIBY1RW7XF3KkLzmJHPRwAMQlAMwJAcrWRWZzFoARgrpyKY1aZKATAEQTEAQzIxw6wELMDYORXBzJq68DIdgN4JigEYRFMXN0MIt1SfGQlYgFGzfoI5eZkOQO8ExQAMxUUtzMraCWAqnI5gVoJiAHonKAZgKB6AmJVgBZgKpyOYldUTAPROUAzAUATFzEqwAkxCPB1xrpvM4KYiAdA3QTEAQzEpwyzOrZ0AJsYpCWaxqUoA9E1QDMBQTBQzC4EKMDW+rzGTpi7c5wBArwTFAAzllsozgyNFAibG9zVmZf0EAL0SFAPQOxMyzMHkHTApZdU+CSE81lVmYE0XAL0SFAMwBBMyzOIkBioAU2OqmFn4vARArwTFAAzBhAyzEKQAU+X7G7NwAguAXgmKARiCCRlmYe0EMEll1XZB8bnucg0X/wLQK0ExAEMwIcO1YpACMFW+x3EdF/8C0CtBMQBDMFHMdVz0BEzdsQ5zHRcAA9AnQTEAQ9hUda5h0g6YOt/nmIWX6wD0RlAMQK+auvDAwyxM2gGTZr0OM7KnGIDeCIoB6JsjlMxCgALkwJodriMoBqA3gmIAIDVnZdU+0RUgA05PcB1BMQC9ERQD0LdtFecapomBXPh+x3UExQD0RlAMAKTGhB2QC9/vuI67HQDojaAYgL7ZUcx1BCdAFsqqPQ0hnOs2V9hUHAD6IigGoG8mY7hSWbWOYgM58XIMAEiCoBiAvgmKucqZ6gCZERRzpaYunMYCoBeCYgD65gglVxGYALnxfY/reMkOQC8ExQBASgQmQG5OdRwASIGgGIDeNHWxodpcQ1AMZMVedmawrUgA9EFQDECfBMVc54kKARmynx0AGJygGABIhsk6IFPWTwAAgxMUA9AnE8VcxUQdkCtrd7iK1RMA9EJQDECfBMVcxUQdkCtrdwCAwQmKAYBUCIqBXFm7AwAMTlAMAKRCUAwAP8qJLAB6ISgGoE9bqs0VBMVAllzkyTVuKRAAfRAUA9Cnm6rNFQTFAAAAAxEUAwCpcJkTkLMT3QcAhiQoBgCSUFbtsU4AGfOyjBdq6sKeYgDWTlAMQJ885ADA8wmKuYrPUACsnaAYgD65jIUXceQayJ1TFQDAoATFAEAKTNIBAAAMSFAMAAAwPC/MAIBBCYoBgBSc6gKQOasnAIBBCYoBgBQIigHgxVxmB8DaCYoBAAAgbYJiANZOUAxAL5q62FZpAHghO4oBgEEJigEAAAZWVq0dxQDAoATFAEAKjnQBAABgOIJiAAAAAIDMCYoBAAAAADInKAYAAAAAyJygGAAAAAAgc4JiAAAAAIDMCYoBAAAAADInKAYAAAAAyJygGAAAAAAgc4JiAL8qbz0AACAASURBVAAAAIDMCYoBAAAAADInKAYAAAAAyJygGAAAAAAgc4JiACAF27oAAAAwHEExAADAwJq62NIDAGBIgmIAelFW7ZFKA8AL3VQaAGBIgmIAAABI2xP9AWDdBMUAQApM0gHAix2rDQDrJigGAFJgNyeQu43cCwAADEtQDAAAMDxBMQAwKEExAJACqycAAAAGJCgGoE9nqs0LbCoMkDkTxQDAoATFAPTpVLUB4LkExVzFZygA1k5QDAAkoakLIQkAPEdZtYJiANZOUAwApEJQDOTstu4DAEMSFAPQpyeqzRVcaAcAADAQQTEAfTpWba6wpThAjpq62NZ4rnCuOAD0QVAMAKTCRDEA/Cgv2gHohaAYAEiFiWIgVyaKAYDBCYoB6JMbu7mKy+yAXDlRAQAMTlAMQJ8ExVzlluoAmXKigqscqQ4AfRAUAwDJaOpCWALkyIkKAGBwgmIA+mSimOsIS4AcOVEBAAxOUAxAb8qqFRRzHRPFQFaaunCRHdexegKAXgiKAYCUCIqB3DhJAQAkQVAMQN9OVJwrCIqB3AiKuc4TFQKgD4JiAPrmYYer2NMJ5MbqCa5UVu2xCgHQB0ExAH0TFHMl+zqBzDhJAQAkQVAMQN9MxXAdoQmQhaYuurUTN3SbK1jZBUBvBMUAQGoExUAufL/jOk5iAdAbQTEAfTtSca4hOAFy4fsd1zlVIQD6IigGAFKz2dTFTV0BMmAnO9cRFAPQG0ExAL0qq9ZEMbMwZQfk4LYucw2rJwDojaAYAEiRKTtg0pq68H2OWbgEGIDeCIoBGMJjVecaAhRg6pycYBYmigHojaAYAEiR49jA1HkhxrXKqjVRDEBvBMUADMGeYq7lWDYwcb7HcZ0zFQKgT4JiACBVQhRgkpq66NZO3NBdrnGqQAD0SVAMwBBMFDOLHVUCJsqLMGYhKAagV4JiAIbgwYdZbDZ1cVOlgAnyIoxZ+LwEQK8ExQD0rqxaDz7MytQdMCnxBZgLO5mFi+wA6JWgGIChnKg8MzB1B0yNF2DMyot1AHolKAZgKE9UnhkIioGp8X2NmZRVa6IYgF4JigEYigvtmMWNpi62VAqYEBPFzOJMlQDom6AYgKE4TsmsdlUKmIL44uuWZjIDn5MA6J2gGICheABiVo5pA1PhxRezcvIKgN4JigEYRFm1HoCY1a2mLjZUC5gAL76YlRfqAPROUAzAkOzfY1bCFWDUrJ1gToJiAHonKAZgSG7zZlaOawNj5/sYM3PyCoAhCIoBGJKgmFltxmk8gLFyMoJZnagUAEMQFAMwJEEx8zCNB4yStRPMydoJAAYhKAZgSIJi5mEaDxgrL7qYh89HAAxCUAzAYMqqNTHDPG41dbGtYsAICYqZh/3EAAxCUAzA0B7rAHMQtgCj0tRFdxrihq4xBxPFAAxCUAzA0DwMMY+dpi5uqhgwIl5wMY/zsmqfqBgAQxAUAzA0QTHzuGFXMTAWTV1shBDuaBhz8LkIgMEIigEYmj18zGtPxYCRME3MvHwuAmAwgmIABhUvtDvXBeaw2dTFloIBIyAoZl6CYgAGIygGIAWOWTIvU8VA0uIldrd0iTn5TATAYATFAKTA9AzzcqkdkDovtJjXmYvsABiSoBiAFJieYV43HOkGUhUvsbutQczJ5yEABiUoBiAFJopZhGk9IFX7OsMCfB4CYFCCYgAGF49ZnukEc7rV1IWpYiApcS3Ojq6wAEExAIMSFAOQCg9HLEJQDKRmL67HgbmUVWv1BACDEhQDkApBMYu43dTFtsoBCbEWh0U8VjUAhiYoBiAVgmIWZRcokIS4Dsc0MYvwOQiAwQmKAUhCWbWnIYRz3WABpoqBVHhxxaIExQAMTlAMQEo8JLEoR72BQcVp4lu6wCLKqvUZCIDBCYoBSImHJBZ1p6mLDdUDBmSamEXZTwxAEgTFAKREUMwy7qseMATTxCzJ5x8AkiAoBiAZZdUe21PMEu7YVQwMxDQxyxAUA5AEQTEAqTnUEZYgrAF6ZZqYZdlPDEAqBMUApMbDEsu4baoY6EtTFzetvWFJ9hMDkAxBMQCpERSzLFPFQF/2Qgg3VJsl+NwDQDIExQAkpaza0xDCma6whNvxKDjA2sRp4j0VZklWbgGQDEExACny0MSyTBUD63bfNDFLOo8X+QJAEgTFAKTIMUyWdaupC2ExsBZNXWyEEO6qLkvyeQeApAiKAUiRBydWYS8eDQdYtQMVZQWcoAIgKYJiAJJTVu2TEMIjnWFJN+LRcICVaepip9uFrqKsgBfjACRFUAxAqjw8sQp3m7rYVklgFeIpBS+gWIWTeIEvACRDUAxAqhzHZFWEOsCq7HU70FWTFfBCHIDkCIoBSFKcsjnTHVZgs6mLPYUElhEvsHtdEVkRe64BSI6gGICUmSpmVfZjyAOwKMEeq3JeVu2xagKQGkExACkTFLMqN4Q8wKLiqQQX2LEqPt8AkCRBMQDJKqu22993rkOsyO2mLnYUE5hHPI2wr2iskKAYgCR9QlsASFz3MHVXk1iRgy70Kav2iYICM7ofTyUwoHc+/nz45nc/s7bfwH/2k/8sfKr4d738AcuqFRQDkCRBMQCpExSzShcrKEwWA9eKpxDuqNRqfOPDX/z+f87//d7Pff+f/9VHfzD8zsc/+f1//X9+pwzf/LjvR9Vf+pH/yZ/8iQ/CH/nEt7//r//THz8PP/OJ7x10+r0/9mH47Cf/zdN//j0/9m74zI9/bdb/oker+f0CwOoVbdsqKwBJa+riiWkuVuxVE13AVeLKiWM/f673Qfvp8G+/8/PhvY9/KvzrD19++u//Fx/8oae//uv/+HvDb3z0qZR/+yu1/anz8PuLj8Lv/7HvhJ/9iX//9D/6T/3UN57++nOf/Gr3y72yau3MByBJgmIAktLUxVYI4WYI4fKv2x7UWbFuJGyrrNpThQWep6mLIxfY/cBvfveV8P7Hv+/pJPC3f/eT4Rvf+U/C77Q/EY4+8ON5AY/j/0n3d+xJfCFx+vaD1/xMAmBQgmIAetfUxUUA3H1tXPr1lm7Qo8dl1W4rOPCspi72QghfzrEw3XqI3/7uT4ff+qh8OhWc20RwAh5fCo8vAuTj3IsCQD8ExQCszQsCYdNZpOSLZdXe1xHgQjzZ8vWpF6SbEP4PH/3M01URAuFROLkIjuMk8vHbD15zMSsAKyUoBmAl4i7HrUurIkwIMxafK6vWtBZw8YKzC+E2p1SNLhQ+/fCz4V99+OmnKyO++v5PJ/C7YgXOLk0eC48BWJqgGIC5XZoU3o5fW3YIM2JncV+xh2vIXFMX3SVjd8dche5iuf/3/e3vTwoLhbNzdhEax+D4KPeCADA7QTEA14rHcLcuhcKTmrSCEMKjsmp3FALy1dTFbgjhwdgKcDEtfPz+RvgnH7xsfQTP8/hSeHxk6hiAFxEUA/AjYjC8fenLtDA5sK8YMhV/7h2N4eddFwz/P+/9yXD8wa3wD9//mfDNjz+RwO+KkTmJf9+PBMcAXCYoBkAwDD9gXzFkJvW9xO98/Pnwf737XwiGWaeL4PjQqgqAvAmKATIUL567CIV3BMPwfefdRYz2FUM+mro4DCHcSeUPfLFj+J9++09YJcFQHl2aNvbyFCAjgmKATDR1cREKb9sxDFc6Kat2S4lg+pq62AshfHnoP+jFOol//O2fc/kcqekuxzuMofGh7gBMm6AYYKLiUdodU8OwkIdl1e4qHUxXUxfdz8avDPUH/Pp7vxRO3v8j4R+891lTw4zJoxgcH9ptDDA9gmKACYkrJXbi1229haXcK6v2QAlheoa4vK5bKfHPv/0L4fj9jfBr396wa5gp6HYbH8TQ+FRHAcZPUAwwcpfC4V0rJWDlXimr1sU+MCF9Xl53EQ7/+rf/WPjVdz/jrxFTJjQGmABBMcAICYehN93ldttl1brMByaiqYvjdf7sFA6D0BhgrATFACMhHIbBdBf5bJVVaxcjjFxTF114dXcdf4pu5/A/+p3PC4fhh12Exgd2GgOkT1AMkLBLF9LtCYdhUCdxsthDLoxUUxf3QwhfWOXv/hsf/mL4385/3s5hmI2L8AASJygGSFC8ib2bHL6jP5CMx2XVbmsHjE9TF93P1Aer+I2/8/Hnw1ff+YXwD977bPiNjz7lbwPM7zwGxt2UsXsAABIiKAZIRFwtsRcD4t5uYQfm8rCs2l0lg/FYRUh8sXf4759vhq++/9O6D6vTrXe6b58xQBoExQADsloCRklYDCPR1EV3CuBri/5uf/O7r4TDd/6s1RLQj0dxyvhQvQGGISgGGEBTF1sxHN4xPQyj9GZZtXtaB+mKP2uP5v05ezE9/NaTnw9HH/gRDQM4u3QBniljgB4JigF6FI+/mh6GabhXVu2BXkJ6FgmJTQ9Dkh7aZQzQH0ExwJrF3cMXAbHRJJgWYTEkZt6Q+Nff/WW7hyF9J90u47cfvOZnLsAaCYoB1iTuRewC4rtqDJMmLIZEzBoSd+sl/t47fz78nXf/RPiNjz6lfTAe5/HyO2spANZAUAywYtZLQJaExTCwWULidz7+fPhfv/lq+JXzn9UuGL+Hccr4WC8BVkNQDLACTV3cjOFwFxLfUlPIkrAYBnJdSPyND38x/N3mvwy/+u5ntAim53EIYd8eY4DlCYoBlmD/MPCMN8qq3VcU6M9VIbH9w5AVe4wBliQoBlhADIj37R8GnuNhWbW7CgPr19TFTrer9NmQuAuI/+a3/oz9w5CnszhhLDAGmJOgGGAOAmJgRsJiWLN4J8CDi/+W7oK6f/7tXxAQAxfO4uf2w7cfvPZEVQCuJygGmIGAGFjAo241TVm1Hk5hxS6HxF1A/Pfe+fPhbz3ZDN/8+BNKDTzrvFtJEddS+JkMcAVBMcAVBMTAkrp9idvCYlidpi664+R3BcTAnATGANcQFAM8h4AYWKGTOFl8rKiwuKYubnYBzwftp+8KiIEl2GEM8AKCYoBLBMTAmpzHyWJhMSwghsRHv/7uL2/aQQysiMAY4BmCYgABMdCfe2XVeiCFOTR1sfV//M5/+7//T+/8539AQAysQRcY77394LVDxQVyJygGshYnlPbi143c6wH04s2yaveUGq73K1/6K3/tb7/7x9/4lx998iXlAtbscZwwPlJoIFeCYiBbTV3sC4iBgXQPozsuuYPne/neW9uf+8n3Dr7+nZ+6pURAzx7FCeNThQdyIygGstPUxU688djDJzCksxgW21sM0cv33tr4qZd+939473df+iU1AQb2Zpww9lIXyIagGMhGUxfbcQ/xbV0HEtFdcrdnbzG5e/neWxeroF7PvRZAUs5jWHxfW4AcCIqByXNRHTACD2NgbGqJ7Lx8763deNLHKiggVd0poF37i4GpExQDk2YPMTAiJ91DqFUU5KLbQxwD4k1NB0bicQyM7S8GJklQDExSXDNxYA8xMDJPj7iWVeuIK5PV7SGOAfEdXQZG6o3u+5j9xcDUCIqBSYlrJjx8AmP3KE4XewBlUl6+95aTPsBUdOso9t5+8NqhjgJTISgGJsOaCWBizmNY7AGU0YtrJpz0AaboUQyMraMARk9QDIyeNRPAxL0Z11GYLmZ0Xr731s34M9pJH2DKzuMqin1dBsZMUAyMVlMXN+Oaibu6CEzc0+OtposZk5fvvdWd8tl30gfIyEm87M7FtMAoCYqBUWrqYidOKHn4BHJidzHJe/neW1vxRe5t3QIy9fQ0kMvugLERFAOjEi+rO/DwCWTsPE4XH/hLQGriZXWvawzA09NA3XTxkVIAYyEoBkajqQtHWAF+4HEMjB1vZXBxirh7ebGpGwA/xHQxMBqCYiB5pogBruSyOwYTL6vrXuJ+QRcAXsh0MTAKgmIgaaaIAWZiHQW9e/neW9vxRe4t1QeYieliIGmCYiBJpogBFnISA2MTS6zVy/feum+KGGAhpouBZAmKgeQ0dbEbb0s3RQywmG5/8W5ZtafqxyrZRQywMm++/eC1PeUEUiIoBpLR1MXN+PB5R1cAVuJh3F8sMGZpL997q1sF9bpKAqzMSZwudjEtkARBMZCEpi66PYeHpogB1kJgzMJevvfWRvwZbYoYYD2++PaD1+6rLTA0QTEwuKYu7DkE6IfAmLn8mb/4v/yl3/qPP/4/ftgWn1I5gLXq1kbtuOgOGJKgGBhMUxf2HAIMQ2DMlX7lS3/l1j95/7P/6OiDG39UpQB6cx7DYhfdAYMQFAODcGEdQBIedd+Ly6r1QMpTTV1s/Iv3/txf/Rv/4b/6b/7lR598SVUABuGiO2AQgmKgV/HCui4gvqvyAMk4iYHxgZbkKZ7y2fu1b33p7v63/nTu5QBIwUmcLnb6B+iNoBjojVUTAMk7i9+nD6ylyEM84bP3Qfvpzb/+dhW++v5P514SgJR0qyh2337w2qGuAH0QFAO9sGoCYHQexcDYw+nEdOslunC4Cx+6n8vf+PAXw198+78O3/z4E7mXBiBVVlEAvRAUA2tl1QTA6JkynoD483gnhsO3L/5Ev/atLwWrJgBG4XFcRfFEu4B1ERQDaxMnlg6tmgCYjJP48u+wrFoPqiPQ1MVODIh3Lp/q+aD9dHjzt/5y+NV3P5N7iQDGpFtFsf32g9eOdQ1YB0ExsBbxwfTAqgmAyXoUXwYKjRPzonD4wm9+95Xw3739F8JvfPSp3EsFMFZffPvBa/d1D1g1QTGwck1d7IcQXldZgGxchMZH1lMM47pw+MKvv/vL4a/99rZ9xADj97DbN28VBbBKgmJgZeL+w26K+I6qAmTr5NKksaOxaxLXO23HYHh7lhM8f+vf//XwK+c/O9Y/MgA/6iTuLfaSFlgJQTGwEk1dbMWQ2D5iAC6cX0wamzZeTnwZu33pa+aft90+4v/+N18PRx/YBgUwQfYWAysjKAaW1tTFdgwCPIECcJWzi9BYcHy1ZYLhy+wjBsjGvbcfvHag3cAyBMXAUpq62A0hPFBFABZwHkPj44tfc70YL7503br0tfQJHfuIAbLz5tsPXtvTdmBRgmJgYU1ddG+s76ogACvUTR2fXgqQT6e06zjuFr7YL7wRVhQKP+vXvvWlsP+tP73q/1gA0tddMLvrkjtgEYJiYG7xOGy3auK26gHQk4sAuQuNn8QgOZRVe5RaA+Le/psxBL7869p/bnb7iP/n3/5LLq0DyNtJ3FssLAbmIigG5hInoQ5dWgfA/8/e/cDImdZ3gn8LDMH8WbuACfHWZO1waIggko0Rd1Imwm0OrQJZjRuSLDW5RO4Kp4iL2BuPMmgpLrnxCO0WmyDh4Thp7lak2jqyqRWzom3l+JNkM23dsNLmDsa9kqPcCIhNXDcEPK7usWd68NDU6fU8PfR47O7q7vrzPO/7+UgWfyKF8vOred96v+/v+T2RWQ2Ss9UQOTi/5r9ftThIl/Ka7t+1VoPfVashcDbpF6gOrQNgDYfcAZsmKAYGFjqk5h1aBwBxcWgdADexFMZQzFkcYBAvs0rAIMKhdUJiAIjM48/elf3md39bSAzAjfJnty/VGp0ZKwMMQkcxsKEQEretFADE5dErH84+8sR7VQWAjTzYbdePWSVgPTqKgXX1WpUTQmIAiM/DT94nJAZgUPfUGp1ZqwWsR0cxcEu9ViX/IXHUCgFAXD73D5/MHlp6i6oAsFmnwtziRSsH3EhQDLxEr1XJT2/PQ+IjVgcA4rHc35N9/vu/KyQGYDsWsiybEhYDNxIUAy8SQuL80Lr9VgYA4pGHxB+7eH82v+xcWQC2TVgMvIQZxcALhMQAECchMQBDlj/zna01OgcsLLBKRzFwXa9VORDGTQiJASAiF587nH3qex8SEgMwCkuhs/is1QUExcBqSJx3EnsCBYCI5CHxb373t7NLKzuUBYBRERYD1xk9ASUnJAaAOAmJARiT/Flw3hgKQFAMJSYkBoA4CYkBGDNhMSAohrISEgNAnITEAEyIsBhKTlAMJSQkBoA4PXrlw0JiACYpf0Z8rNbozKgClI/D7KBkhMQAEKc8JP7IE+9VHQBi0ei267OqAeWhoxhKREgMAHESEgMQobbOYigXHcVQEkJiAIiTkBiAyL2j266fVSQoPh3FUAJCYgCIk5AYgAQ44A5KQlAMBSckBoA4CYkBSMQuYTGUg6AYCkxIDABxuvjc4ez3vz+lOgCkQlgMJSAohoISEgNAnPKQ+De/+9vZpZUdKgRASoTFUHAOs4MC6rUq+7IsOyskBoC4CIkBKIClLMumHHAHxaOjGAqm16rszrJsTkgMAHEREgNQEPmz5lyt0dmtoFAsgmIokBAS5+Mm9qsrAMRDSAxAwewNYyiExVAggmIoCCExAMRpub8n+9T3PiQkBqBo9guLoVgExVAcJ4TEABCXPCT+2MX7s/llE6EAKKT8GXRWaaEYBMVQAL1WJb8xH1VLAIiHkBiAkjhSa3SExVAAgmJIXK9VOS4kBoD4fP77vyskBqAsjtYanROqDWmr9Pt9JYRE9VqVmSzL2uoHAHH53D98Mnto6S2qAkDZNLrtuu5iSJSOYkhUr1WZFhIDQHwefvI+ITEAZdWuNTrTqg9p0lEMCeq1Kgfy02WzLLOfFQAi8uiVD2cfeeK9SgJAmS1lWTbVbdfP+hZAWgTFkJheq7I7y7LzQmIAiMvjz96VffC7d6sKADwfFu/rtuuL1gLSYfQEJCSExDqJASAyF587nP1O99eVBQCelz+zztcand3WA9IhKIa05IcC7FczAIjHcn9P9nvd38ourexQFQD4if3hGRZIhKAYEtFrVU5kWXZEvQAgHnlI/LGL92fnru1UFQB4qSO1RueEdYE0CIohAb1WZSbLsnvUCgDi8vnv/242v2wiFACs455aozNjgSB+DrODyPValQNZlj2mTgAQl4efvC87/uQ7VQUABvOObrt+1lpBvATFELFeq7Ivy7KzDq8DgLg89vTd2W9171IVABjcUpZl+7rt+qI1gzgZPQGR6rUq+emwc0JiAIjLxecOZ/d+7/2qAgCbkz/bzlsziJegGOJ1IpwSCwBEIj+87ve6v5VdWtmhJACweftrjc6sdYM4CYohQr1W5ViWZUfVBgDi8sluMzt3baeqAMDWHXW4HcTJjGKITK9Vmcqy7BF1AYC4zP7g97NP996uKgAwHA63g8gIiiEiYS7xeXOJASAuj175cPaRJ96rKgAwPA63g8gYPQFxmRcSA0Bc8sPrfv/7U6oCAMO1KxzgDkRCUAyR6LUqDq8DgMjkh9d96nsfcngdAIzGoVqjc9zaQhyMnoAI9FqV6SzLvqQWABCXTz3xR9kXrtyuKgAwWoe77fq8NYbJ0lEME9ZrVfbl5+OoAwDE5auLHxUSA8B4zNUand3WGiZLUAyTN2cuMQDEJZ9LfN/371QVABgP84ohAoJimCBziQEgPvlc4t/r/pbKAMB4mVcME2ZGMUyIucQAECdziQFgoswrhgnRUQwTYC4xAMTJXGIAmDjzimFCBMUwGbPmEgNAXMwlBoAo7NJYBZMhKIYx67Uq+cylQ9YdAOKRzyX+1Pc+pCIAEIcjtUbnmFrAeJlRDGPUa1UOZFn2mDUHgLjM/uD3s0/33q4qABCPpSzLprrt+lk1gfHQUQxj0mtV8hlLc9YbAOLy2NN3C4kBID5GUMCYCYphfPKRE3utNwDEIx85ce/33q8iABCn/bVG57jawHgYPQFj0GtVprMs+5K1BoC4fOLiZ7PTz9ymKgAQt8Pddn1ejWC0dBTDiIWRE7bLAEBkvrr4USExAKRhttbo7FYrGC1BMYzebJitBABE4vLKwexTT/43ygEAadgbxjkCIyQohhEKIyeOWGMAiMunn5jJLq3sUBUASMc9tUZnSr1gdATFMCJGTgBAnIycAIBkGUEBIyQohtExcgIAInPxucPZfd+/U1kAIE1GUMAICYphBIycAIA4fep7H1IZAEibERQwIgazwZAZOQFJWsqy7OwNHzz/z4tb+MscyLJs7Xa4/N/v97WAyctHTswv2+wDCTmz5qPOr/n3ize5b2/F2qBpd7iHZ+7dkIT8mXufUsFwVfr9viWFIeq1KvkN66g1hWisPmSuPmCuBsCL1WZ/GA+ZAwsvklYfQlcD5X1r/uz1tYHRuLxyMPvg+XsdYAfxWH1Je/7GP912/Xwsn7LW6BxYEyKv/ddDEXw8KLsHuu26MRQwRIJiGKJeq5J3JTxiTWHsLoSHzPk1D5tnq83+VjqCJ6rXqqw+gE6tCZA9jMI2feLiZx1gB5OxGgiv/smD4Pki1KLW6Kzepw+EP+7ZMH7v6LbrY23+gCITFMOQhE7BszoCYeQW1j5wVpv9QjxsbqTXqqx9EJ0K/2oPPQwgHznhADsYi9VQeH71Ph1Td/C4hC7ktX+ExzA6C912/YD1heEQFMOQ9FqVfMvL/dYThmppzcPmfFlC4UGF8HhqTXhsniLcYLm/J3vfd/7QyAkYjQvhPj0fQmFdfbcQDt5avV9PedkLQ3Vvt10/YUlh+wTFMARhq/hj1hK2bWnNA+f8uGcIpy7sbJha80dwTOl96ok/yr5w5fayLwMMS36fnlu9T5exW3hYQtfx6j37SDH+VjAx+bVpX7ddT27sHMRGUAxD0GtV5m0pgy1bWH3o1DE8XCE4ng4PodO6lyibx5+9K/vgd+9Wd9ie1fv0nI7h0ak1Omvv10bZwead6rbr09YNtkdQDNvUa1VmsixrW0fYlFOrD50pHjiXqrD7YcZDKGXxofN/nJ27tlO9YfNOrQmH3afHLBySNx3u2XYHweAOF+WwTJgUQTFsQ+jWO69LDza0tCYYnrNckxfmG3sIpbAefvK+7PiT71RgGJxwOEJCY9iUC912fZ8lg60TFMM29FqVfGD+PdYQbil/6JwVDscthMYz4Y9OY5J3eeVg9u5vf0whYWNn8vu0cDgNa0LjY+7XcEsPdNv145YHtkZQDFvkADu4pXyW4QljtiKtcAAAIABJREFUJdIUrm3HzDQmZZ+4+Nns9DO3qSHc3IUQDs86jC5d4TA892t4qXwn4wHXN9gaQTFskQPs4EWWwkPniWqz70dZQYQZ7DOudaTksafvzn6re5eawUudDOGw+Z0FU2t03K/hxRxsB1skKIYtcIAdvOBMGC0xa0mKK4ymOBYeQnUtETUH2MGLXAi7fGaNlii+MJriuC5juM7BdrAFgmLYJAfYwQsH0x3XPVw+4UXZMQfqECMH2MEL8he5J7rtujMCSqjW6OwOYfFxs4wpsYVuu37AFwA2R1AMm9RrVfIfXPdbN0rowprxErqSSq7XqkyFwPhI2deCOOQH2H3w/L3ZpZUdKkKZnQwB8VnfArLnQ+PVw++MpaCMGt123c5H2ARBMWxC2H79d9aMkrkQuof9yOIlwnUxf4F21OowSZ/7h09mDy29RQ0onVdXfvzDZ/ov6+TXYoc3cSu1Rmcq3K8FxpRJvhNyn9E7MDhBMWxCr1WZ0z1HiQiIGdiawNhcRMbu8Wfvyj743bstPKWy++UrP37rK5b/7X9+9rUfF4IwqDVzjL3gpSwe6Lbrx1UbBiMohgGFbdaPWC9KQEDMloU57sfCH4ExY/GJi5/NTj9zm8WmFN748h9l//y1f7fwhh1Xj3zk0//mgqqzFQJjSubn7LiAwQiKYUC9VmXeVi0KTkDM0BhJwbg8euXD2UeeeK/1phTurf7ND9+3+8yH3/4/n/kTFWcYao1OftjXCc85FNzJbrs+o8iwMUExDKDXquRbqb9krSgoATEjIzBm1D50/o+zc9d2WmcK7SO7vpX92hu++p9/ZsfX69VmX1ccQ2eGMSXwDgd9wsYExTCAXquS/yDfa60omPxwhxPVZt/MLkau16roWGLovrr40ey+799pYSmsu179g+x/+OlTV3/2lf/xD6rN/gmVZtRqjc50uF979qFoznTb9SlVhfUJimEDvVYl36LStk4UzIOhi9jhN4xVmPc+6wGU7Vru78ne950/zC6t7LCWFM7bX7mcffy2v8je8Zo/XcgPCdVFzLjVGp3jzhuggA532/V5hYVbExTDOsKhTOf9QKJAzuQ/+qvNvm1XTFSvVTkWtri6vrIlDz95X3b8yXdaPAolP6juo7sXsl97w6fzv9YDdv0wSbVGZ3foLjY+iqLQVQwbEBTDOnqtSv7j/H5rRAFcCAHxnGISi/AyzgMom6abmCL6zdddzH7np/80e/3Lv5l3Ec94qUsswvzi/H69X1EogEa3XXc2C9yCoBhuQTcxBWLMBFEL4yg8gDKwz/3DJ7OHlt5iwSiEfMzEJ39mLrvjVaeXwv3aLGKiVGt07AaiCC502/V9Kgk3JyiGW9BNTAHoSCIprrsM4vLKwezd3/6YtaIQjr/hG9mvvP5Psp2VJ86Ee7ZZxESt1ujsC2cNOJyWlOkqhlsQFMNN6CYmcXlH0glzDUlRr1XxAMq6dBNTBFM7l7KP/8y/z25/xSNLYTSUwIKk1Bqd6XC/9rxEinQVwy28zMLATTnhl1TlHUkHhMSkKu+mqzb7+SiKe8NLD3hB3k0sJCZ1eRfx5372I3lIfDLLsn1CYlLUbdfzcy/yoO2UApKgvbVGZ0bh4KV0FMMNQjfbWUExCbrXXEOKRHcxN9JNTMrWdBFfCGMm5hWUItBdTKJ0FcNNCIrhBr1WZdYJ/CTGLGIKzexiMrOJSdx91XPZh974x0/trPx/n7HrhyIyu5hEmVUMNxAUwxpmE5OgB6vN/jGFo+h6rcqB8AC6X7HLSTcxKXrjy3+U/e+1L2Z3vOr0qTCL2GF1FFqt0fFyl5ToKoYbmFEML2Y2ManIZ7ceFhJTFqFjPp9dfFLRy8dsYlJ016t/kH35zc2/v+NVp/P79bSQmDLotut5UPyOPIBTcBJgVjHcQEcxBLqJSUh+YF3+wLmoaJRRr1XJf9CfcL0uD93EpOYP3vDYDz/0hj/8uLMDKKtao7M77AQ64ktA5HQVwxo6iuEndBOTggeqzf6UkJgyqzb7s6G7eMEXofh0E5OSfNTE5//xV772oTf84c8IiSmzbru+2G3X80Pu7vVFIHK6imENQTH8pJvYFn5ilo+a+IADcOB5RlGUx7+79IGyLwGJOPhTT1/9N2/6i/2//K9O/rIXuvC8brt+IoyiWLIkRMwzFgRGT4AT9YnfQhg1YbYh3ESvVclf9H3G2hRP3k387m9/rOzLQAJ+4ZXLX/va/9b4ZbWCmwujKOYdSkvEDnfb9XkFoux0FMPzdBMTq7xbckpIDLcWtncf1q1UPKcvv7/sS0AaGkJiWF8YRXHATiAipquY0ssExfDCoUhmExOjfB7xjO2rsLFqs593gBwwt7g4lvt7stmn3lr2ZSBu+cupd3Tb9Vl1gsF02/UZc4uJ1KFaozOlOJSdoBi8OSQ++YNnwzxi2JzQeZ//wD9l6dL3f17+77JLKzvKvgzEK38pdaDbrp9VI9icMLf4A3YCESE7jSk9M4optdBN3C77OhCVpTBqwoMnbEOvVck7/I5aw3RNffv/EBQTqzwknsq30qsQbF2t0TkQ5hbb3UlMfq7brhv7R2npKKbsZsq+AETleneSkBi2Lx/bknfmW8o0PXrlw0JiYnUyn7MqJIbtCx35+4yNIjJ2dVJqgmJKq9eq5NuTD/kGEIkFh9bBcFWb/dkQFtvampj/5ck7y74ExOlkmK8KDEl46TIlLCYi07VGZ7eCUFaCYsrMD31icTKExLqTYMhCWDwlLE7H48/elZ27trPsy0B8GkJiGI08LM479cNvYpi0XWYVU2aCYkqp16rsM7uSSJzMt8gLiWF0wjgXYXEiZi+9t+xLQHzykHhWXWC0wssYYTEx8GKQ0hIUU1Yu/MTgZJijCozYmrD4grWO1+WVg9npZ24r+zIQFyExjJGwmEjsrTU6ntMoJUExZWUrCZP2oJAYxiuExQfMQYzXv7v0gbIvAfHIdyB8QEgM4xfC4gctPRPmWY1SEhRTOr1WZSbMHYJJaVSbfS8rYALCmBeH5kRoub8ne/jqvrIvA3HIQ+Kpbrs+px4wGd12/Vg4kBYm5VCt0Tlg9SkbQTFlJKBjkhrhcC1gQoTFcTqz9KvZpZUdZV8GJm81JD6rFjBZoaNfWMwkyQ4oHUExpdJrVfI3gvtVnQkREkMkhMXxaS8eLPsSMHlCYoiMsJgJm641OrsVgTIRFFM23ggyKUJiiIywOB6PP3tXdu7azrIvA5M3LSSG+ISw2AF3TMIus4opG0ExpdFrVfI3gUdVnAk4KSSGOK0Jiy8o0eT8+dK7yvpXJx6Nbrs+rx4Qp3DAnbCYSdBsRqkIiikTbwKZhDwk9t2DiIWweDpsO2fM8kPsHlp6i2VnkhqhYxGImLCYCdlba3SmLD5lISimTLwJZNyExJCIarN/NnQWC4vHLD/EDiZISAwJERYzIZ7pKA1BMaXQa1Xyh/+9qs0YnRISQ1qExZPhEDsm6EEhMaQnhMXOF2CcjjrUjrIQFFMWAjvGacF3DtIUwmI7UMbEIXZM0Mluu+6fdUiXw2gZt2krThkIiim8cIidizrjkv9gnQozT4EEhcMnG2o3eg6xY0LOhI5EIFHddn3RLiDGzMtFSkFQTBnkIfEulWYM8h+qM0JiSF8Iix9UytFxiB0TsqCBAIpBWMyY7a81OgcsOkUnKKYMvPljXKbCtnWgAKrN/jEH5ozON66+v6h/NeKVh0nTIVwCCqDbrp818o0x8l2j8ATFFFqvVdmXv/lTZcagISSGQjpmBuJodBaNnWDsprrt+nnLDsXSbdfnsiy7V1kZA0ExhScopuhcyBmHB8M2daBgwigZ21qH7PLKwWx+2VQoxqoROg+BAuq26yfsAmIMdtUaHeOLKDRBMUUnKGbUzoTt6UBBrQmLGZK/WnyPpWScHuy2617oQsGFQyrtAmLUBMUUmqCYwuq1Kvmg+b0qzAhd8EMByiGMlmko93B88crbivDXIA1nuu26F7pQHnYBMWpHa43ObqtMUQmKKTIPBYzS9QNxQqchUAJhxIxtrdt08bnD2blrO5P+O5CMJS90oVzCYZX+uWfUfMcoLEExRebizSgdc3gdlE+12betdZv+cvHOpD8/SZkKoRFQIt12fd7hdoyYrIHCEhRTSL1WJb9wOyWHUTnp8DootWnbWrdu9qm3pvrRScu9Dq+D8gqH253yFWBEjhg/QVEJiikqb/gYlQVjTaDcqs3+eYelbs1jT9+dXVrZkeJHJy2nQkgElNtMOFMERkHmQCEJiikqF21GIe8gnDGXGKg2+3NZlj1Y+oXYpK9fdYgdI3fBixwgM6+Y0dM8RCEJiikcYycYIXOJgRdUm/1j5hVvzsNX96X0cUnTjLnEwKowguYBC8II7K81On7YUDiCYorIW2NG4ZS5xMBNzJhXPBhjJxiDB8IhVgAv6Lbrx7MsO2NFGAHZA4UjKKaIXKwZNttYgZsKuwyOW52Nfe2pg7F/RNK2EMIggJvxYpdRkD1QOIJiCsXYCUbEXGLglqrN/gmdSutb7u/JvnDl9pg/Imlb8kIXWE+3XT/vxS4jcKjW6Oy2sBSJoJii8UaPYXuw2uzbxgpsZFqn0q2dWfrVWD8axXA8zCEFuKVuu56/2D1lhRgyGQSFIiimaFykGaYLOg+AQYRdBzoab+HPrvxClJ+LQjgTwh+AQRhBwbDJICgUQTGF0WtVpoydYMiMnAAGVm3253QqvdTF5w5n88tuz4yMFzTAwLrtev7b/pgVY4iOGD9BkQiKKRJv8hgmIyeArTimU+nF/nLxzpg+DsXyQJg7CjCwbrs+62wBhmzKglIUgmKKRFDMsCwZOQFsRbXZd1jODb7y9Juj+jwUxkK3XffPGrBVRlAwTLIICkNQTCH0WpUDWZbtVU2GxMgJYMuqzf4JnUrPe+zpu7Nz13bG8FEoHlvHgS0LuxHMN2dYBMUUhqCYorDVg2E5E+aMAmyHECvLsq9ffVsEn4ICerDbrhsPBWxL2JWwYBUZgl21RueAhaQIBMUUhTd4DMOSQ3GAYag2+2fzMKvMi7nc35M9tPSWCD4JBWM8FDBMXuwyLJ4jKQRBMcnrtSr5CaOHVJIhOBHmiwIMw/Eyzz/8xtX3R/ApKKBj3XbdeChgKMLuhJNWkyGwy5lCEBRTBLqJGYYL5pQBwxRmnZe2U6mz+K4IPgUFkx9gN6uowJCV+sUuQ7O/1ujss5ykTlBMEXhzxzAcc4AdMGzVZn+2jAfbXV45mM0v74rgk1AwtogDQ+dgO4ZINkHyBMUUgYsx2+UAO2CUSjdP9fRlYycYupMOsANGJRxsd8ECs02yCZInKCZpvVYlP1l0ryqyTQ7FAUam2uyXbv7hV55+cwSfgoJxrwZGzXWG7TIWk+QJikmdN3Zs18kQ4gCMUmkePh97+u7s3LWdEXwSCuSBsDUcYGTCDPTSjYtiqHbVGp0DlpSUCYpJnaCY7dI5AIxctdnPQ64HyrDSX7/6tgg+BQWyZHYoMEaeDdguGQVJExSTuiMqyDY8GMIbgHE4UfRT1Zf7e7KHlt4SwSehQE5023WHzQJjEWah6ypmOwTFJE1QTLJ6rYoLMNuxpGMAGKdqs79Y9M7Ib1x1iB1DpZsYmATPCGyHZjaSJigmZYJituNECG0AxqnQXcVfXtofwaegQHQTA2Onq5jtqjU6sgqSJSgmZS6+bJUOJWAiitxVfHnlYHb6mdsi+CQUhHs1MEm6itkOWQXJEhSTskOqxxbpJgYmqZBdxX+1+J4IPgUFopsYmBhdxWyToJhkCYpJkvnEbIMOJWCiitpV/MUrb4vgU1AQ7tVADHQVs1Wa2kiWoJhUCYrZKt3EQAwK1VX8+LN3Zeeu7Yzgk1AQuomBidNVzHaYU0yqBMWkykWXrZq1csCkFa2r+M+X3hXBp6AgdBMDMdFVzFYdsHKkSFBMqlx02YqT1Wb/vJUDIlGIMGy5vyd7+Oq+CD4JBTGrmxiIRegqXlAQtkBzG0kSFJOcXquSh8S7VI4t0BEARCN0FZ9MvSLfuPr+7NLKjgg+CQWhmxiIjesSWyEoJkmCYlLkgstWnNJNDEQo+RdYX17aH8GnoCBOdtt192ogKt12PR9dd0FV2KRdtUbHliuSIygmRcZOsBU6AYDohBdYyR6Uc3nlYHb6mdsi+CQUhHs1ECvXJ7ZCkxvJERSTIhdbNutCtdmft2pApJLtKv7rK78YwaegIM502/WziglEajYctgmbocmN5AiKSUqvVdmdZdleVWOTzCYGohVeZCW5pbW9eDCCT0FBzCokEKtwyOacArFJgmKSIygmNS60bNaSH3VAApLb0nrxucPZuWs7I/gkFMBSmAEKEDPjJ9isQ1aM1AiKSY2xE2zWXLXZX7RqQOSSC8nmLr8ngk9BQQiJgeiF8TgLKsVm1BodGQZJERSTGh3FbJY3/0D0wgutkylV6uGrDvJmaNyrgVS4XrFZMgySIigmNS6ybMZCtdl3MA6QimS6Kh+98uHs0sqOCD4JBZAfYndeIYFEzDnUjk2SYZAUQTHJcJAdW+CNP5CMlA61e/Tqz0fwKSgIYyeAZDjUji0QFJMUQTEpcYFls/yIA1IT/QuuyysHsy9cuT2CT0IBOHAWSJEXXGzGfqtFSgTFpMQQeDbjpEPsgARFH5r99ZVfjOBTUBBzoTsPIBnddj2ZHUDEodboaHojGYJiUuLiymboUAKSU23281mtZ2L+3O3FgxF8CgrCvRpIlesXmyHLIBmCYlLieHUGtVRt9v14A1IV7ZbWi88dzs5d2xnBJ6EALnTbdfdqIFXOQmEzZBkkQ1BMSsz2YVAePIGURXsN+8vFOyP4FBSEezWQrG67nu8AWlBBBmSMJskQFJOEXqviwspmePgEkhXmq5+K8fPPPvXWCD4FBeEwKCB1rmMMyugJkiEoJhW2ajAoYyeAIojuOvbY03dnl1Z2RPBJKIB87MRZhQQS55mDQe2qNTq7rRYpEBSTCkExg/KDDSiC6K5lX3vKIXYMjXs1kDzjJ9gkXcUkQVBMKoyeYFAePoHkxTZ+Yrm/J/vCldsj+CQUxLxCAgXhesagBMUkQVBMKnQUMwhjJ4Aiiebh88zSr0bwKSiIpW677l4NFIU5xQxKpkESBMWkYq9KMQAPnkCRRHNN+7MrvxDBp6Ag3KuBwgjz1i+oKAPQUUwSBMVEr9equKAyKFu/gMKoNvtRzD68+NzhbH55V3EWlklzrwaKxnWNQegoJgmCYlLggsqgdCkBRTPxh8+/XLyzcIvKRLlXA0XjusYg7JImCYJiUqCjmEEshMOfAIpk4g+fs0+9tVALykQtdNt192qgaHQUM5Bao+OQfqInKCYFOooZhDf5QOFUm/384XNpUn+vx56+O7u0ssMXi2ERpgCFE16AnVFZBrDbIhE7QTEpEBQzCA+fQFFN7Pr2tacO+lIxTF7qAkXlWYRB2C1N9ATFpMDFlA2FrjuAIprI9W25vyf7wpXbfaEYmm677l4NFJXrG4PQUUz0BMWkwFHrbMRWL6DIJvLw+Y2r7/elYpjcq4HC8iKMAWmCI3qCYqLWa1VcSBmEH2ZAYVWb/bOTmFPcWXyXLxXD5F4NFJ0XYmzEWE2iJygmdrZmMAgPn0DRjfU6d3nlYDa/bEMPQ+VeDRSd6xwb2WuFiJ2gmNjpKGZD5hMDJTDW69zpy8ZOMFy2ZQMl4DrHhmqNjmY4oiYoJnYuomzEFi+gDM6O8+/4laff7EvFMC1YTaAExnqvJlma4YiaoJjYuYiyET/IgMIb586Jx56+Ozt3bacvFcOkyw4ovG67vujFGAPQDEfUBMXEzkWUjXj4BMpiLDsovn71bb5QDJuXukBZuN6xEc1wRE1QTOycCspG/BgDymLk17vl/p7soaW3+EIxbO7VQFm43gFJExQTO6eCsp6larN/3goBJTHyh89vXHWIHcPXbdcFJ0BZuN6xkSkrRMwExUDK/BADymTk17zO4rt8oRg2h84CpdFt143FA5ImKCZavVbFmzY24ocYUBrVZn+kQfHllYPZ/PIuXyiGzUtdoGwcaMd6jNckaoJiIGXGTgBlM7KHz79afI8vE6PgXg2Ujese6zFek6gJiomZN21sxI8woGxGdt374pW3+TIxCjqKgbJx3QOSJSgmZoJi1lVt9o2eAMpmJA+fjz97V3bu2k5fJkZBYAKUjese66o1OgesELESFAOpuqByQAmN5OHzz5ccYsdILHXb9UVLC5SMXY9sZLcVIlaCYmKmo5j1+AEGlNHQr33L/T3Zw1fdchkJXXVA6XTbddc+IFmCYmLmqZX1GDsBlE612R/6w+c3rr4/u7Syw5eJUfBSFygrux9Zj9ETREtQDKTKVlagrIb68Pnlpf2+SIyKoBgoK9c/1mP0BNESFBMzF0/WY0sXUFZDe/i8vHIwO/3Mbb5IjIp7NVBWrn9AkgTFxEyLE+vRUQyU1dAePv9q8T2+RIySezVQVq5/rEdTHNESFANJGsWcToBEDO3h84tX3qbmjJJ7NVBWrn+sx4xioiUoBlK0pGpAiQ1l9MTF5w5n567t9D1iZLrtuo46oKxc/4AkCYqJUq9VsRWD9XhDD5TZUILiucvGTjBSTvwHysxhdkCSBMXEylYMALi5oXQpPXx1n+VllIQkQGl123XXQCBJgmIgRTqKgdIaxoz2R698OLu0ssOXCABg/DTGES1BMZAiM78AtuHRqz9v+Ri1eSsMlNyZsi8At7TL0hArQTEAQHq2PP/18srB7AtXbldyAADgRQTFxMphdqxHlxJQdlueffjXV36x7GsHAADchKCYWJnZAwAj0F48aFkZBy91gbJzHQSSIygGACiJi88dzs5d26ncAADASwiKgRQ5zA4ouy11Kc1dfk/Z1w0AYOJqjY5d1ERJUAwkp9rsn1U1gM17+Oo+qwYAMHnOZSJKgmIAgBJ47Om7s0srO5SacdnygYsABaG5BUiOoBgAoAS+9pRD7BifbrsuKAbKzrg8IDmCYgCAglvu78m+cOV2ZQYAAG5JUAwAkJ5NdWueWfpVJQYAANYlKAYASM+mguI/u/ILSgwAAKxLUAwAUGAXnzuczS/vUmIAAGBdgmIgNWdUDGBwf7l4p9UCAAA2JCgGACiw2afeqrwAAMCGBMUAAAX12NN3Z5dWdigvAACwIUExkJrdKgYwmK89ddBKAQAAAxEUA6nZr2IAG1vu78m+cOV2KwUAAAxEUAwAUEBnln5VWQEAgIEJigEA0nNgo0/8Z1d+QVkBAICBCYoBANKz7rz2yysHs/nlXcoKAAAMTFAMAFAwpy+/X0mZqFqj4/BZoOxcB4HkCIoBAArmK0+/WUmZtA3HowAUnOsgkBxBMQBAgTz29N3ZuWs7lRQAIF6LakOMBMVAcnqtypSqAdzc16++zcoAAESs266fVR9iJCgGAEjPTV+YLff3ZA8tvUU5AQCATRMUAwAUxDeuOsSOaNj9A5Sd6yCQHEExsZpXGdbhBGGAm+gsvsuyAAAAWyIoBlLkBGGg7F5yHby8cjCbX95V9nUBAAC2SFAMAJCelyTCpy8bO0FUvNQFys51EEiOoBhI0T5VA3ixrzz9ZitCTIyJAsrONh9u5YyVIVaCYiBFgmKgtHqtyksOx3n82buyc9d2+lIQE0ExUFq1Rsc1EEiSoJhYnVUZABjMny85xI7o7FcSoMSMnQCSJCgmStVmf1FlWMchiwOU2It2VSz392QPX7XRAgAA2B5BMQBAWl6UCn/j6vuzSys7lJDo1Bqdl4xJASgJ1z/WYwc10RIUA0m62YxOgJJ4UVD85SU7/ImWGZ0A8FJ2UBMtQTExcxIoALzUC0Hx5ZWD2elnbrNExMqMTqCsNLUASRIUA6ny4wsoqxfCt79afI8vATHTUQyUlesf69FRTLQExUCq/PgCymrX6t/7i1fe5ktAzHQUA2VlLhTrMaOYaAmKidl51WEdHj6B0lk7n/3xZ+/Kzl3b6UtAzNyrgdKpNTr7VB1IlaCYmAmKWY+HT6CMXthN8edL7/IFIHa7VAgoIUExGzF6gmgJioFU7eq1KsZPAGXzwkuyh696DiV+tUbHmQJA2bjusa5uu270BNESFBMzF082oqsYKJvr171Hr3w4u7SyQ/FJgTcaQNm47gHJEhQTM9sx2IigGCib54Piqz+v8KTCvRooG9c91nPB6hAzQTGQMm/rgbLZe3nlYPaFK7crPKkQmABls1/FWYezmIiaoJhoVZv9edVhAx4+gdLotSrXZx7+9ZVfVHRScki1gLKoNTqeT4CkCYqBlHn4BMrk+sNne/GgopOUWqNjBxBQFoJiNqIhjqgJiondggqxnl6r4scYUBYHLj53ODt3baeCk5opFQNKwrMJkDRBMbFzoB0b8WMMKIsDc5ffo9ikyL0aKAsvxtjIWStEzATFxM6gdzbixxhQeL1WZXd+OM7DV+3gJ0mCYqAsHGTHRjTDETVBMbETFLMRD59AGRx49MqHs0srOxSbFDlTACi8WqOjgYVByDiImqCY2Hnbxkb2h047gCKbevTqzyswyRKgACXgOseGuu26oJioCYqJnfk9DMKPMqDQnu7/3Hu/cOV2RSZl7tVA0bnOsZELVojYCYqJnbdtDMKPMqDQ/q+lX7lThUmcezVQdMbssBH5BtETFBO1arPvQsogPHwChdVrVab+7MovKDCpE6AAhWW8DgOSbxA9QTEpsD2DjZhTDBTWN5/+jfr88i4FJnmCFKDAXN8YhKCY6AmKSYGLKYPw4wwopK9ffds/U1kKwr0aKCrXNwbhDCaiJygmBS6mDMKPM6Bw8t0S/+Hq3prKUhDu1UBRGa/DIBatErETFJMCF1MGMW2VgKL5t9+//19eWtmhrhTFoVqjY1QUUCi1RsdzCAPptuvzVorYCYpJgYspg9jba1X2WSmgSP7mh2/65wpKwegqBorGdY1BLFn7G9NaAAAgAElEQVQlUiAoJgU6ihmUt/lAYeSdl3+xXH2zilIw7tVA0biuMQgjNUmCoJjoVZt9F1QG5W0+UBj/7c7F/0k1KSCBClAYtUbnQL6zUUUZgFyDJAiKScWCSjGAI/nBTxYKKIJv/ejVv6GQFNCuEKwAFIFGFQZ13kqRAkExqXBRZVA6lYDk5UHahede+Y9VkoKaUVigIFzPGJSOYpIgKCYVLqoMylt9IHl7X3Htf1RFCsxLXSB5tUYnP0h7v0oyIJkGSRAUkwoXVQbl4RNI3tM/fplrGUW21/gJoADcqxnUUrddd0g/SRAUkwqjJxjUrl6r4kcbkKxaozN9aWVHVQUpONu1gdS5jjEojW8kQ1BMEqrNvgsrmyEoBpK1Z8ePflP1KAH3aiBZxk6wSfIMkiEoJiVnVIsBHe21KrstFpCaWqOz+4kf7fhVhaMEjJ8AUuZlF5shKCYZgmJSYvwEm+HHG5Ai1y7K5JhqA4ly/WIzZBkkQ1BMSryFYzOELUBy/tHLftxUNUrEvRpITtgNsVflGFS3XZ+3WKRCUExKBMVsxpFeq7LPigGpyOcdPvXjl92hYJTIrlqj4zAoIDW6idmMBatFSgTFJKPa7HsLx2Z5+ARS4sGTMtJVDKTGdYvN0PBGUgTFpOaCirEJgmIgGf/oZT/+DdWihI7k3fQKD6Qg7ILYpVhsgqCYpAiKSY2LLJuxt9eqTFkxIHa1Rmf6qR+/7DaFoqS82AVS4XrFZskwSIqgmNQYP8Fm+TEHRG/Pjh/9pipRYu7VQPTC7odDKsVmOMiO1AiKSY23cWzWUYfaATGrNTq7l1Ze9s8UiRLbm3fV+wIAkXOWAJvlIDuSIygmKQ60Y4t0KgExm36m/7KfUiFKTgADRCt/qeuZgi2QX5AcQTEp8laOzfKjDojWHa/84cdVB7JDDrUDIjbtEDu2wI5okiMoJkXeyrFZ+aF2wmIgOnkw9vi1n3qrysB1xy0DECnXJ7ZCUExyBMWkyMWWrbClFYjOe3cuevCEnzgatncDRCPMUN+rImzSUrddl12QHEExKdJRzFbs77UqU1YOiMn/+6NX/7qCwIt4sQvExnWJrZBbkCRBMcmpNvvn87dzKscW6NwDovG//l7zl97xiqVXqwi8yDFdxUAsao1O3mhySEHYAt3EJGmHspGo/O3cEcVjkw71WpV94WUDwET9xhs/9d/n//v/Osuyx5+9K/vOs/8k+9YP35T97bXbsvll5+VQWrvCoVGzvgJABJxzwlbpKCZJgmJSJShmq477wQdMWv7SKp/Huvox7njV6eyOV734QwmPKbHjgmJg0vIDZ9feq2Ezuu26oJgkCYpJlYsuW3W016oc11UMTNiGo3BuFR7/l6fvyL517U3ZYz98Q3bu2k51pIj21hqdmW67LiwGJsnYOrbqjJUjVYJiklRt9s/2WpWlsD0RNktXMTAxN3YTb8aN4fFyf0/29z98l/CYItJVDEyMbmK2SWMbyRIUkzLjJ9gqXcXAJA2tQ2ln5Ymbhsd/+8xU9u1na9k3l/9J9p9+WM0urfjJR3J0FQOTpJuY7RAUk6xKv99XPZLUa1WOZVn2GdVji05Wm31dxcBYhW7ivxv3/+7llYPZhWffKjwmNRe67fo+VQPGKXQTj/1eTXF02/WKcpIqTwikzFs6tkNXMTAJE+lQev3Lv5m9/jXfzN7xmiz7tfDfrYbHC8/8V9njP/zp7PQzt/lCEJu8q/hYt10/oTLAGLnmsB3mE5M0HcUkrdeqLJpTzDacqjb70xYQGIdJdRNvxsXnDmfnn31z9q1n9wiPiUV+JsW+bru+qCLAqNUanaksyx6x0GzDA9123egSkqWjmNSZU8x2HOm1KlPVZl93OjAO0T803P6KR67/+aXXPf+f//UN4fH/8+zt2fyy97OMVf6FO2ZeKDAmrjVs15wVJGU6iklar1XJZ8y2VZFtOFNt9qcsIDBK+UupInUoPf7sXdl3nv0n2bd++Kbsb6/dJjxm1HQVAyOnm5ghWOq267stJCnTUUzqdIKyXYd6rcp0tdn35hcYpUJ1KN3xqtPZHa968X+3Xnj89lcuZ+eu7Rz/B6UodoWZoQ6hBUZp1uqyTfIJkqejmOT1WpX8MLK9Ksk2XKg2+05VB0YifxmVZdmXyra6y/092d//8F3Z95+7LTv7zL7soaW3RPCpSNw7uu36WUUEhi0/ODPLss9YWLap0W3XvXAgaS9TPgpAJyjbtbfXqphHBoxKKU9P31l54nrn8S+97vPZna/9mwg+EQVQyn+WgNGqNTq7zSZmSHQUkzxBMUXgYswwHOu1KuZJAUMVXkKVftfLz7/arZqhOFRrdKYtJTBkx8OIG9iOhW67ft4KkjpBMckzW5Yh2aVTCRimXquSj7Q5ZlGf7y6+69U/iOCTUAAnQvcfwLbVGp0DWZbdYyUZAm/FKQRBMUVxSiUZgqO9VmXKQgJDckKH0k+8+7WPx/JRSNteL2CAIdIowrBoYKMQBMUUhbd3DIsfi8C2hZdOR6zkT/zXr/tPsXwU0nd/6AIE2LJwgN0hK8gQLHXbdZkEhSAopii8vWNY9jvYDtiOMO/cidc3eP3Lv5m9/ZXLUX0mkubFLrBlDrBjyOQRFIagmEKoNvv50PgF1WRIjoXZogBbccwBdjf3vtd8J8aPRZoOhW5AgK2YNR6KIdJNTGEIiikSb/EYll26AYGt6LUq+Xb4+y3ezf3i6/5LjB+LdB2vNTpe7AKbUmt0po2HYshkERSGoJgicXFmmA71WhWdSsBmecm0jjtedTp748t/FO3nIzle7AKbEkZOuG4wTKe67fqiFaUoBMUURrXZP5tl2QUVZYiOG0EBDCrMN99vwdb3a689H/PHIz1GUACbYeQEw2bsBIUiKKZodBUzTDqVgIEYOTG4O1/7N6l8VNJhBAWwISMnGBEZBIUiKKZohHoMmxEUwCDcfwb0jtf8qfETDJsXu8C6jJxgRBa67bqtUhSKoJhCCeMnllSVITOCArilXqtywsiJzTF+ghEwggJYj5ETjIKXDxSOoJgisvWDYdvlewXcTK9Vmcqy7B6LsznGTzAin6k1OgcsLrBWeIlk5ASj4BmRwhEUU0Qu1ozC/tA1CHBdr1XZ7Z6zNcZPMEKzYYs5QBZeHh23EoyAsRMUkqCYwqk2+3PGTzAi94TuQYDMNtbtMX6CEcnHwHixC6ydS+xezSgYO0EhCYopKhdtRmUudBECJRYOubSNdRuMn2CEjtYanRkLDKXnDAFGya4yCklQTFEJihkV84qh5HqtSr6N9TNlX4ftMn6CETthXjGUV3hZdNRXgBExdoLCEhRTSNVm/2yWZRdUlxE5ZF4xlFPYUTCv/MNh/AQjtMu8Yiin8JLIb3VGyfeLwhIUU2S6PhmlfF7xtBWG0pkz63B4/umu/7sofxXitN8uMyiX8HLIvZpRkzVQWIJiisyDAaM2G7agAyUQdhIcUuvhueNVp7O3v3K5KH8d4nSk1ugcVxsojTzA26vcjNCpbru+aIEpKkExhRXGTyyoMCO0K4TFtrVCwfValXzW4T3qPHzve813ivZXIj731xodu4Cg4GqNjhe6jINuYgpNUEzR6Spm1GxrhYILOwfMohuRu17/5UL+vYjOrMPtoLjC4XVe6DJqS9123bMfhSYopuhcxBmHIw63g2Jac3idWYcj8vqXfzOb2rlUyL8bUcn/GZ5zuB0UT3gJ1FZaxkA3MYUnKKbQqs1+PjvolCozBveErelAQQiJx6e+26F2jMXe8M80UBAhJPbPNeOiOYjCExRTBrqKGZd2r1WZstpQGLNhvAwj9s7XGj/B2OyvNTp+G0IBhB0Cs17oMiYXuu36WYtN0QmKKbxqs59vD7GnlXGZC/NMgYT1WpX8wfOIGo7HzsoT2Ud2fasMf1XicFRYDGkLIfG8F7qMkW5iSkFQTFl4GGBc8o6G+V6rss+KQ5p6rcqxPEhSvvH6p7uMn2CsjobDr4A0nRASM2YyBUpBUExZePvHOO0KncUOzIHEhFnjn1G38bvjVaezt79yuWx/bSarLSyG9IQdAV7oMk4nu+36ohWnDATFlEK12T+fZdkZ1WaM9ofOYmExJCKExE5Nn6DG7m+W9u/OxORh8bTlhzQIiZkQ3cSUhqCYMnFxZ9yExZCIMFvc7pMJO7TrP5T678/EzNYaHecLQOTCDgAhMeOWH2I3b9UpC0ExpVFt9mcdascE7Bc+QdxCSDzv1PTJc6gdE3L9fAFhMcQrhMR2/TAJnuUoFUExZaOrmEk42mtVfPcgQkLi+DjUjgkRFkOkhMRMmOc4SkVQTNl4G8ikCIshMkLiODnUjgkSFkNkhMRMmEPsKB1BMaXiUDsmTFgMkRASx+1fvOHrZV8CJkdYDJEQEhMBz26UjqCYMtJVzCQJi2HChMTxe+drv5y98eU/KvsyMDnCYpgwITERWHCIHWUkKKZ0qs3+XH5yqcozQcJimBAhcRryQ+1+7bXny74MTJawGCZESEwkNJhRSoJiyspFn0nLw+KzvVZlt0rAePRalSkhcTp+441fKvsSMHmrYfGMWsB41BqdE0JiIrDUbdc19lBKgmLKKr/oL6k+E7Y/fwAVFsPo9VqVPOh5REicjte//JvZXa/+QdmXgcnLrxltYTGMXq3RyZ/R7rHUREBjGaUlKKaUqs1+fnLpnOoTAWExjFgIiXUnJWjmjX9Z9iUgHsJiGKEQEh+1xkRCNzGlJSimzI6rPpHIw+LzYXYqMES9VuW4kDhdd7zqdPb2Vy6XfRmIRzuEWcCQ1Bqd3bVG56yQmIic7LbrDkqgtATFlFa12c8v/qd8A4jErtBZPKUgMBzh0Mj7LWfa/sUbvl72JSAuR/OwOA+31AW2p9bo7AtnB+y3lETE2AlKTVBM2bkJEJM8LH4kbJMHtigf5dJrVeZ1JxXDL73u87qKic3RcMidsBi2qNbo5DvpzgqJicyZbrt+VlEoM0ExpVZt9vMg4UzZ14HotHutipcYsAVhhEt+bT9k/Yrj11/3N2VfAuKTh1tnQ9gFbEKY9z3vgFkiZDwlpScoBoPqidM9vVZlziF3MLgwusUW1gL6ldf/SfbGl/+o7MtAfPaGzuJptYHB1Bqd1bMDhMTEZqHbrs+rCmUnKKb0qs1+HhRfKPs6EKUjYW7xPuWB9YWRLY948CymnZUnso/uXij7MhCn/JrzpRB+AbcQDq2bc3YAEbOjk9LLVfr9voWg9ELA4FR8YrWUZdl0GJUCrBG67k+YR1x8l1cOZu/+9sfKvgzELT8keabbri+qE/xEGNEya8cPEbvQbdc151B6mY5ieJ6uYiK3esidbiVYI3TbO7SuJF7/8m9mH9n1rbIvA3E7Ym4xvNiaecRCYmLmOQsCQTH8hK0mxO5+c4vheb1WZdpp6eXzG2/8UtmXgPitzi2eUSvKrtbozJpHTALybmLnFkEgKIafmA1b/CFm17uVeq2KbiVKq9eq5C/2vuTBs3x0FZOI/NrUzkOyfC6rolE2eVd9rdE5a8cPidBNDGsIiiGoNvuLuopJRN6t9JhRFJRNPmqi16rkD573KH556SomIUeNoqBsjJogMUu6ieHFBMXwYid0FZOQfBTFfJjTCoUWDh01agJdxaTm+svdWqPj5S6FlnfP1xqdOaMmSIxGMbhBpd/vWxNYI3Rp3m9NSEj+cmOm2uzPKRpFE2Zyz4axK3Dd5ZWD2bu//TGLQWrO5Pfrbrt+XuUoklqjM5Vl2ZyAmMTkz1D7uu36osLBT+gohpfSVUxq8h/lX3LQHUXTa1XyB8/zQmJupKuYRB0KoyiOKSBFELqI82enR4TEJOiEkBheSlAMNzCrmITlYdr5XqsyrYikLH/hEQ6s8+DJLZlVTKLya9pnao3OfK3RMTqKZIUuYucGkKoLnvnh5oyegJsIXZnnBRQk7FQYR+EtOUkJLzpmXX8ZxOf+4ZPZQ0tvsVakKt/BdrzbrgsrSEbeRRwCtqOqRsIaDrGDmxMUwy30WpV8W+BnrA8Jyx9Aj1WbfT+CiJ5ZxGyFWcUUxEKYXXxWQYlZrdHxMpciuNBt1+3ogFsQFMM6eq3K+XBaNaTsTAiMPYASpfBi7rgHT7ZCVzEF8mDoMLYbiKiEMSmzYc42pE43MaxDUAzr6LUqM1mWta0RBfFAvlXQOApiEQ6ry7ev7lcUtmq5vyd733f+MLu0ssMaUgTXdwMJMYhBGDORv8y9X0EoCN3EsAGH2cE6wpb9C9aIgrg/HHY3o6BMUjisbjYcVickZlt2Vp7IPrp7wSJSFPnOinY47G5KVZmUWqMzEw6rExJTJMdUE9anoxg2EA5WcrQ6RZOPozhebfbnVZZxCXOIj4U/xkwwNLqKKbCTYRzFeUVmHMILiuPGTFBAZ7rtuhdwsAFBMQyg16rM+7FEQZ0K84s9gDJSoZP9uLnvjMpXFz+a3ff9O60vRXV9fJT5xYxKmEN8wqGyFNjhbruuSQY2ICiGAYQ5mo9YKwrsZAiMPYAyVOYQM04fOv/H2blrO605RbUUrqcCY4YmBMT5i9yjVpUCO9Vt16cVGDYmKIYB9VqVOW/YKbgXHkAFxmxXCIhtXWWsHr3y4ewjT7zXolN0AmO2TUBMyfycET4wGEExDKjXquQ/pv7OelECAmO2TEDMpH3i4mez08/cpg6UgcCYTRMQU0IPdtt1h9jBgATFsAm9ViX/MX6PNaMkVh9AZ80wZiMCYmLx+LN3ZR/87t3qQZkIjNmQgJiSyq+P+1wbYXCCYtiEcGL/eaf1U0LXT10XGHOjcEjdMTOIicnn/uGT2UNLb1ETyiYPRGZDYOx+zXW1Rid/kTsjIKakHui268cVHwYnKIZN6rUqeSDyGetGSZ0KIymcGFxi4aXZakC8t+zrQXwurxzMPnj+3uzSyg7VoazyF7yzTvgvr1qjMxPu1Xb6UFYXuu36PtWHzREUwxb0WpXzwhFKbiEExrNlX4gyCbPaj4UHTzsriNrDT96XHX/ynYpE2S2EDmP36xKoNTq719ynPatQdoe9LIPNExTDFoRZnI9YO/jJNldjKYorjJfQlURSlvt7spkL/yo7d22nwoGxFIVmvAS8xJluuz5lWWDzBMWwRb1WZS7LsiPWD15wJhx8p2upAHQPUwSPPX139lvdu9QSXmwhHH4354CndIXD6WZ0D8NN/ZyXYrA1gmLYohCinBWgwEvkXUtzITS23SshYfbwtMPpKJJPXPxsdvqZ29QUbu5kCIznrE/8wmiJabt8YF0OsINtEBTDNvRalfwGdL81hFu6sCY0PmuZ4rMmHJ62S4Iiyg+2e/e3P6a2sL7Vl7xC48isCYfdp2Fj+bPHAbslYOsExbBNDraDgQmNIyEcpmwcbAebIjSeMOEwbNkHXLdgewTFsE0OtoMtyUPjfCzFXLXZ92NuDMK4nPyBc8pDJ2XjYDvYllMhOJ4383N0ao3OgXCPnjH+CbbEAXYwBIJiGAIH28G2nQrB8bxu4+HptSqrwfC0nQ+UnYPtYChWdwfNh+DY9u4tCofRTa25Tzv3BLZuKYyc8DILtklQDEPgYDsYqtVu49Xg2A++AYUdDqt/HHIDN/jUE3+UfeHK7ZYFhmdh7T1bcHxrNwTDU17gwlA5wA6GRFAMQ9JrVY5lWfYZ6wlDt7TmIfRstdmft8QvvKBa3aZ6QDAMG8sPtvvg+XuzSys7rBaMxurL3ryB4my3XS/lPTvMGF57j57SUAIjs9Bt1w9YXhgOQTEMUa9VOWumGIzFwupD6OqfarNf2C6mXquS//i9MRj2wAlb8NXFj2b3ff9OSwfjk9+zz4f7dR4cny/S9vAwW3jtPXqfbmEYq8NlfSkFoyAohiEKYc5j1hQmYmlNcLwYHkYXU5p5HEZHrHYhHQj/XqcwDNknLn42O/3MbZYVJmth7f169f7dbdeju2/XGp3VA7LW3qcFwjB5D3bb9WPqAMMjKIYh67Uq+Wyk+60rROVC6GZafRDN1gTK2ag7ksNLpN3hP67++9UHzUwYDON18bnD2S//3e9YdYjbwpr79NpuwbX37xds1FG4ZhzEjfaFP9kN92ZBMMTtQjjAzmx0GCJBMYxAr1U574clJG3hZg+hm2A0BETu4Sfvy44/+U5lAoA0faDbrs+pHQyXoBhGIGwff8TaAkC8Pvr3D2Xzy97pAEBiTnXb9WlFg+F7mTWF4as2+/nWtwctLQDE6+M/8+9VBwDSkp9LMqNmMBqCYhid42FuEgAQodtf8Uh2/A3fUBoASMeMucQwOoJiGJFwMJY3nQAQsV97w6ezqZ1LSgQA8TtlLjGMlqAYRsgICgCI37980xevKhMARO2CRiwYPUExjF4+gmLBOgNAnH72lf/xD7Ise0B5ACBaRk7AGFT6/b51hhHrtSoHsix7zDoDQHTOVJv9qfxD1Rqds1mW7VciAIjKg912/ZiSwOjpKIYxqDb7Z3UqAUB0bjw5fTr8dwBAHC6EXbrAGAiKYUyqzb4RFAAQl5lqs39+9RN12/XzHkYBICrTRk7A+AiKYbx0KgFAHE5Vm/2XnJzebddP5P83NQKAiXug266fVQYYH0ExjFHoWjJbCQAma6OT02e82AWAiTrTbdft8oExExTDmFWb/VmdSgAwUdPVZv+W21jDFtdpJQKAibjxDAFgTATFMBkzoZsJABivB8Ihs+vqtuvzDqIFgImYCecGAGNW6ff71hwmoNeqHMiy7DFrDwBjc6ba7E9t5n+s1ujkofJ+JQKAsXiw264b1wgToqMYJiR0M91r/QFgLJa2OE7CQbQAMB4LWZaZSwwTJCiGCao2+05WB4DxWHcu8a2Era/mJALAaC2FkRObvlcDwyMohskzrxgARiufSzy/1f+Fbrs+l2+FVSMAGJlj3XZ9wzMEgNEyoxgiYF4xAIzMpucS34p5xQAwEuYSQyR0FEMEzCsGgJHY6lziWzGvGACGa0FIDPEQFEMkzCsGgKHb0lziWwnziocZPANAmQ37hS6wTYJiiMtMOOkVANiee7czl/hWuu16/v/zAbUBgG2bDi9hgUgIiiEioetpxrZWANiWk2Gnzkh02/XjdgEBwLY8EF6+AhERFENkwrziGXUBgC3Jd+aMY9ahXUAAsDWnwktXIDKCYohQtdmfy09+VRsA2JR8R87MMOcS30q3XbcLCAA2b0FjFMRLUAyRqjb7x2xrBYBNmQk7c8ai267bBQQAg7v+Qje8bAUiJCiGuNnWCgCDuTfsyBmrbrs+53A7ABjIdHjJCkRKUAwRc7gdAAxkpIfXbSTMWTypVABwS/c6vA7iJyiGyIUttNPqBAA3Na7D6zZyzC4gALipk912fWIvdIHBVfr9vuWCBPRalbyzuK1WAPCCfMfNvnEcXjeIWqOzO8uy81mW7VIiALhuoduuH7AUkAYdxZCIarM/a1srALwgD4mnYgmJs+dHUOSfZcrIKAC4biHcF4FECIohIdVmP+8qPqNmAJDNhPFMUQmH9MwoDwAll780nQkvUYFECIohPdNmIAJQco1qsz8X6xJ02/X8szUi+CgAMClT4eUpkBBBMSQmbLG1rRWAsjoZxjFFrduuGxkFQFk1hMSQJkExJEhYDEBJnQxjmJLQbddnhMUAlMy94WUpkCBBMSQqzGWcVj8ASiIfu3Qswb/qMSOjACiJk912/YRiQ7oExZCwarM/bwYiACVw/dT0sKMmKeEQnylhMQAFdzLspAESJiiGxIU5jfeqIwAFdf3U9BRD4lUhLJ42MgqAgkp11w9wA0ExFEC12T9hBiIABZQHq/8/e3cfXGlW3wf+HGr+MWB3t7PGhq6lBeMBjLe2NcausNimNVuLg2fYtEglpoFKWgqvhq0dTSXGNAZaHeKImCSjycZeXtPqbGyEd72onQyhnKxHCpvNugxG2hcvZoCR7DRvflGrDPjPs/U05w631Xq5L8+993n5fKpuNajV0r3n3Hnu83yf3/mdmdxuqdZuXL2wbX8BABro1qqffFMUqLmYUjKH0BC7S7GoLr5oPgFoiHubEBJ3Oz2/Oh1CKFpHnajOswKAgeyEEKaFxNAcKoqhQfJO8BvmFIAGmG9aSBy+XVm8aXkuAA1QrJCZFRJDswiKoXlmbZgDQM3N5x78jXTj6oUVm9ECUGN7ud1E427oQtsJiqFh8mY/dlcHoK4aHRJ3CIsBqCkhMTSYoBgaSFgMQE091IaQuENYDEANCYmhwQTF0FDCYgBq5tqpS2m5bZOWw+IrFXgqAHCceSExNFtMKZliaLDdpTgVQti0uzoAFXYtb8jaWqfnV4vA+KI3KQAVNZ9vbgINpqIYGu7UpbSdK4v3zDUAFdT6kDh8u7K4GINrFXgqALCfkBhaQlAMLXDqUtoUFgNQQULiLsJiACpISAwtIiiGlhAWA1AxQuIDCIsBqBAhMbSMoBhaRFgMQEUIiY8gLAagAoTE0EKCYmgZYTEAEyYk7oGwGIAJEhJDSwmKoYWExQBMiJC4D8JiACZASAwtJiiGluoKi7e8BwAYAyHxAHJYfKV2TxyAOhISQ8vFlFLbxwBabXcpngwhrIcQzrZ9LAAYmUdOXUoLhndwp+dXi8D4al2fPwCVVqw0nb1x9cK6aYJ2ExQDwmIARmn+1KWkOqkEwmIARqAIiWduXL2waXABrSeAog3FTW0oABgBIXGJ8nLg+ca8IAAmTUgM3EZQDNzSFRZvGBEASiAkHoGusNiGtAAMQ0gM3EHrCeAOu0uxuAi9aGQAGEBx4Tl36lJaM3ijc3p+dTq3jTrR1NcIwMhs5ZD4piEGugmKgQMJiwEYwK3qpFOXkuqkMRAWAzAAITFwKK0ngAOdupSKDXOuGB0AeiQkHrO8XHjaHgMA9Oi6kBg4iopi4Ei7S9EO6wAcZyuHxC48J+D0/OrJXFl8tnUvHoBeXbtx9cKc0QKOoqIYOFLeiOiVNs0B4BBC4h+TszQAACAASURBVAnLlWHFhrTXWj0QABzmipAY6IWKYqAnu0tRH0QA9ruWWxVREafnV+0xAEC3+RtXL6wYEaAXKoqBnuSek/ogAtDxiJC4enLF2HzbxwGAWytC7xMSA/1QUQz0ZXcpFn0Q10II54wcQGvN59ZEVNTp+dXZEMKKlUAArbQTQpjNm54C9ExQDAxkdyla2grQPkV10uypS2nd3Fff6flVbaMA2ufW3gG5fz1AX7SeAAaSlxs/ZPQAWqOzaZ2QuCZyJdmUtlEArXFNSAwMQ0UxMJTdpWhpK0DzbeRKYheeNXR6frVoG7VsJRBAo125cfXCoikGhiEoBoa2uxSnc9/iM0YToHGu2bSuGU7PrxYBwuW2jwNAwxRtoeZuXL2wZmKBYQmKgVLY5A6gkWxa1zA2uQNoFJvWAaUSFAOl2l2KxdLWB40qQK3t5X7ELjwbKG9yV4TFZ9s+FgA1tpFDYm2hgNIIioHS7S7FudwLUbUSQP10Nq1z4dlguW9xERafb/tYANSQfsTASAiKgZHQtxiglvQjbhl9iwFqRT9iYKQExcDI5L7FqpUAqq+48FzQj7idTs+vzuSbu1YCAVTXVg6JtYUCRkZQDIzc7lJUrQRQXbc2wtGPuN1Oz69O5bBY32KA6rlW3NDVjxgYNUExMBa7S1G1EkD1XC+qk/QjpuP0/KpNaQGqYy8HxFb8AGMhKAbGJreiKMLic0YdYOIeOnUpLZsG9js9vzqbW0e5uQswOVpNAGMnKAbGTisKgInSaoJjaUUBMFFaTQATISgGJkIrCoCJ0GqCvmhFATBWWk0AEyUoBiYmt6IoToLOmwWAkbp14XnqUnLhSd9Oz6+6uQswekWridkbVy9sG2tgUgTFwMTtLsWFEMKiC1CAkdjKVcRaTTCw0/Orbu4CjM4jN65eWDC+wKQJioFK2F2K0/kCVC9EgPJcOXUpLRpPynJ6ftXNXYDy7OQN69aNKVAFgmKgUnaXol6IAMPbyVXELjwpnY3uAEpxPYfE9g0AKkNQDFRO3uiuqC4+Y3YA+nYt9yN24clInZ5fLSqLLxtlgL7s5YB4zbABVSMoBiopb3S3qLoYoGd7uYrYhSdjc3p+VesogN6pIm6gGGOx0qZ4FJ+JJ494hcW8F3tGbKeUbFpIJQmKgUrbXYqz+QJUL0SAw13PIbELTyZCdTHAkYqbuYs3rl5YNkz1F+OtFbCdx7kBX1DxnljvPFKy6TDVICgGKi9XF9tpHeBOqoipDNXFAAcqbuYu3Lh6QQVpjeVweC6EMDuiIqad3P9/WbUxkyQoBmpD72KA26gippJUFwPcohdxA8QY53JLxHFeg24UvzMlmxIzfoJioFb0Lga4VXGyoIqYKlNdDLScXsQ1N6GAeL+t4pxPYMw4CYqBWlJdDLTUI8VFiypi6uL0/OpCvtC21wDQBjs5IBbs1VRuMbFcsRudRYXxnJYUjIOgGKi13aVoeSvQBlu5itiFJ7Vzen51Kl9022sAaLJH8oZ1bubWUIyVX7m6l9tR2BCRkRIUA7W3uxSncnXxoDvOAlRVcVGwfOpSWjRD1N3p+dXZHBhbDQQ0yUberG7TrNZTjHHodkn3v/z+8J+feU74oRf8UHj6059+x99/9StfCX904z+F3/7ffis8/oXHhxmn4v02m5LVZYyGoBhojN2lW32kli1vBRrieq4itsyQxjg9v1pUbC1YDQQ0wF6uIFbhWWO5F3Hf15BFMPxTf+X+8CMv+tHwIy/6L8PTnvpdPf/br//xn4U/+Nzj4d+vPxau/Yt/PkhwXLz3ZlJKbk5QOkEx0Cg2uwMawGZ1NF5uR2E1EFBX13IVsarOGssh8dVeX8E9P3hPuPi3/na48NrXhLuf++zSXvinPvU7t0Ljd777Uj//bC/3LXa+SKkExUAj7S7dWj607AIUqJG9fNxatlkdbaEdBVAzG7mK2J4BNRdjLG5WXuzlVRQB8c///C+EC6/5mb4qh/tVVBp/6P0f7Dcwnk8prTRlXpg8QTHQaLkdxaILUKDitJmgtbSjAGpgL1cQC+QaIMbeN0T/+39vKSz8nQdHGhDvVwTG737Xu8MHPvDLvf4TYTGlERQDjZfbUSzkh/7FQJVs5YBYZRKtl9tRFNXF59s+FkClXCmOTdpMNEOv7SaKHsS/+N73hemzL5zY6/71j/2v4Z3vfHsvPYz1LKY0gmKgNXaX4lSuLu5piRHACO3lgFj1B+xzen51Jn9eax8FTNL1XEVstU9DxBiLz5fHjns1b3rTW8M//ifvG2sV8WG++KU/DO/6hXeEj67+6nHfWpxbTqdkdRrDERQDrbO7FF2AApOiDzH06PT8qvZRwCToQ9xAMd5aZbp93ArTotXEL7zr7ZUagG9+6y/CG173hl7C4q2U0vR4nhVNJSgGWmt3KdpABxinYof0RX2IoT+n51cXtY8CxmAnVxCvGezmiTGuH1coVMWQuNsvvue9vWx090hKaWGsT4xGERQDrZc3vFt2AQqMSFGZNCcghsF1bXgnMAbKZqO6hosxFp8dDx/1KqseEnf8/NveEX7pfUvHfdt9Kdn/gsEIigFseAeMxkauIHaiDiXJG97ZbwAow5PtoGxU11wx3tqnZvOoa7y6hMSh9zYUOymlqfE9K5pEUAzQRWAMlGArb1QnIIYRERgDQxAQt0iMceWoz4pXX3ht+NBHPtTzxnXf+Oa3wuOPPxG+cuPL4Stf+fKtr33ly18Of3TjP93xvS98wQ+Fp3/3d4d7nvf88PwX3BO+/xl/qZSB//of/1n4iZe8ODz+hceP+raHUkrLpfxCWkVQDHCArsD4svEBerSTK4gtXYUxERgDfRAQt0yMsdjY7bOHvep7fvCe8L//H/9neMb3fW/PAxNjHHgQL7zqNeFv/s25cP8DLxt6Ij71qd8JL33pi4/6luL9PpWSzZPpj6AY4Ai7S9EFKHAcATFMmMAYOIKAuKWOqyb+2OpvhJ951V/ra3CGCYo7Xv5TLw//w6+8P/zg3cPtqd7D5nZXUkqLQ/0SWkdQDNCDHBgXFcZzWlIAmYAYKkZgDHQRELdY7k38xGEjULSc+LWP/su+B6iMoLhjY+M/HlcVfKSiX/G9Z88e1YJiL6V0srQnTCsIigH6oIcxkDepWxEQQ3UJjKHVBMQUgW7xHnjwsJH47Ob/G6bPvrDvgdofFBftJN729neEZz3rB27rQdzpZfzvH3ssfPKTj4ZP/tYn7/hZdz/37vAf/uPvDNW7+CMfvhZe/4a5o75lPiXnrPROUAwwAIExtNJGriC2SR3URA6M53xeQyvs5IB4RUBMjPHmYcf9N73preH97/9nA43R/qD4jW98S/jAB3752H93WKD7niv/4Lj2EUfqoap4I6U0M/AvoHUExQBDyIHxbK5aGq7JFFBV13IFsYAYaur0/KobvNBct1pB3bh6QdUkt8QYi+uzjx82GoNWE4chguLCJx79t+GBV/zUHV//6tf+ZNRVxc9JKW0P/AtoFUExQEl2l2KnYumsMYXaK5atruUKYifW0CCn51fn3OCFRtjIAbEbudzmqE3s7n/5/eHRf/PowAM2TFAccjXzBz/4K7d97dF//Vvh/gdeNvBzKqqKn/60px71LQ+llJYH/gW0ylNMN0A5in6lpy6l6RDCfSGE64YVaqkIiK+EEKZOXUpzQmJonqLq8MbVC1P583rDFEPtFCt97r1x9cKMkJhDzB72FxfnXjfRMTv/V+98al/5ypeH+plPe+p3hbf93JHtK7SeoGd3GSqAcuXl6eu7S7d22l3IvREtc4Vq2yr6GtqgDtojB0wzXRvfzfq8hsoq2kus2KCO48QYp486lr/ox350omP4zNPPGsnPPTfzX4dfet/SYX99fiS/lEYSFAOMSK5EXNhdiov6GENl6T8MLXfj6oXi83ou9zHutJHyeQ3VsJE3p3Mjl14dWj1btJ24+7nPbuRAnpv58SP/vgjQU0qbY3tC1JagGGDETl1KN3MFxMruUpzJF6EH9swCxuLJqqT83ydAyFWKRQ/H5dPzqzM5MFaFBeP35D4B+UYO9GPqsO99yUt+srEDWbSfePWF14aPrv7qYd9SVFoLijmWoBhgjLraUizmwHhO1RKMzfVcPbxmyIGj5LYU67kthc9rGI+tfLNmTXsJhjB92D+953nPm/i4/t6nP33H1+553vNL+dk//ML/4qi/PjRAh26CYoAJyG0pirB4cXcpzubWFKqMoXyd6uEVG9MB/crVjLc+r0/Pr/q8hvLtdT6nb1y9oNqRMhwaFD/vBS+Y6AB/45vfCktL77nta3c/9+7w0pe+uJSf/wPPfOZRf21DO3oiKAaYsFzduLa7FBe6qpbOmhcYit7DQKluXL1w6/P69PzqQg6MF3xew8Cu58phvYcp26Eb2T3rWT8w0cFe/sePhC9+6Yu3fe3SpXeV9vNf9GM/VtrPor0ExQAVkXul3uqNuLt0a7feTmhsB3bozZNLVvUeBkYlL4m/VQGZW1N0gmOtKeBoW/m/nTW9h5mEZ3zf907k937t638a3v2ud4cPfvBXbvv6hVe9Jrzu9WNbpKL1BD2JKSUjBVBhXa0pZoXGcIedrnDYRScwMXkDvDmf13CbnbwxndYSjFyMt4ptPnvY7ykj/4ox3vb/i7D3bW9/x4Hf+5UbXw7r678d3veP3nvH3xX/7kMf+VB4+tOeWtqwbG79frh3+ocP/fuUUjz0LyETFAPUxO5SPNkVGNuFnTZ78qLz1KXkohOonK5+xkJj2kg4zETEGIsbdo8d9rtHERQP4uf+7tvDuxffVWpIHATFlERQDFBDQmNaSDgM1JLQmJYQDjNxVQ+K3/jGt4Q3/+xbjgxzhyEopgyCYoCaExrTYMJhoFGExjSMcJhKmUTriX59+EMrI+tLLCimDIJigAbJofGMi1BqbCtfdK4Jh4Emyz2NZ22ER810NqRbFw5TRTHGQ0OuUQTFL/+pl4e//jcu3Pa1b/z5n4ff/9z/d8fmdR3vufIPwjvffan00TsmKN5JKdnQjmMJigEabHcpugilDq4XF5w2pAPa6vT86nTXjd5z3ghUyF7nMzqHwz6nqbSjguKvff1PwzO+73uHevr7g+KincQHPvDLB37vN775rfCxj/7P4fVvmLvj70ZRWfypT/1OeOlLX3zYX2+klGZK/YU00l2mFaC5Tl1K6/nkfmF3KU7lC9AZLSqYsM5S1fVTl9KayQDaLldmFo/l0/Or3auDZtzoZQK2OuHwjasX1k0ANbNz2HHzy1/+6tBBcT+KzeqKMPiZz3xWeOAVP3Xbv1xaek941av/Rqkb2n3+Dz43uhdDawiKAVoiV2ou50d3tXHx51nvA0aoU42kahjgGDeuXrjZacETvl1t3H2jd0ZbKUZgp/tzOr8Hoa62DwuKP/+5z4Xpsy8c+8u6/4GXhZ/7u28P7/tH733ya1/80hfDo//qk+FVF/5aab/n85//g6P+2k0feiIoBmiprmrj7t7GM4JjSrLRVTWshyHAgPJS/ydv9Ha1qRAcM6juYFg7CZpm87AWPp/5zKfDz7yqvGC2H29885tvC4oLa2u/UWpQ/P/831tH/bX/zumJHsUA3EFwTJ86FcObORhWsQAwJoJjeiAYpjVijEVD4KsHvd77X35/ePTfPDrUUPTTo3i/V194bVj92K/d9tWvfu1Pwvc/4y8NPT1f/+M/O+7n3JuS4g2Op6IYgDucupRuW/aag+PuC9FpF6KttrMvGHbSCTAh3f2Nw3daVcx0fW672ds+G92f01pJ0DKHFix84pOfCF/80h+Gu5/77ImMyIv/8n91R1D8B597vJSg+NO/+3tH/fWekJheCYoBOFYOjte7T7x2l+J0vgh1Idpse50Lzc5FZ34/AFBBuVp0pfuZnZ5fnen6zJ72md0oG/lz+tYj3ziA1kopbccYD93Q7l//5r8KDy68dSLDc++LfvSOr332M58OL33pi4f+2Rvrv33UX1vtR8+0ngCgNHmDvKmuC9ED+4NRWTvdF5s5FLY8FaCBusLjKZ/ZtdB943ZbKAyHizEWN8suHvQNw7afGKb1xDe++a3w3U9/2m1fu/Cq14SPrv7qwM8n9NZ2Yj6ltHLUN0CHoBiAkdpdilP7qpimVDJN3F5XGLzdFQqrFAZosdy2otO6ovO/BcjjdeBntPYR0LsY42wI4eOH/YNHH/234f77/5uBRnSYoLjw03/lp8Mnf+uTt33tz7/xzfD0pz11oOdT+MiHr4XXv2HuqG85lZLzfHqj9QQAI5UrUrc7/Y47cuuKk/suRvU+Llex9fHNruqjbYEwAIfJbSu29y9TPj2/erLrZm/n8/qkEHlge11BcCcMvnnj6gXLw6EEKaW1o9pP/OZvrg0cFA/rx3/8pXcExb/3mf9r4PYT3/zWX4R/+A9/8ahvuS4kph+CYgAmomsDtDsuivaFyKHrT0Hy7TpB8Pb+h5YRAJQlV7MeGmLmNhZh3+f1yRwqHxjUNNz+z+ebXWGwdhEwHkWrhcsH/aaiAvjNP/uWMH32hWOfih8puU/x6q/9enj8C48f9S1aTtAXrScAqJ3czmIqP+/ORWn31+p+YbrR9b87F+adi8wiZFdxBECtdIXJnerkjpmu/32you2puj+Xn/w8zp78nBYCQ3XEeOt64YnDntCgvYqHbT3xta//afiB7//PbvvaoH2Ki97EP/GSFx8VFO+klKYO+0s4iKAYgMbLm+x161Q67bf/+4bVqSTabzNfaHaoAAaAA5yeXz3sMzscEDr36qgbrtu5BQdQc0dtalf48IdWwutef+hfH2jYoLjw6guvDasf+7XbvvbVr/3JcRvS3eHn3/aO8EvvWzrqW2xiR98ExQAAAAA0ynFVxYUvfHEn3P3cZ/f8sssIig/afK7f0PoTn/h34YEHXnbUt6gmZiB6FAMAAADQKCml7RjjIyGEBw97Xf/9W382/Ppv/C/haU/9rp5eehHodnvmM5/V95C94q++Inw4DP5zvvilPwwLD77luG9b7PuJ0XpBRTEAAAAATRRjPJlbwR26Ifab3vTW8P73/7NavPpvfusvwhte94bjehpvpJTKbqlHSzzFRAMAAADQNCmlYl+QuaNeVtE64hff897Kv/IeQ+LCwnieEU0kKAYAAACgkVJKayGE60e9tne++1Klw+I+QuIrKaXN8TwrmkjrCQAAAAAaK7egKALUM0e9xr//95bCwt95sOeexePQR0is5QRDExQDAAAA0GgxxukQwvpR/YoLr77w2rD8T/9peMb3fe/Eh2Nz6/fDz/z12fD4Fx4/7lt3QgjTudUGDEzrCQAAAAAaLbdkOLZ/b1G5+xMveXH4xCf+3USH4yMfvhbunf7hXkLivRDCrJCYMgiKAQAAAGi8lNJKCGH+uNdZhLMPPPCy8OY3/3fh63/8Z2MdlqKK+IGffiC8/g1H7sHXUYTEM/oSUxatJwAAAABojRhjkcJe7fX1Fr2L3/DmN460HUUREL//f/yV8IEP/HKv/0RITOkExQAAAAC0Sr9hceFtP3cpvOK/PR9+8if/cilDVWxUt7H+H8K//J9WetmsrpuQmJEQFAMAAADQOr1ucLffPT94T7j4t/52uPdFPxqe/4Lnhbuf++ye/21ROfz5z30ufOYznw6/9L6lQYZ8K/ck3vaOpWyCYgAAAABaKcY4FUIoehefG+b1v/rCa8P3nDgZTnzP94TnPe/5T379dz/9u7f+/KOdJ8InPvmJYYf4WrEhn43rGBVBMQAAAACtFmNcDCFcrugYFK0m5lJKaxV4LjSYoBgAAACA1iururhkqogZm6cYagAAAADaruj7m1KaCSHcF0LYmPBwFL//3pTSnJCYcVFRDAAAAAD7xBiL0HhxzBXGRQXxckpp03wwboJiAAAAADhEbkkxlx9nRjBOW7nlxYrqYSZJUAwAAAAAPcih8WwIYTqEMDNgcFwEw0XF8HoIYU04TFUIigEAAABgQLlFRcjh8ckDfsp2ftzUUoIqExQDAAAAALTcU9o+AAAAAAAAbScoBgAAAABoOUExAAAAAEDLCYoBAAAAAFpOUAwAAAAA0HKCYgAAAACAlhMUAwAAAAC0nKAYAAAAAKDlBMUAAAAAAC0nKAYAAAAAaDlBMQAAAABAywmKAQAAAABaTlAMAAAAANBygmIAAAAAgJYTFAMAAAAAtJygGAAAAACg5QTFAAAAAAAtJygGAAAAAGg5QTEAAAAAQMsJigEAAAAAWk5QDAAAAADQcoJiAAAAAICWExQDAAAAALScoBgAAAAAoOUExQAAAAAALScoBgAAAABoOUExAAAAAEDLCYoBAAAAAFpOUAwAAAAA0HKCYgAAAACAlhMUAwAAAAC0nKAYAAAAAKDlBMUAAAAAAC0nKAYAAAAAaDlBMQAAAABAy93V9gEA2ifGmIZ50Sml6G0DAAAANImgGACAgcQYZwb8pzdTSptGHQAAqiOmNFRhHUDtqCgGKMcQx9ONlNKgITMAADACehQDAAAAALScoBgAAAAAoOUExQAAAAAALScoBgAAAABoOUExAAAAAEDLCYoBAAAAAFpOUAwAAAAA0HKCYgAAAACAlhMUAwAAAAC0nKAYAAAAAKDlBMUAAAAAAC0nKAYAAAAAaDlBMQAAAABAywmKAQAAAABa7q62DwDQSldMOwAAAMB3CIqB1kkpLZp1AAAAgO/QegIAAAAAoOUExQAAAAAALScoBgAAAABoOT2KGUiM8WQIYSaEMF2TEVxPKa1X4HkALRZjnM7Hzak6jIJ+3gAAAO0hKKZnORyey4+zNRw5QTEwdjkcLo6bsyGEMzWbAUExAABASwiKOVYOiBfy44QRo+5ijGmYl5BSit4EHCfGOJOD1nMGizqIMRbv18tjeqrnhj0WdzgmM4x8M2+ma7XH2I/Z3sMAQFUIijlSjLGogFsREAP0Jt9cKwK3Bw0ZQPXk89vOwzkuExFjnKtLK6oJ2gwhbKeUNls7ApQu3xivOu99JkZQzKFijEVAfNEIAfQmV6at1LQ9D0BjxRin8uq4OeEwFTFn1VFvYox7IYS14pFSWqvDc6bSxrV6amj5vb/e9f6/6a3FqD3FCHMQITFAf3JIvC4kBqiOIiDO57VP5JUeQmKonxP52vTjMcbtoiI0r+CCvuSbhnVSvPfPhxCuFhXG3vuMg6CYOwiJAfrTFRILIAAqoLiQzsuLn3BeC41yJleEbuY2MtCPOrd7OZHf+9s1aZ9BTQmKuU2MccHJNEDv8l19vdwBKiJvJrpZp+XFQN/O5ArjFRWWtMytwDjGuOm9zygIinlSXobxsBEB6MuCdhMA1ZCLHh7LIRLQfEWR07rAjBY6m6uLp00+ZRIU023FaAD0Lt9gU7EGUAG5fZqiB2ifs8JiWupEfu8LiymNoJhb8oHFrrsA/dEfDKAC7LEBrVeExWttHwRa6YQbJZRJUEzHgpEA6F0+GbOJCsCECYmB7JxNvjhGnTezO8oJN0ooi6CYDmEHQH9mbWAHMFlCYmCfy7k1GBykye+Nc7lPPwxFUExnZ2hhB0B/ZowXwOTEGOeExMABVBXTVotaUDAsQTFB2AEwEMdOgAnJFYPLxh84wEVVxbTUCW1FGdZdRpAQgh0yAfqQ79SfMWY0TLGEf73Pl/TYEEPwUAhh05uIAa2McEXcnvcm1N6CwIyWWlBVzzAExRTKXppwPV9oVukEe7sCzwFojrJvsO3l0GPT8YpJSSlt9/v+izEO82w3U0r9BtPQaZt2ruSR2MsVymspJSEx1N+coJgDDHJTvEzTOX8ZxedYx4kY42xKyeZ2DERQTCjxAFWcYM+66APoy1ZxsphSumnYAHqyUvIwXSlCYsdhauq+Ep/2MKtEOvpZLTLTFZqdLeF3dyvCsmk3fug2yE3xkj2ZleQVirP5pkbZoXHxcwXFDERQTJkWhMRAS5TV925PSAzQu6JKqsTWP4ocqL0y379DrhLp6Ge1SHdoNtVVBVxWW5lZbWSoqnz+X9z4XMmfbWW2VJo18QzKZnaUyR0roC3KCorXhMQAfSlzKbmQGCqiqPRMKS3mc6zrJT0re/FQC7lNxFReaViGWxX1Zp9BCIopjbADoG/6EQP0KFcclrU894qQGKqnuKZMKRXVkNdKeHKCMmoj5ykzJYbF3v8MRFAMAP0r68ZY2ZuJAjRZWUtpd3LlIlBRKaW5EsListrUwFjksHiupN9V1gpIWkZQTGlyXx2ANiir353jJkDvyrp4FhJDPSzkXuIDyxuGQW3kDRivlPB8Z8w6gxAUE0pc2rCclwQC0JszMcayd+8HaJwc9pwt4XXtpZQcd6EGcnXl8pDP1PJ76sjnFBMjKCaUuIS6WNqzGWNcdOcWaLgyewtfjDGuxxjd9Qc4XFnHSJsvQ70MGxRD7RSbO5ZQ0CeTYSB3GTbyEuqyNgY5EUK4XDxijFslhtAhP8/Ozys2H9nOB1CAsSqOPTHGMn9lcQx+LMa4V2Jbi47OZk0388/etPkoUENlVQXawA5qpDhnydeVZawogDpZG/J9778ZBiIoJowglOgo+8DUHWYXYXSxDHEnn/CvpZRUiADjtFHiTbaOEyP4mXf8vHzBtZKPnW64AXVQVkXxTMVapa2nlITXcLRtoReTFGOczhW6U2PcJM5qQyZCUEyoeWVF0e7iYl66XYTGi/rOAWOyPoJQd1yKi62Hi0eM8Vo+dgqMgSorawntxQq+RkExHK0obDpvjBiHfDNxJj+m3aSgbfQopqz+N1VQhMZXc69Pm+oBo9aUVQxFaPJE0V++As8F4DAu1AEYiWKPpRjjQoyxuCnxRJEr5HNknz20jqCYjiZV4Z7Lm+rZ4RYYmZRScSK506ARvpxvtNn4AgCAxssB8WJub/KwYBgExXxHERTvNWg8ij6f68JiYMSathP3OUuggaqJMerTCECpYoyzOSC+olE3cwAAIABJREFUnPMDaL0gKKYj74DftN6+nbBYdRwwKk27yVY4G2PU6x0AgEbK57ofFxDDnQTFdFtsYOBxooEBOFAR+SbbQgPn42KusgAAgMbIIXEVNzaFShAU86QceMw1cETOW7IIjEpKqTjZ3GjgADetrQYAAC0mJIbjCYq5TUqp2MX/kQaOit38gVEqqm+3GjbCZ2KMTbx5CABAy8QYF4TEcDxBMXdIKRUH0GsNG5lzMcapCjwPoIHyioyZBobFgmIAAGot71ukeAx6ICjmQCmlIhx4qGGjo98mMDJdYXGT2lCcsyEoAAA1t2zjOuiNoJhDpZSKg+m9DaqQExQDI1WExSmlIiy+0qDNQR07gUm7aQYAGEQuenA+Cz0SFHOklNJmSmk6hDDfgMD4XAWeA9ACKaViadtUQwLj6Qo8B6DFivNR8w/AgGZVE0PvBMX0pNjVPwfGz8ktKa6HEHbqNnr6FAPjkquLF1NKRRXDK/NGoXVsSyEoBgCgrlQTQx/uMlj0I6W0nfv7LI9i4HKQO5X7fBYH9LMl/4riZ2+X/DMBjpRSWgshrI1qlGKMM/uOnWVWTbjBBlTBVonnhfellNbNKkArnC/xRe7lc/rN/Bilx7w9mQRBMZWSg+jiUZy8L+bwY7HEthE2ZQIapyvwWAnfDo7nSty044x3DFAB2yUGxc4HAVogxljmyrhrIYSFvIH1yMUYvUWZCK0nqLQi/MgbQ10r6XlaQg00XtEuKFcXN2VDPYAyK7ecDwK0Q1nH++sppblxhcQwSYJiaqE4KNexJzLApOTNn/Rko8pmzA59KDModmwEaIeyWqgter/QFoJi6mTFbAH0LrekUFVMVanqpB9l9hQ+a4NjAHq0kwswoBUExQDQbE5sqaqZGKNesfQkL/fdKnG0RrIxMwCVUsbqJZvh0yqCYgBoNlWbjEQJIW+x2eKC2aEPZVYVn88bfwIAkAmKqZMy+smVeYEBUGl5p+cTZokRKeMmxIIWAPSh7DZkV4XFABzDeQqtIiimFmKMxZKRs2YLoC9lbLxhI1EOU8bO38WNjDUtKOhF7hFZZvuJkMNile0AHOZMziOgFQTFVF4+KK+V9DzLuKgFqLwYY1F5d76E56kvGwcqcWOX4kbwurCYHo2it/DDMcZ11e0AjVPWucqK8xTaQlBMZcUYZ3PQ8VhZS6ftVgo0WRFyFMuoY4xFuHuxpJcqKGYcirB4WxsAelAUD+yNYKDOhRCeiDEWFe5ltDsDYPLKKhQ74zyFtrjLTNNRVFJUZDCm8oG4bJZPA6XKPYCrsnP+qPoRC4o5yk6Jn9knchuAxRwG9rSaKKVk/4EWSSndjDEWx93LI3rV5/NGd3t5b4v1EivSDuQ9DDAyZR6/u89TioK2dcdvmkhQTLdzDR8N1cRA2U624NjpBJijbI/g5m7x8x7Mj15EM9QuKaXFXNU1isKCjhOd0HgMg+s9DDAao8gAzuSblZdjdPimebSeoE2EHQD9c5ONo/hsZVIs/wXgSCml7RFsggqNJiimTcraEA+gLTaKZd5mmyO4kcBE5OW+jxh9AI6xYoCgd4Ji2mIn300EoHdusHEcFcVMTEppQaUYAMcQFEMfBMW0RVU2mwKoEyfWHClXnF83SkzQjA2LAThMPle5YoCgN4Ji2mBP2AHQt2vaTtAjn7FMTD5OzebzPQA4yLKbitAbQTFtsCzsAOjboiGjFymlNRdfTFJKqeiVPa0NBQAHyXmATVChB4Jimm5H2wmAvl3R150+LRgwJikfs2a0QgHgIHkT1HmDA0cTFNN0c6qJAfqy5QYb/cpVxQI6Jqo450spFW0oHtKKAoD9UkorwmI4mqCYJpvPdw0B6E0RrMy6wcaA5iz9pwpSSsu5FYWbFwDcJofFr3RDEQ4mKKap5vMHAAC9KU6WZ7ScYFD5BsOMsJgqKI5lubr4PoExAN3ySqgpnw9wJ0ExTVMEHa8UEgP0ZaM4Wc4bQsHAusJiF15UQrG6LAfGzwkhPGLjRQDC7e2K7svnwtB6QVBMw1zLQceaiQXoyU5egTGj3QRl6brweqVQjqrIFcYLKaWiguze3Md4w9JjgHbLNxRn3FCEb7vLOFBjxYn9en6sCDnoVUopGixabCcfN9fcWGOU8vtrLcY4nfsXF3+eM+hMWl49sdnZuDPGOJWXIBfv0ZMmiDGp4iqeMqoqR3FNtj3Ec3ONSE9y+7WF4pE/F2byZwO0SkwpmXFqIcZ4Mp/AB5vUAfSmKwDZ1n8YAACAwwiKAQAAAABaTo9iAAAAAICWExQDAAAAALScoBgAAAAAoOUExQAAAAAALScoBgAAAABoOUExAAAAAEDLCYoBAAAAAFpOUAwAAAAA0HKCYgAAAACAlhMUAwAAAAC0nKAYAAAAAKDlBMUAAAAAAC0nKAYAAAAAaDlBMQAAAABAywmKAQAAAABaTlAMAAAAANBygmIAAAAAgJYTFAMAAAAAtJygGAAAAACg5QTFAAAAAAAtJygGAAAAAGg5QTEAAAAAQMsJigEAAAAAWk5QDAAAAADQcoJiAAAAAICWExQDAAAAALScoBgAAAAAoOUExQAAAAAALXdX2wegqWKMMyGEmbaPA1BL611PejultG0a4U4xxukQwsn8mDZE0E4ppUVT3wxdx/WOqfwAqJoV12nNFFNKbR+DRooxFieMl9s+DkBj7IUQNkMIN/Of2zlEXjfFNFmMsRMSzHQFBkWQcMLEA+HbQXE0ENXXFQJ3ink6fzqmA3V0n2uxZlJRDEAdFBdQ5/LzPN95vjHeujbeyeFxcaKy6YSFusqrgabzY6rrPQ9ATeQbfJ1jeecm3xnzB0AdCIoBqLsz+XErQM7h8UYOjtdSSptmmKqJMXaqyjrhsFAYoIa6Wv7NqA4GoO4ExQA00bn8uBxjLNpWrHUFxzfNOOO2LxguHmdNAkD95BYSs/lY7iYfAI0iKAag6YrKnov5cTXGeD0Hx0JjRiqHCTM5UBAmANRQ142+2fxQMQxAYwmKAWib8/mxHGNcyzv26mtMKXI4PJfDBD0pAWoqxtg5lp83hwC0haAYgLZ6stI4xlhsiLeoyphBCIcBmiEfzxdUDgPQVk8x8wBwK9y7GkLYjjEu5x3L4VDFeyTGuBBj3A4hfDaE8KCQGKB+itYSRfVw1/H8opAYgLYSFAPAd5zIgd8TMcYVgTH7xRhnc8uSJ0IIDwuHAeop3/BbLm4S55vFjucAtJ6gGAAOdlFgTPhOtdlirjb7uH6VAPWVA+KVfMPvQdXDAPAdgmIAOFp3YHzSWLVHV5iwG0K4rNoMoL72BcQXTSUA3ElQDAC9uZh7GC8KjJstxjgTY1wXJgDUn4AYAHonKAaA3p3IlaWbRa9a49YsXQHxYyGEc20fD4A667QNKj6zBcQA0BtBMQD0r2hB8PFiUzP9i+svxjgtIAZojnwzdzPf3NWDGAB6JCgGgMGdz9XFC8awfrqWI39WQAxQf/m4vp43HtVXHgD6JCgGgOEUlUoPFxemqovrwXJkgObJN2033fgDgMEJigGgHOf0Lq4+y5EBmiXf/CuqiB92XAeA4QiKAaA8J3Lv4pXiwtW4VkdejrxmOTJAc+Sbf9uqiAGgHIJiAChf0c6gaEUxbWwnr2s58vm2jwVAU8QYl/PNP1XEAFASQTEAjMbZHBbPGd/JyMuR1yxHBmiOfGwvbv49aFoBoFyCYgAYnSKcvJo3TmOMupYjqyIGaIi8Umc734wFAEomKAaA0busb/H4WI4M0Dx5hc5nHdsBYHQExQAwHp2+xcLiEbEcGaCZcq/5q6YXAEZLUAwA43PWJnejYTkyQDMVK3Jyr3kAYMQExQAwXsLiklmODNBMOSS+aHoBYDwExQAwfieExeWwHBmgmYTEADB+gmIAmAxh8ZAsRwZoJiExAEyGoBgAJkdYPCAhAkAzOb4DwOQIigFgsoTFfRIiADST4zsATJagGAAmT1jcIyECQDM5vgPA5AmKAaAairB4LcZ40nwcTIgA0EwxxjnHdwCYPEExAFTHmVxZLCzeR0gM0EwxxtkQwlXTCwCTJygGgGo5W1QWm5PviDEuCIkBmie3XFoxtQBQDYJiAKiec7mCtvXycuSH2z4OAE2TV8+s5dZLAEAFCIoBoJou5pC0tXKl2bL3J0AjreWWSwBARQiKAaC6ruawtHVUmgE0V4xxsVg9Y4oBoFoExQBQbW3d3E6lGUADxRhnQgiXzS0AVI+gGACq7UTbNrdTaQbQTF2rRQCAChIUA0D1ncvhaePlVhsqzQCaaUVLIQCoLkExANTD5ab3K1ZpBtBcMcbZEMJ5UwwA1SUoBoD6WGt4v+JFfYkBmid/dq2YWgCoNkExANTHmRymNk7e3OhB70WARtJyAgBqQFAMAPXyYA5Vm2bZ+xCgebScAID6EBQDQP2sNKkFRYxxIYRwtgJPBYAS5c8qNwIBoCYExQBQP41pQZFDhEa20wAgLOg9DwD1ISgGgHoqWlBMN2DuFvStBGieGONUCOGyqQWA+hAUA0B91Xo5rxABoNG0nACAmhEUA0B9nYsxztX4+Ws5AdBAedNVG9gBQM0IigGg3pbruLFdria+WIGnAkD53AgEgBoSFANAvZ3IfX7rpo7PGYBj5Gric8YJAOpHUAwA9bdQp6ri/Fzr3DIDgMOpJgaAmhIUA0D9najZpkFz+TkD0CCqiQGg3gTFANAMF3Pf3zrQdgKgmVQTA0CNCYoBoDkqf4Geq83OVOCpAFAi1cQAUH+CYgBojjpUFetNDNBMqokBoOYExQDQLJW9UM+b2M1W4KkAUKJ8k1I1MQDUnKAYAJplNgeyVTRrEzuARlJNDAANcJdJBPbZCyFsGpRbpvRSpYZO5M3iqnjRrpqYJvF5CVaLUE8b5u0O027mA0FQDBxgM6U0Y2DuFGMsTqBO5hOpqfynkyqqaK6iQfH5CjwHOEwn+N3Oj+J/3yy+N6W0btTgUHPOhaioznF9PT+2U0rbJutOMcZ17WOAICgG6F1KqVM5dltgkAPk4jFjaT0VcSbGOJdSWqnKE4oxqjajara6woNN4QEMbMHQUSHFsX2teHSduwPQI0ExwJDySWjxuBXK5eB4LofGWlcwKXOd92RFCIqZtL0cHqznAOGmGYHh5HMe5zpM2lY+51lz0w9gOIJigJLl4LiorlnIF1ALKo2ZgHPFLvQVumDS0oZJKXpRrlSpwh4aRDUxk7KTw+EV4TBAeZ5iLAFGpwiNU0pzuafxlXxSC+NSiQv4IrBWccYEXAshPKfouy8khpGxWoRxK6qH51NKxc3wRSExQLkExQBjUCxxziezRWA2n5dAw6jNVWSEVRMzTp2AeE6AAKNT9MK3WooxKlaH3JdSmnbzD2B0BMUAY5ZPbjsVxjBKJyqyiZygmHHYEBDDWKkmZhyK1XivzKtD1o04wGgJigEmoFNhXIQaOdyAUanChfx0BZ4DzbXXFSIIiGEMYownQwjnjTUjVBzbr+QWE2sGGmA8BMUAE1SEGkW4obqYEapCUHy2As+BZiputAkRYPxUEzNKxbF9OhdVADBGgmKACsgnwvfqXcwITLT9RIxR2wlG5ZFcRXzTCMPYCYoZlYesEAGYHEExQEWklDZz7+Itc0LJJnlBr+0Eo1DseL9gZGFi3ASkbEWxxL0ppWUjCzA5gmKACsmVcTPCYko2yaB4ymRSsnk73sPk5FUqJ0wBJdrKbYQ2DSrAZAmKASpGWMwInJhgCwgVxZRJSAyTp5qYMhXnu9oIAVSEoBiggoTFjMCkqopVFFMWITFUg/7ElEVIDFAxgmKAiuoKi3fMESWYVAXYGZNHCa4JiWHyYoxTjuuUREgMUEGCYoAKyyfPKncow9kY48lxjmQOFGBYWymlOaMIlaDtBGUQEgNUlKAYoOLyxh4PmSdKMO4LfEExw9pzswwqRVDMsIrj+pyQGKCaBMUANZBSWg4hbJgrhuQCn7pZTCltmzWoDJ8jDGshF0EAUEGCYoD6sPSaYU2PeQQFCgxjK98kAypAf2JKcF2/eYBqExQD1ESuqrtivhjCOYNHjSyYLKgUN/8Yxp6iB4DqExQD1MtyPtGGgcQYXehTBxsppXUzBZUy7lUpNMuivsQA1ScoBqiRfIJtKTbDcKFPHSyaJagcnx8MakcrIYB6EBQD1I8TbYYxzgt91csMYkc1MVSS9kUMys0/gJoQFAPUTK4qvmbeGNCUgaPi3AyDiokxqiZmUHs2sAOoD0ExQD0JUhiUijCqbs0MQeUIihmUkBigRgTFADWUUtoslmebOwYRYzxp4KiorZTStsmByrEahUEJigFqRFAMUF+q7hiUyjCqynENqknPeQaxk4sbAKgJQTFAfQlUGJTKMKrKJnZQTVaiMAjnqgA1IygGqKmUkkCFQQmKqSTHNaiss6aGATimA9SMoBig3jbMHwMQFFNFW2YFqifG6DODQQmKAWpGUAxQb/q+MQgX/VTRTbMCleQzg0EU/Ykd1wFqRlAMUG+CYgBglPQnZhDbRg2gfgTFAPXmJJxBnDNqAPRo2kAxAMUMADUkKAaoMRs/AQBQQdpOANSQoBgAAAAAoOUExQD1t2UOAQCoEKveAGpIUAxQf5b20bcYo56TAAAAPElQDADtZBd7AAAAniQoBgAAAABoOUExAAAAAEDLCYoBAAAAAFpOUAwAAAAA0HKCYgAAAACAlhMUAwAAAAC0nKAYANpp07wDAADQISgGqL9pc0i/Uko3DRoAAAAdgmKA+jthDgEAAIBhCIoBaizGeNL8AQAAAMMSFAPUm7YTAAAAwNAExQD1NmX+GMCWQQMAAKCboBig3gTFDMJGdgAAANxGUAxQbzPmDwAAABiWoBig3vQoZhCbRg0AAIBugmKAmooxFiHxCfPHALSeAAAA4DaCYoD60naCQW0bOQAAALoJigHqS1DMoATFAAAA3EZQDFBf580dAxIUAwAAcBtBMUANxRhnzRuDSikJigEAALiNoBignubMGwPaMnAAAADsJygGqJkY45S2EwzhpsEDAABgP0ExQP2oJmYY60YPAACA/QTFADUSYzwZQlgwZwxBf2IAAADuICgGqJciJD5hzhjCpsEDAABgP0ExQE2oJqYMKSVBMQAAAHcQFAPUx6JqYoa0YQABAAA4iKAYoAZijDMhhAfNFUNSTQwAAMCBBMUAFZdbTqyYJ0ogKAYAAOBAgmKA6lsOIZwxT5Rg3SACAABwEEExQIXFGIvN6y6aI0qwk1LaNpAAAAAcRFAMUFExxrkQwsPmh5KoJgYAAOBQgmKACsoh8VVzQ4kExQAAABxKUAxQMUJiRmTNwAIAAHAYQTFAheSexEJiyraVUrppVAEAADjMXUYGYPJijCdDCCshhPOmgxFQTQwAAMCRVBQDTFiMcSaEsCkkZoQExQAAABxJUAwwITHGqRhjEeA9FkI4Yx4YkZ2U0qbBBQAA4CiCYoAxywFx0WbiCVXEjIFqYgAAAI6lRzHAmOQWE3MhhIvGnDFaMdgAAAAcR1AMMEIxxukcDs9qL8EEaDsBAABATwTFACUpWkqEEIpHUTk8nf88YXyZoGWDDwAAQC8ExcB+52KMyahAI+hPTJ34/KFKrqSUFs0IDOyxGKPRA6gZm9kBQDNdTyltm1sAAAB6ISgGgGayiR0AAAA9ExQDQPMUm9hpOwEAAEDPBMUA0Dw2sQMAAKAvgmIAaJY9bScAAADol6AYAJplOaV005wCAADQD0ExADTHnrYTAAAADEJQDADNoZoYAACAgQiKAaAZVBMDAAAwMEExADSDamIAAAAGJigGgPpTTQwAAMBQBMUAUH8LqokBAAAYhqAYAOptK6W0Yg4BAAAYhqAYAOptwfwBAAAwLEExANTXtZTSuvkDAABgWIJiAKinPdXEAAAAlEVQDAD1NGcDOwAAAMoiKAaA+rmeUlozbwAAAJRFUAwA9bJTVBObMwAAAMokKAaAepnVcgIAAICyCYoBoD4eSiltmi8AAADKJigGgHq4llJaNlcAAACMgqAYAKpvK4SwYJ4AAAAYFUExAFTbnr7EAAAAjJqgGACqqwiJZ1JK2+YIAACAURIUA0A1dUJim9cBAAAwcoJiAKimBSExAAAA43KXkQaASikqiedSSmumBQAAgHERFANAdWg3AQAAwERoPQEA1TIXYzxpTgAAABgnQTEAVMeJEMKDIYTtGOOseQEAAGBcBMUAUD1FYPzxGOOKuQEAAGAcBMUAUF0XY4ybWlEAAAAwaoJiAKi2syGEdWExAAAAoyQoBoDqExYDAAAwUoJiAKiHIizWsxgAAICREBQDQH2cjzEumi8AAADKJigGgHq5HGOcMWcAAACUSVAMAPWzpl8xAAAAZRIUA0D9nNCvGAAAgDIJigGgns5rQQEAAEBZBMUAUF+qigEAACiFoBgA6utMjHHR/AEAADAsQTEA1NuCje0AAAAYlqAYAOqt2NhuwRwCAAAwDEExANSfqmIAAACGIigGgPpTVQwAAMBQBMUA0Axz5hEAAIBBCYoBoBnOxBiFxQAAAAxEUAwAzSEoBgAAYCCCYgBojnMxxinzCQAAQL8ExQDQLKqKAQAA6JugGACaRVAMAABA3wTFANAsxaZ20+YUAACAftxltIB9dkIIKwblNlP5UThXkecERymqiheMEAAwQa4r6qM4dzzT9kEABMXAnbZTSovG5XAxxpMhhOl9j7NVfb600oxpBwAmzHVFTcQYZwTFQBAUA/QvpXQzhLCeH7fk8HgmP2adaDFhZ2OMUymlbRNBTdyXUlo3WQAAMDl6FAOUoAiPU0prKaWFlFLRpuLeEMIjeckdTMKsUQcAAKBXgmKAEUgpbXaFxveFEK4bZ8ZM+wkAAAB6JigGGLFiOXVKqajufE4I4ZrxZkwExQAAAPRMUAwwJkW/2JTSnMCYMTkRY5w22AAAAPRCUAwwZl2BcdHHeMP4M0KqioH/v707PqrruAI4vDfj/6VUIFyBSAXCFQhVYKkCSxUEVWBcgVEFQRUEVRCoIFBBoIKTWXuVYFkg3uO9d3fv+b6ZN/L4D/uyK2vGPw7nAgDAgwjFADNpe4xryHtXSrlxD2yBUAwAAMCDCMUAM4uI4xb0LtwFGyYUAwAA8CBCMUAH6nRxi3p2F7NJdU/xnhMFAADgW4RigE5ExHXbXfyLO2GDvNAOAACAbxKKAToTEW9LKW/cCxsiFAMAAPBNQjFAhyLiRCxmQ+wpBgAA4JuEYoBOtVhsZzGPZUcxAAAA3yQUA3Ss7Sz+6I54hGcODwAAgG8RigH6V2PxlXtiXdM0WT8BAADAvYRigM5FxHUp5dA98QjWTwAAAHAvoRhgABFxXkp5765Yk1AMAADAvYRigHEcW0HBmvYdHAAAAPcRigEG0VZQHLkv1vDUoQEAAHAfoRhgIBFxYqqYNZgoBgAA4F5CMcB4TBWzqidODAAAgPsIxQCDMVXMOqZp8kI7AAAA7iQUA4zpxL2xIqEYAACAOwnFAGMSigEAAICNEYoBBhQRl6WUC3fHCg4cFgAAAHcRigHGZaoYAAAA2AihGGBcZ+6OFTx1WAAAANxFKAYYVEScl1Ju3B8PtO+gAAAAuItQDDA2U8UAAADAownFAGM7d38AAADAYwnFAGMTinkoO4oBAAC4k1AMMLZL98cDPXdQAAAA3EUoBhhYe6EdAAAAwKMIxQAAAAAAyQnFAOP75A4BAACAxxCKAQAAAACSE4oBIIlpmp66awAAAL5GKAaAPPbdNQAAAF8jFAMAAAAAJCcUAwAAAAAkJxQDAAAAACQnFAMAAAAAJCcUAwAAAAAkJxQDADC3fTcAAADzEooBxvfCHQKDe+oCAQBgXkIxAABz23MDAAAwL6EYYGDTNPlxbWAJhGIAAJiZUAwwNj+uzSounRadskIHAABmJhQDjM1EMQ8WEUIx3fITEgAAMC+hGGBsflwbWAqhGAAAZiQUA4xNWAGW4sBNAgDAfIRigLHZ6wksxaGbBACA+QjFAIOapsn0Hav45LTo3BN7igEAYD5CMcC4hGJgaV67UQAAmIdQDDAuP6bNKi6dFgMQigEAYCZCMcCApmnaK6U8d3esQChmBHX9hFgMAAAzEIoBxmSamFVdOzEGceSiAABg94RigDGZuGNV506MQTzzsk4AANg9oRhgMC2gWDvBqqyeYCQnbgsAAHZLKAYYj2liVhYRQjEjqVPFb90YAADsjlAMMJD2Ersf3RkrunBgDOhomqanLg4AAHZDKAYYi5c8sQ77iRnREysoAABgd4RigEG03cSmiVmHtROM6qUVFAAAsBtCMcA4TBOzrrOZTs4kM5vw8zRN+04SAAC2SygGGECbqHvhrljTXMF2rkDN8pyJxQAAsF1CMUDnWhwxTcy6LiLieqbTM1HMpjxpsXjPiQIAwHYIxQAda2/8P2mRBNYxW6yNiLob+cqtsSFPTBYDAMD2CMUAfauR+Lk74hHmXv9g/QSb9EwsBgCA7RCKATo1TVONxC/dD480d6g9nfnfz/J8nix+7W4BAGBzhGKADrVI/KO74ZEu2vqHOZkoZhtqLP51mqZjpwsAAJshFAN0pO4kFonZoNkjbXuR3qe5n4PF+mmapnOrKAAA4PGEYoBOtBfXnYnEbFAvax+sn2Cb6h73f03TdNT+HAUAANYgFAN0YJqmw1LKpRfXsUE3EdHL2gehmF34e/1z1O5iAABYj1AMMKNbqyb+0XZuwqZ0E2fbnuSLDh6F5fu8u1gwBgCAFQnFADOpPybdpoitmmAbepviPengGcjjWQvG120lxZ67BwCA+wnFADvUJojf1mm39mPSpojZhrp2ordQbP0Ec3jS/qz99zRNp3XK2B5jAAD4OqEYYAfqG/nbiokaiH9u026wLd1N77b1E586eBTyelmnjEsp/2nR+K1JYwAA+L/vnAXA5rWJtYP2ORSG2bFe1zzU53rRwXPAy/aY59ElAAAIQUlEQVT5eZqmq1LKeSmlvvzxvKOXQAIAwE4JxcCX6mqEA6eysr322W+/Ph/s+VmOi4g47/GriYiTaZqOrVyhM8/ap4bj+o2++stV+wmQ+t/Sdft0+d8V+OYGALApQjHwpRo4/+lUYFjHnT94nSr+qYPngPt8jscm4BnB5JYAgE2woxgAlqO+xK7XtROf9R6yAQAAUhKKAWA5uo+wXmoHAADQJ6EYAJZjlGndow6eAQAAgFuEYgBYhg8RcT3CV9JevHTVwaMAAADQCMUAsAyjTemaKgYAAOiIUAwA4/ul7f4dRnvpnqliAACATgjFADC2m4Gnc00VAwAAdEIoBoCxHY+ym/hLpooBAAD6IRQDwLhqZD0e/P5MFQMAAHRAKAaAcb0ddZr4M1PFAAAAfRCKAWBMnyLidCF397qDZwAAAEhNKAaA8dwsKa5GxFkN3x08CgAAQFpCMQCM5ygiLhd2b6aKAQAAZiQUA8BY6sqJ0V9g9yctfP/S2WMBAACkIRQDwDgWtXLiK4682A4AAGAeQjEAjOPtAldO/E9EXNevsZPHAQAASEUoBoAxfIiIk6XfVUScllI+dvAoAAAAqQjFANC/i2STtq/bmg0AAAB2RCgGgL79tpe4rWVIoX2tS97FDAAA0B2hGAD6dhgR59nuqK2g+NDBowAAAKQgFANAv95ExFni+6nrNq46eA4AAIDFE4oBoE8pXl53n7aC4rDfJwQAAFgOoRgA+lMjsR29v8fiunbjTQePAgAAsGhCMQD0RST+Qpustq8YAABgi4RiAOjHhUj8de1cLnp8NgAAgCUQigGgDzWCHriLex14uR0AAMB2CMUAML+6bmK/vbyNO9x6ud2NMwIAANgsoRgA5mUn8Qray+1MXgMAAGyYUAwA8xGJ19Bi8ZvhHhwAAKBjQjEAzOONSLy+iDgRiwEAADZHKAaA3ar7dV+10MkjiMUAAACb852zBICduaovY2urE9iAGounaar/oF+dJwAAwPpMFAPAbnwspeyLxJtnshgAAODxhGIA2L53EVEnia+d9Xa0WPyqrfYAAABgRUIxAGxPXTXxt4g4dsbbFxGnpZQDsRgAAGB1QjEAbMcHqyZ2r533finlItvXDgAA8BhCMQBsVp1mfRURr62amEdEXLbJ4o8Zv34AAIB1CMUAsDl1inivrUBgRjXS173QpZT37gEAAODbhGIAeLy6i/gHU8T9iYijejf2FgMAANxPKAaA9dX4+D4i6hTxmXPsU7ubvVLKp+xnAQAAcBehGADW8/lldUfOr39tFUXdW/zOdDEAAMCfCcUAsJo6lfq3tmbi0tmNJSKOa+A3XQwAAPBHQjEAPMyntof4ICLOndm4auBv08VvTBcDAAD8TigGgPvdDsT2EC9IRJy03cW/ZD8LAAAAoRgAvk4gTqDtLn5bSvneOgoAACAzoRgA/qi+pO57gTiXW+sofhCMAQCAjIRiACjlqpTyvpTyVy+py61+c0AwBgAAMhKKAcjsYynlVUTsRcRRXUPgdwPlz8H4g0MBAACWTigGIJuLUsq7Nj18GBGnfgdwlxaMX7cdxnXq/MZhAQAASyQUA5DBRYt8dffwfkQcmx5mFW2HcZ06f1qn0Ns0OgAAwGJ85yoBWKgah09KKad2DrNJbQr9dJqmGo0PSyl14viFQwYAAEYmFAOwFHUlQA14Zy0Omxhmq9rvsfrNiJNb0bh+6m7jJ04fAAAYiVAMwKiuSinnLQzXPbLnbpK53I7G9RGmaTpowfjAtDEAADACoRiAEdzcisL113PrJOhZfQle+/36mxaO9299nrtAAACgJ0Lxcp3c/h9UgFG14AZD+zIcl9/jcQ3Gey0e7936PHPbAADArgnFC9Um7UzbAUCn2rqU87Zb+w/azuP99vdu//VtB+4WAADYlCkiHCYAAAAAQGJ/cfkAAAAAALkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAyQnFAAAAAADJCcUAAAAAAMkJxQAAAAAAmZVS/gt+mQAuFVPI0gAAAABJRU5ErkJggg==""")
            image = Image.open(BytesIO(icon_data))


            self.tray_icon = pystray.Icon(APP_NAME, image, "Acuerdo Monitor", menu=pystray.Menu(
                pystray.MenuItem("Salir", self._exit_app)
            ))

            # Iniciar ícono en otro hilo para no bloquear la app
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            self._log_error(f"Error creando tray icon: {e}")

    def _log_info(self, message):
        """Registra mensajes informativos"""
        print(f"[INFO] {message}")
        # Podrías agregar logging a archivo aquí si es necesario

    def _log_error(self, message):
        """Registra mensajes de error"""
        print(f"[ERROR] {message}", file=sys.stderr)
        # Podrías agregar logging a archivo aquí si es necesario

    def start(self):
        """Inicia el monitor en segundo plano"""
        if not self.running:
            self.running = True

            # Iniciar el icono en la bandeja
            self._create_tray_icon()

            # Iniciar el monitor de cambios
            monitor_thread = threading.Thread(
                target=self._monitor_changes,
                daemon=True
            )
            monitor_thread.start()

            self._log_info(f"Monitor iniciado. Observando acuerdos cerrados en: {self.db_path}")

    def stop(self):
        """Detiene el monitor limpiamente"""
        print("\n[DETENER] Deteniendo AcuerdoMonitor...")
        self.running = False
        if self.tray_icon:
            print("[DETENER] Cerrando icono en bandeja...")
            self.tray_icon.stop()
        if self.mutex:
            print("[DETENER] Liberando mutex...")
            win32event.ReleaseMutex(self.mutex)
            win32api.CloseHandle(self.mutex)
        print("[DETENER] Saliendo del programa")
        sys.exit(0)


def _show_status(self):
    """Muestra el estado actual del monitor"""
    try:
        self._show_notification(
            "Estado del Monitor",
            f"Monitor activo. Último ID verificado: {self.last_checked_id}",
            None
        )
    except Exception as e:
        self._log_error(f"Error mostrando estado: {e}")



if __name__ == "__main__":

    from PyInstaller.utils.hooks import collect_data_files

    datas = collect_data_files('pystray')

    # Verificar si estamos en Windows
    if not sys.platform.startswith('win'):
        print("Este software solo es compatible con Windows.")
        sys.exit(1)

    try:
        monitor = AcuerdoMonitor(DB_PATH)
        monitor.start()
        # Mantener el programa en ejecución
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
    except Exception as e:
        print(f"Error fatal: {e}")
        sys.exit(1)
