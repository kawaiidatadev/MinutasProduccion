from common import *

def center_window(window):
    """Centra la ventana en la pantalla"""
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')

    # Maximizar la ventana según el sistema operativo
    if sys.platform == 'win32':
        window.state('zoomed')  # Para Windows