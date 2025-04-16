import tkinter as tk
from tkinter import Toplevel, Tk
import ctypes
import sys
import win32api


def print_monitor_info(monitors):
    """Imprime información detallada de los monitores disponibles"""
    print("\nMonitores detectados:")
    for i, monitor in enumerate(monitors, 1):
        print(f"Monitor {i}:")
        print(f"  Área de trabajo: {monitor['Work']}")
        print(f"  Área completa: {monitor['Monitor']}")
        print(f"  Primary: {'Sí' if monitor.get('Flags', 0) == 1 else 'No'}")
    print()


def get_monitor_info():
    """Obtiene información de monitores y la imprime"""
    monitors = []
    try:
        monitor_tuples = win32api.EnumDisplayMonitors(None, None)
        for mon in monitor_tuples:
            info = win32api.GetMonitorInfo(mon[0])
            monitors.append(info)

        # Imprimir información de los monitores
        print_monitor_info(monitors)
        return monitors
    except Exception as e:
        print(f"Error al enumerar monitores: {e}")
        return None


def get_largest_monitor():
    """Obtiene el monitor con mayor área de trabajo"""
    try:
        monitors = get_monitor_info() or []
        if not monitors:
            user32 = ctypes.windll.user32
            return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)), "Monitor primario (fallback)"

        largest = max(monitors, key=lambda m: (m['Work'][2] - m['Work'][0]) * (m['Work'][3] - m['Work'][1]))

        # Identificar si es el monitor primario
        monitor_name = "Monitor principal" if largest.get('Flags', 0) == 1 else "Monitor secundario"
        return largest['Work'], monitor_name
    except Exception as e:
        print(f"Error crítico: {e}")
        user32 = ctypes.windll.user32
        return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)), "Monitor primario (fallback)"


def move_to_largest_monitor(window):
    """Mueve la ventana al monitor principal y reporta dónde se movió"""
    try:
        if not window.winfo_exists():
            return

        work_area, monitor_name = get_largest_monitor()
        l, t, r, b = work_area

        window.update_idletasks()
        width = window.winfo_width() or 400
        height = window.winfo_height() or 300

        x = l + (r - l - width) // 2
        y = t + (b - t - height) // 2

        window.geometry(f"+{x}+{y}")
        window.lift()

        # Reportar dónde se movió la ventana
        print(f"\nVentana '{window.title()}' movida a:")
        print(f"  Monitor: {monitor_name}")
        print(f"  Posición: ({x}, {y})")
        print(f"  Dimensiones: {width}x{height}")
        print(f"  Área de trabajo del monitor: {work_area}\n")

    except Exception as e:
        print(f"Error moviendo {window.title()}: {str(e)}")