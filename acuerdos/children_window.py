from common import *

def center_child_window(child_window, parent_window):
    """Centra una ventana hija respecto a la ventana principal"""
    child_window.update_idletasks()
    width = child_window.winfo_width()
    height = child_window.winfo_height()

    x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - (width // 2)
    y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - (height // 2)

    child_window.geometry(f'{width}x{height}+{x}+{y}')