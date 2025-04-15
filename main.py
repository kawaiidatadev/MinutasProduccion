from common import *
from sql.db import db_create, buscar_minutas_db
from Menu.Menu import show_main_menu
from tkinter import Tk, Toplevel
import sys
from monitor_exe import ejecutar_monitor
from common import *
from sql.db import db_create, buscar_minutas_db
from Menu.Menu import show_main_menu
import locale

def main():


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