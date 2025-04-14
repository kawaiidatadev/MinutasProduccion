from common import *
from sql.db import db_create, buscar_minutas_db
from Menu.Menu import show_main_menu
from tkinter import Tk, Toplevel
import sys
from monitor_exe import ejecutar_monitor



def maximize_all_windows():
    """Decorador para asegurar que todas las ventanas Tkinter se abran maximizadas"""

    def decorator(window_class):
        original_init = window_class.__init__

        def __init_wrapper__(self, *args, **kwargs):
            original_init(self, *args, **kwargs)

            # Maximizar según el sistema operativo
            if sys.platform == 'win32':
                self.state('zoomed')  # Windows
            elif sys.platform == 'darwin':
                self.attributes('-fullscreen', True)  # macOS
            else:
                self.attributes('-zoomed', True)  # Linux

                # Maximizar la ventana según el sistema operativo
            if sys.platform == 'win32':
                self.state('zoomed')  # Para Windows

            # Centrar en la pantalla principal
            self.update_idletasks()
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            window_width = self.winfo_width()
            window_height = self.winfo_height()

            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2

            self.geometry(f"+{x}+{y}")

        window_class.__init__ = __init_wrapper__
        return window_class

    # Aplicar a las clases base de Tkinter
    Tk.__init__ = decorator(Tk).__init__
    Toplevel.__init__ = decorator(Toplevel).__init__

    return decorator
from common import *
from sql.db import db_create, buscar_minutas_db
from Menu.Menu import show_main_menu
import locale

def main():
    # Aplicar el decorador a todas las ventanas Tkinter
    maximize_all_windows()

    verificar_imports()

    # Configuración regional
    try:
        ejecutar_monitor()
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        locale.setlocale(locale.LC_ALL, '')

    # Crear/verificar la base de datos
    db_create()
    db_path = buscar_minutas_db()

    # Mostrar el menú principal
    show_main_menu(db_path)

if __name__ == "__main__":
    main()