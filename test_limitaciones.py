import tkinter as tk
from tkinter import Toplevel
import platform
import ctypes
import getpass

def bloquear_ventana_robusta(ventana):
    """
    Bloquea una ventana Tkinter para que:
    - Abra en el tamaño más grande posible (debe establecerse como maximizada antes de llamar a esta función).
    - Muestre bordes y botón de cerrar.
    - Permita minimizar.
    - Si permita maximizar.
    - No permita redimensionar.
    - Permita cambiar de ventana.
    - Muestre la barra de tareas.

    Args:
        ventana (tk.Tk o tk.Toplevel): Ventana que se desea bloquear
    """
    # Verificar si el usuario es "jhuizar"
    if getpass.getuser().lower() != "lmacias":
        return  # No hacer nada si el usuario no es "jhuizar"

    # Evitar redimensionamiento
    ventana.resizable(False, False)

    # Desactivar el atributo topmost si estaba activo
    ventana.attributes('-topmost', False)

    # Obtener tamaño inicial después de cargar
    ventana.update_idletasks()
    w, h = ventana.winfo_width(), ventana.winfo_height()
    ventana._dimensiones_iniciales = (w, h)

    # Configurar geometría inicial (solo tamaño)
    ventana.geometry(f"{w}x{h}")

    if platform.system() == "Windows":
        _bloquear_ventana_windows(ventana)

    # Reforzar tamaño en caso de cambios
    ventana.bind("<Configure>", lambda e: _corregir_geometria(ventana))


def _bloquear_ventana_windows(ventana):
    """Bloqueo específico para Windows: remover botón de maximizar y borde de redimensionar"""
    try:
        hwnd = ctypes.windll.user32.GetParent(ventana.winfo_id())

        GWL_STYLE = -16
        WS_MAXIMIZEBOX = 0x00010000  # Botón de maximizar
        WS_THICKFRAME = 0x00040000   # Borde de redimensionar

        # Obtener y modificar estilos
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~(WS_MAXIMIZEBOX | WS_THICKFRAME)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        # Forzar actualización de la ventana
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                      0x0002 | 0x0001 | 0x0020)
    except Exception as e:
        print(f"Error al aplicar estilos de ventana en Windows: {e}")


def _corregir_geometria(ventana):
    """Mantiene el tamaño inicial de la ventana"""
    if ventana.state() != 'iconic':  # Si no está minimizada
        # Corregir solo si el tamaño ha cambiado
        ancho_actual = ventana.winfo_width()
        alto_actual = ventana.winfo_height()
        if (ancho_actual != ventana._dimensiones_iniciales[0] or
            alto_actual != ventana._dimensiones_iniciales[1]):
            ventana.geometry(f"{ventana._dimensiones_iniciales[0]}x{ventana._dimensiones_iniciales[1]}")