import tkinter as tk
from tkinter import Toplevel
import platform
import ctypes
import getpass

def bloquear_ventana_robusta(ventana):
    """
    Bloquea una ventana Tkinter para que:
    - Muestre bordes y botón de cerrar
    - Permita minimizar
    - No se pueda maximizar ni redimensionar
    - No se pueda cambiar de pantalla (posición fija)
    - Permita ver la barra de tareas

    Args:
        ventana (tk.Tk o tk.Toplevel): Ventana que se desea bloquear
    """
    # Verificar si el usuario es "jhuizar"
    if getpass.getuser().lower() != "jhuizar":
        return  # No hacer nada si el usuario no es "jhuizar"

    # Evitar redimensionamiento
    ventana.resizable(False, False)

    # Asegurarse de que la ventana no esté maximizada
    ventana.state('normal')

    # Desactivar el atributo topmost si estaba activo
    ventana.attributes('-topmost', False)

    # Obtener posición y tamaño inicial (una vez cargada)
    ventana.update_idletasks()
    x, y = ventana.winfo_x(), ventana.winfo_y()
    w, h = ventana.winfo_width(), ventana.winfo_height()
    ventana._posicion_inicial = (x, y)
    ventana._dimensiones_iniciales = (w, h)

    # Fijar geometría
    ventana.geometry(f"{w}x{h}+{x}+{y}")

    if platform.system() == "Windows":
        _bloquear_ventana_windows(ventana)

    # Reforzar geometría en caso de movimientos
    ventana.bind("<Configure>", lambda e: _corregir_geometria(ventana))


def _bloquear_ventana_windows(ventana):
    """Bloqueo específico para Windows: permite cerrar con 'X' y minimizar"""
    try:
        hwnd = ctypes.windll.user32.GetParent(ventana.winfo_id())

        GWL_STYLE = -16
        WS_MAXIMIZEBOX = 0x00010000  # Maximizar
        WS_THICKFRAME = 0x00040000  # Redimensionar con bordes

        # Obtener estilo actual y desactivar lo no deseado
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~(WS_MAXIMIZEBOX | WS_THICKFRAME)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        # Asegurarse de que la ventana no esté maximizada
        SW_SHOWNORMAL = 1
        ctypes.windll.user32.ShowWindow(hwnd, SW_SHOWNORMAL)

        # Refrescar ventana para aplicar estilo
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                      0x0002 | 0x0001 | 0x0020)
    except Exception as e:
        print(f"Error al aplicar estilos de ventana en Windows: {e}")


def _corregir_geometria(ventana):
    """Evita que se cambie la posición de la ventana"""
    # Solo corregir si no está minimizada
    if ventana.state() != 'iconic':
        # Asegurarse de que la ventana no esté maximizada
        if ventana.state() == 'zoomed':
            ventana.state('normal')
        ventana.geometry(f"{ventana._dimensiones_iniciales[0]}x{ventana._dimensiones_iniciales[1]}+"
                     f"{ventana._posicion_inicial[0]}+{ventana._posicion_inicial[1]}")