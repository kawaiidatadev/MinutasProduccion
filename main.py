from common import *
from sql.db import db_create
from Menu.Menu import show_main_menu
import locale
from Ejecutable_Inicializador import ejecutable_run


def main():
    verificar_imports()
    # Configuración regional
    try:
        ejecutable_run()
    except Exception as e:
        print(f"Error al ejecutar inicializador: {str(e)}")


    # Crear/verificar la base de datos
    db_path = db_create()
    print(db_path)


    # Mostrar el menú principal inicialmente
    show_main_menu(db_path)


if __name__ == "__main__":
    main()