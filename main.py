from common import *
from sql.db import db_create
from Menu.Menu import show_main_menu
from monitor_exe import ejecutar_monitor
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
    db_path = db_create()
    print(db_path)


    # Mostrar el menú principal inicialmente
    show_main_menu(db_path)


if __name__ == "__main__":
    main()