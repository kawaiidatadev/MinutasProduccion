import tkinter as tk
from tkinter import Toplevel, Tk
import ctypes
import win32api
from threading import Lock


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
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True
        self.special_windows_titles = ["Gestión de Acuerdos", "Registrar Nuevo Acuerdo"]
        self.main_window_position = None
        self.main_window_size = None
        self.user_moved = False
        self.currently_moving = False

    def print_monitor_info(self, monitors):
        """Imprime información de monitores (debug)"""
        print("\nMonitores detectados:")
        for i, monitor in enumerate(monitors, 1):
            print(f"Monitor {i}:")
            print(f"  Área de trabajo: {monitor['Work']}")
            print(f"  Área completa: {monitor['Monitor']}")
            print(f"  Primary: {'Sí' if monitor.get('Flags', 0) == 1 else 'No'}")
        print()

    def get_monitor_info(self):
        """Obtiene información de todos los monitores"""
        monitors = []
        try:
            monitor_tuples = win32api.EnumDisplayMonitors(None, None)
            for mon in monitor_tuples:
                info = win32api.GetMonitorInfo(mon[0])
                monitors.append(info)
            return monitors
        except Exception as e:
            print(f"Error al enumerar monitores: {e}")
            return None

    def get_best_monitor(self):
        """Selecciona el mejor monitor según las reglas establecidas"""
        try:
            monitors = self.get_monitor_info() or []
            if not monitors:
                user32 = ctypes.windll.user32
                return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)), "Monitor primario (fallback)"

            if len(monitors) == 1:
                monitor = monitors[0]
                monitor_name = "Monitor principal" if monitor.get('Flags', 0) == 1 else "Único monitor"
                return monitor['Work'], monitor_name

            def calculate_area(work_area):
                return (work_area[2] - work_area[0]) * (work_area[3] - work_area[1])

            primary_monitor = next((m for m in monitors if m.get('Flags', 0) == 1), None)
            largest_monitor = max(monitors, key=lambda m: calculate_area(m['Work']))

            if primary_monitor is None or largest_monitor == primary_monitor:
                monitor_name = "Monitor principal (más grande)"
                return largest_monitor['Work'], monitor_name
            else:
                non_primary = [m for m in monitors if m.get('Flags', 0) != 1]
                if non_primary:
                    best_monitor = max(non_primary, key=lambda m: calculate_area(m['Work']))
                    monitor_name = "Monitor secundario (más grande no principal)"
                    return best_monitor['Work'], monitor_name
                else:
                    monitor_name = "Monitor más grande (fallback)"
                    return largest_monitor['Work'], monitor_name

        except Exception as e:
            print(f"Error crítico: {e}")
            user32 = ctypes.windll.user32
            return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)), "Monitor primario (fallback)"

    def move_to_largest_monitor(self, window):
        """Función principal que maneja el posicionamiento de todas las ventanas"""
        if not window.winfo_exists():
            return

        if self.currently_moving:
            return

        self.currently_moving = True
        try:
            if window.title() in self.special_windows_titles:
                self._handle_special_window(window)
            else:
                self._move_normal_window(window)
        finally:
            self.currently_moving = False

    def _handle_special_window(self, window):
        """Maneja el posicionamiento de las ventanas especiales"""
        if window.title() == "Gestión de Acuerdos":
            work_area, monitor_name = self.get_best_monitor()
            l, t, r, b = work_area

            width = 1400
            height = 700
            x = l + (r - l - width) // 2
            y = t + (b - t - height) // 2

            window.geometry(f"{width}x{height}+{x}+{y}")
            window.resizable(True, True)  # Permitir maximizar
            self.main_window_position = (x, y)
            self.main_window_size = (width, height)

            window.bind("<Configure>", self._update_main_position)

        elif window.title() == "Registrar Nuevo Acuerdo":
            if self.main_window_position:
                main_x, main_y = self.main_window_position
                main_width, main_height = self.main_window_size

                width = 1200
                height = 800
                new_x = main_x + main_width + 20
                new_y = main_y

                window.geometry(f"{width}x{height}+{new_x}+{new_y}")
            else:
                work_area, monitor_name = self.get_best_monitor()
                l, t, r, b = work_area
                width = 1200
                height = 800
                x = l + (r - l - width) // 2
                y = t + (b - t - height) // 2
                window.geometry(f"{width}x{height}+{x}+{y}")

            window.resizable(True, True)  # Permitir maximizar

        window.bind("<Configure>", lambda e: self._check_user_move(window))

    def _update_main_position(self, event):
        """Actualiza la posición de la ventana principal cuando se mueve"""
        if event.widget.title() == "Gestión de Acuerdos":
            self.main_window_position = (event.x, event.y)22
            self.main_window_size = (event.width, event.height)

    def _check_user_move(self, window):
        """Detecta si el usuario mueve manualmente la ventana"""
        if not self.user_moved:
            current_x = window.winfo_x()
            current_y = window.winfo_y()

            if window.title() == "Gestión de Acuerdos":
                expected_x, expected_y = self.main_window_position
            else:
                if self.main_window_position:
                    expected_x = self.main_window_position[0] + self.main_window_size[0] + 20
                    expected_y = self.main_window_position[1]
                else:
                    return

            if abs(current_x - expected_x) > 10 or abs(current_y - expected_y) > 10:
                self.user_moved = True
                print("Modo manual activado: el usuario movió la ventana")

    def _move_normal_window(self, window):
        """Mueve una ventana normal al mejor monitor disponible"""
        work_area, monitor_name = self.get_best_monitor()
        l, t, r, b = work_area
        window.update_idletasks()

        width = min(window.winfo_width() or 400, r - l - 40)
        height = min(window.winfo_height() or 300, b - t - 40)

        x = l + (r - l - width) // 2
        y = t + (b - t - height) // 2

        window.geometry(f"{width}x{height}+{x}+{y}")
        window.resizable(True, True)  # Permitir maximizar


def move_to_largest_monitor(window):
    """Función de interfaz mantenida para compatibilidad"""
    WindowManager().move_to_largest_monitor(window)