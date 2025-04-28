import tkinter as tk
from tkinter import Toplevel, Tk
import ctypes
from ctypes import wintypes
import win32api
from threading import Lock


# Al inicio del módulo, justo después de tus imports:
MonitorEnumProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL,        # return type
    wintypes.HMONITOR,    # hMonitor
    wintypes.HDC,         # hdcMonitor
    ctypes.POINTER(wintypes.RECT),  # lprcMonitor
    wintypes.LPARAM       # dwData
)


# Configurar DPI Awareness al inicio de la aplicación
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception as e:
    print("Error setting DPI awareness:", e)
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception as e:
        print("Error setting fallback DPI awareness:", e)


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('rcMonitor', wintypes.RECT),
        ('rcWork', wintypes.RECT),
        ('dwFlags', wintypes.DWORD),
        ('szDevice', wintypes.WCHAR * 32)
    ]


class WindowManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.special_windows_titles = ["Gestión de Acuerdos", "Registrar Nuevo Acuerdo", "Editar Responsables", "Nueva Minuta", "Administración de Host"]
        self.main_window_position = None
        self.main_window_size = None
        self.user_moved_windows = set()
        self.window_dpi = {}
        self.currently_moving = False

    def get_monitor_info(self):
        monitors = []

        # Esta es la función que EnumDisplayMonitors va a llamar
        def _callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            info = MONITORINFOEX()
            info.cbSize = ctypes.sizeof(MONITORINFOEX)
            # Llenamos MONITORINFOEX
            if ctypes.windll.user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                # Obtenemos DPI
                try:
                    shcore = ctypes.windll.shcore
                    dpiX = wintypes.UINT()
                    dpiY = wintypes.UINT()
                    shcore.GetDpiForMonitor(hMonitor, 0, ctypes.byref(dpiX), ctypes.byref(dpiY))
                    dpi = dpiX.value
                except Exception:
                    dc = ctypes.windll.user32.GetDC(0)
                    dpi = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)
                    ctypes.windll.user32.ReleaseDC(0, dc)

                monitors.append({
                    'Monitor': (
                        info.rcMonitor.left, info.rcMonitor.top,
                        info.rcMonitor.right, info.rcMonitor.bottom
                    ),
                    'Work': (
                        info.rcWork.left, info.rcWork.top,
                        info.rcWork.right, info.rcWork.bottom
                    ),
                    'Flags': info.dwFlags,
                    'DPI': dpi
                })
            return True  # continuar enumerando
        # Convertimos la función Python en un CALLBACK válido
        callback_fn = MonitorEnumProc(_callback)

        # Ahora pasamos el puntero correcto como tercer parámetro
        ctypes.windll.user32.EnumDisplayMonitors(
            None, None,
            callback_fn,
            0
        )
        return monitors

    def get_monitor_for_window(self, window):
        x = window.winfo_x()
        y = window.winfo_y()
        monitors = self.get_monitor_info()
        for monitor in monitors:
            m_left, m_top, m_right, m_bottom = monitor['Monitor']
            if m_left <= x < m_right and m_top <= y < m_bottom:
                return monitor
        return None

    def get_best_monitor(self):
        try:
            monitors = self.get_monitor_info()
            if not monitors:
                user32 = ctypes.windll.user32
                return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)), "Fallback", 96

            def calculate_area(work_area):
                return (work_area[2] - work_area[0]) * (work_area[3] - work_area[1])

            primary = [m for m in monitors if m['Flags'] == 1]
            if primary:
                primary = primary[0]
            else:
                primary = None

            largest = max(monitors, key=lambda m: calculate_area(m['Work']))

            if primary and calculate_area(primary['Work']) == calculate_area(largest['Work']):
                best = primary
                name = "Monitor principal"
            else:
                non_primary = [m for m in monitors if m['Flags'] != 1]
                if non_primary:
                    best = max(non_primary, key=lambda m: calculate_area(m['Work']))
                    name = "Monitor secundario"
                else:
                    best = largest
                    name = "Monitor más grande"

            return best['Work'], name, best['DPI']
        except Exception as e:
            print(f"Error: {e}")
            user32 = ctypes.windll.user32
            return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)), "Fallback", 96

    def move_to_largest_monitor(self, window):
        if not window.winfo_exists() or self.currently_moving:
            return

        self.currently_moving = True
        try:
            if window.title() in self.special_windows_titles:
                self._handle_special_window(window)
            else:
                self._move_normal_window(window)
            self._adjust_for_dpi(window)
        finally:
            self.currently_moving = False

    def _handle_special_window(self, window):
        title = window.title()
        work_area, monitor_name, dpi = self.get_best_monitor()
        scale = dpi / 96.0
        print(f"la ventana es: {title}")

        if title == "Gestión de Acuerdos":
            base_width = 1400
            base_height = 700
            width = int(base_width * scale)
            height = int(base_height * scale)
            l, t, r, b = work_area
            x = l + (r - l - width) // 2
            y = t + (b - t - height) // 2

            window.geometry(f"{width}x{height}+{x}+{y}")
            window.resizable(True, True)
            self.main_window_position = (x, y)
            self.main_window_size = (width, height)
            self.window_dpi[window] = dpi

            window.bind("<Configure>", lambda e: self._update_main_position(e, window))

        elif title == "Registrar Nuevo Acuerdo":
            if self.main_window_position:
                main_x, main_y = self.main_window_position
                main_width, main_height = self.main_window_size
                base_width = 1200
                base_height = 800
                width = int(base_width * scale)
                height = int(base_height * scale)
                new_x = main_x + main_width + int(20 * scale)
                new_y = main_y
            else:
                l, t, r, b = work_area
                base_width = 1200
                base_height = 800
                width = int(base_width * scale)
                height = int(base_height * scale)
                new_x = l + (r - l - width) // 2
                new_y = t + (b - t - height) // 2

            window.geometry(f"{width}x{height}+{new_x}+{new_y}")
            window.resizable(True, True)
            self.window_dpi[window] = dpi

        elif title == "Editar Responsables":
            if self.main_window_position:
                main_x, main_y = self.main_window_position
                main_width, main_height = self.main_window_size
                base_width = 750
                base_height = 450
                width = int(base_width * scale)
                height = int(base_height * scale)
                new_x = main_x + main_width + int(20 * scale)
                new_y = main_y
            else:
                l, t, r, b = work_area
                base_width = 1200
                base_height = 800
                width = int(base_width * scale)
                height = int(base_height * scale)
                new_x = l + (r - l - width) // 2
                new_y = t + (b - t - height) // 2

            window.geometry(f"{width}x{height}+{new_x}+{new_y}")
            window.resizable(True, True)
            self.window_dpi[window] = dpi

        elif title == "Nueva Minuta":
            print("afirmativo")
            if self.main_window_position:
                main_x, main_y = self.main_window_position
                main_width, main_height = self.main_window_size
                base_width = 400
                base_height = 450
                width = int(base_width * scale)
                height = int(base_height * scale)
                new_x = main_x + main_width + int(20 * scale)
                new_y = main_y
            else:
                l, t, r, b = work_area
                base_width = 400
                base_height = 450
                width = int(base_width * scale)
                height = int(base_height * scale)
                new_x = l + (r - l - width) // 2
                new_y = t + (b - t - height) // 2

            window.geometry(f"{width}x{height}+{new_x}+{new_y}")
            window.resizable(True, True)
            self.window_dpi[window] = dpi

        elif title == "Administración de Host":
            if self.main_window_position:
                main_x, main_y = self.main_window_position
                main_width, main_height = self.main_window_size
                base_width = 750
                base_height = 450
                width = int(base_width * scale)
                height = int(base_height * scale)
                new_x = main_x + main_width + int(20 * scale)
                new_y = main_y
            else:
                l, t, r, b = work_area
                base_width = 1500
                base_height = 500
                width = int(base_width * scale)
                height = int(base_height * scale)
                new_x = l + (r - l - width) // 2
                new_y = t + (b - t - height) // 2

            window.geometry(f"{width}x{height}+{new_x}+{new_y}")
            window.resizable(True, True)
            self.window_dpi[window] = dpi

        window.bind("<Configure>", lambda e: self._check_user_move(e, window))

    def _update_main_position(self, event, window):
        if window.title() == "Gestión de Acuerdos":
            self.main_window_position = (window.winfo_x(), window.winfo_y())
            self.main_window_size = (window.winfo_width(), window.winfo_height())

    def _check_user_move(self, event, window):
        # 1) Si el usuario ya movió manualmente la ventana, no hacemos nada
        if window in self.user_moved_windows:
            return

        # 2) Ajustar tamaño si cambió el DPI
        current_monitor = self.get_monitor_for_window(window)
        if current_monitor:
            current_dpi = current_monitor['DPI']
            previous_dpi = self.window_dpi.get(window, current_dpi)
            if current_dpi != previous_dpi:
                self._adjust_window_for_dpi(window, current_dpi, previous_dpi)
                self.window_dpi[window] = current_dpi

        # 3) Detectar movimiento/resize manual comparando con la posición “esperada”
        current_x = window.winfo_x()
        current_y = window.winfo_y()
        expected_x, expected_y = self._get_expected_position(window)

        # Umbral de tolerancia en píxeles
        threshold = 10
        if abs(current_x - expected_x) > threshold or abs(current_y - expected_y) > threshold:
            self.user_moved_windows.add(window)
            print(f"Modo manual activado: {window.title()}")

        current_monitor = self.get_monitor_for_window(window)
        if not current_monitor:
            return

        current_dpi = current_monitor['DPI']
        previous_dpi = self.window_dpi.get(window, current_dpi)

        if current_dpi != previous_dpi:
            self._adjust_window_for_dpi(window, current_dpi, previous_dpi)
            self.window_dpi[window] = current_dpi

        if window not in self.user_moved_windows:
            current_x = window.winfo_x()
            current_y = window.winfo_y()

            expected_x, expected_y = self._get_expected_position(window)
            if abs(current_x - expected_x) > 10 or abs(current_y - expected_y) > 10:
                self.user_moved_windows.add(window)
                print(f"Modo manual activado: {window.title()}")

    def _get_expected_position(self, window):
        if window.title() == "Gestión de Acuerdos":
            return self.main_window_position or (window.winfo_x(), window.winfo_y())
        else:
            if self.main_window_position:
                main_x, main_y = self.main_window_position
                main_width, main_height = self.main_window_size or (0, 0)
                return (main_x + main_width + 20, main_y)
            else:
                return (window.winfo_x(), window.winfo_y())

    def _adjust_window_for_dpi(self, window, new_dpi, old_dpi):
        scale = new_dpi / old_dpi
        width = int(window.winfo_width() * scale)
        height = int(window.winfo_height() * scale)
        window.geometry(f"{width}x{height}")

    def _adjust_for_dpi(self, window):
        current_monitor = self.get_monitor_for_window(window)
        if current_monitor:
            current_dpi = current_monitor['DPI']
            self.window_dpi[window] = current_dpi

    def _move_normal_window(self, window):
        work_area, monitor_name, dpi = self.get_best_monitor()
        scale = dpi / 96.0
        l, t, r, b = work_area

        base_width = 400
        base_height = 300
        width = int(base_width * scale)
        height = int(base_height * scale)

        width = min(width, r - l - 40)
        height = min(height, b - t - 40)

        x = l + (r - l - width) // 2
        y = t + (b - t - height) // 2

        window.geometry(f"{width}x{height}+{x}+{y}")
        window.resizable(True, True)
        self.window_dpi[window] = dpi

# debe de funcionar solo recibiendo la ventana
def move_to_largest_monitor(window):
    # Configurar DPI Awareness al inicio de la aplicación
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print("Error setting DPI awareness:", e)
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception as e:
            print("Error setting fallback DPI awareness:", e)

    WindowManager().move_to_largest_monitor(window)