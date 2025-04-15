import sqlite3
import os
import getpass
from datetime import datetime
import tkinter as tk
from tkinter import messagebox


class MinutasDB:
    def __init__(self, root=None):
        self.root = root
        self.current_user = getpass.getuser()
        self.db_created = False
        self.db_path = r'\\mercury\Producción\Minutas Produccion\Program Files\minutas.db'

        # Intentar crear la base de datos en la ubicación especificada
        if not self.try_create_db():
            error_msg = f"No se pudo crear/acceder a la base de datos en:\n{self.db_path}"
            if self.root:
                messagebox.showerror("Error", error_msg)
            else:
                print(error_msg)
            raise Exception(error_msg)

    def try_create_db(self):
        """Intenta crear/verificar la base de datos en la ubicación de red"""
        try:
            # Crear directorios si no existen
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            # Verificar si podemos escribir en la ubicación
            test_file = os.path.join(db_dir, "test.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)

            # Crear la estructura de la base de datos
            self.create_database()
            return True

        except Exception as e:
            return False

    def create_database(self):
        """Crea la estructura de la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Tabla acuerdos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS acuerdos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_acuerdo TEXT NOT NULL,
                    acuerdo TEXT NOT NULL,
                    responsables TEXT NOT NULL,
                    fecha_compromiso TEXT NOT NULL,
                    fecha_registro TEXT NOT NULL,
                    usuario_registra TEXT NOT NULL,
                    estatus TEXT NOT NULL DEFAULT 'Activo',
                    fecha_estatus TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    comentarios_cierre TEXT DEFAULT '',
                    comentarios TEXT DEFAULT '',
                    accion TEXT DEFAULT 'Cerrar'
                )
            ''')

            # Tabla historial de acuerdos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS historial_acuerdos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_acuerdo TEXT NOT NULL,
                    acuerdo TEXT NOT NULL,
                    responsables TEXT NOT NULL,
                    fecha_compromiso TEXT NOT NULL,
                    fecha_modificacion TEXT NOT NULL,
                    usuario_modifico TEXT NOT NULL,
                    estatus TEXT NOT NULL,
                    comentarios_cierre TEXT DEFAULT '',
                    comentarios TEXT DEFAULT '',
                    ruta_pdf TEXT,
                    FOREIGN KEY (id_acuerdo) REFERENCES acuerdos(id_acuerdo)
                )
            ''')

            conn.commit()
            conn.close()

        except sqlite3.Error as e:
            raise Exception(f"Error al crear la base de datos: {e}")

    def get_current_timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def agregar_acuerdo(self, id_acuerdo, acuerdo, responsables, fecha_compromiso):
        """Agrega un nuevo acuerdo a la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO acuerdos 
                (id_acuerdo, acuerdo, responsables, fecha_compromiso, fecha_registro, usuario_registra) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (id_acuerdo, acuerdo, responsables, fecha_compromiso,
                 self.get_current_timestamp(), self.current_user)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error al agregar acuerdo: {e}")
            return False


def db_create():
    root = tk.Tk()
    root.withdraw()

    try:
        minutas = MinutasDB(root)
        root.destroy()
        return minutas.db_path
    except Exception as e:
        root.destroy()
        return str(e)