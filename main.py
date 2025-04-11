from common import *
from sql.db import db_create
from Menu.Menu import show_main_menu  # ahora ejecutaremos la ventana Menu
import locale
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')


import babel
from babel import numbers  # Importación explícita

print(babel.__version__)
print(numbers.format_currency(1234.56, 'USD', locale='en_US'))  # Prueba funcional

def main():


    # Crear/verificar la base de datos
    db_create()
    from sql.db import buscar_minutas_db
    db_path = buscar_minutas_db()
    print(db_path)
    print("Listo")
    # Mostrar el menú principal pasando la ruta
    show_main_menu(db_path)


if __name__ == "__main__":
    main()