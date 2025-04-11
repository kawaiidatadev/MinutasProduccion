import sqlite3
import os
import getpass
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

import os


def buscar_minutas_db():
    rutas = [
        r'\\mercury\Mtto_Prod\00_Departamento_Mantenimiento\Minutas\minutas.db',
        os.path.join(os.path.expanduser("~"), "Documents", "Minutas", "minutas.db"),
        os.path.join(os.getcwd(), "Minutas", "minutas.db")
    ]

    for ruta in rutas:
        if os.path.exists(ruta):
            return ruta

    return "Error: 'minutas.db' no se encuentra en ninguna de las rutas especificadas."


class MinutasDB:
    def __init__(self, root=None):
        self.root = root
        self.current_user = getpass.getuser()
        self.db_created = False
        self.db_path = ""

        # Opciones de ubicación para la base de datos
        self.location_options = [
            {
                'name': "Red (Mercury)",
                'path': r"\\mercury\Mtto_Prod\00_Departamento_Mantenimiento\Minutas\minutas.db",
                'description': "Ubicación compartida en red para todos los usuarios"
            },
            {
                'name': "Documentos del usuario",
                'path': os.path.join(os.path.expanduser("~"), "Documents", "Minutas", "minutas.db"),
                'description': "Ubicación privada en tus documentos"
            },
            {
                'name': "Directorio portable",
                'path': os.path.join(os.path.dirname(os.path.abspath(__file__)), "Minutas", "minutas.db"),
                'description': "Ubicación portable junto al ejecutable"
            }
        ]

        # Intentar con la ubicación preferida primero
        if not self.try_create_db(self.location_options[0]['path']):
            # Si falla, mostrar opciones al usuario
            self.show_location_options()

        # Actualizar la variable global con la ubicación seleccionada
        global global_db_path
        global_db_path = self.db_path

    def try_create_db(self, db_path):
        """Intenta crear la base de datos en la ubicación especificada"""
        try:
            # Crear directorio si no existe
            db_dir = os.path.dirname(db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            # Probar si podemos escribir en la ubicación
            test_file = os.path.join(db_dir, "test.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)

            # Crear la base de datos
            self.create_database(db_path)
            self.db_path = db_path
            self.db_created = True
            return True

        except Exception as e:
            error_msg = f"No se pudo crear la base de datos en:\n{db_path}\n\nError: {str(e)}"
            if self.root:
                messagebox.showerror("Error", error_msg)
            else:
                print(error_msg)
            return False

    def show_location_options(self):
        """Muestra las opciones de ubicación al usuario mediante Tkinter"""
        if not self.root:
            print("No se pudo mostrar la interfaz gráfica. Creando en ubicación alternativa...")
            for option in self.location_options[1:]:
                if self.try_create_db(option['path']):
                    break
            return

        # Crear ventana de selección
        selection_window = tk.Toplevel(self.root)
        selection_window.title("Seleccionar ubicación para la base de datos")
        selection_window.geometry("500x300")

        tk.Label(selection_window,
                 text="No se pudo acceder a la ubicación en red.\nSeleccione donde desea guardar la base de datos:",
                 font=('Arial', 10)).pack(pady=10)

        # Variable para la selección
        selected_location = tk.IntVar(value=1)  # Por defecto selecciona la segunda opción

        # Crear radio buttons para cada opción
        for idx, option in enumerate(self.location_options[1:], start=1):
            frame = tk.Frame(selection_window)
            frame.pack(fill='x', padx=10, pady=5)

            tk.Radiobutton(
                frame,
                variable=selected_location,
                value=idx,
                text=option['name']
            ).pack(side='left', anchor='w')

            tk.Label(
                frame,
                text=option['description'],
                font=('Arial', 8),
                fg='gray'
            ).pack(side='left', padx=20)

        # Botón de confirmación
        def on_confirm():
            selected_idx = selected_location.get()
            selected_path = self.location_options[selected_idx]['path']

            if self.try_create_db(selected_path):
                messagebox.showinfo("Éxito", f"Base de datos creada en:\n{selected_path}")
                selection_window.destroy()
            else:
                messagebox.showerror("Error", "No se pudo crear la base de datos en la ubicación seleccionada.")

        tk.Button(
            selection_window,
            text="Confirmar",
            command=on_confirm
        ).pack(pady=10)

    # En sql/db.py, modificar el método create_database:
    def create_database(self, db_path):
        """Crea la estructura de la base de datos"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Crear tabla usuarios (sin cambios)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    fecha_registro TEXT NOT NULL,
                    usuario_registra TEXT NOT NULL,
                    estatus TEXT DEFAULT 'Activo'
                )
            ''')

            # Crear tabla lugares (sin cambios)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lugares (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    fecha_registro TEXT NOT NULL,
                    usuario_registra TEXT NOT NULL
                )
            ''')

            # Modificar tabla acuerdos para agregar estatus
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

            # Crear tabla para el historial de modificaciones
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
        """Devuelve la fecha y hora actual"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def agregar_usuario(self, nombre):
        """Agrega un nuevo usuario a la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (nombre, fecha_registro, usuario_registra) VALUES (?, ?, ?)",
                (nombre, self.get_current_timestamp(), self.current_user)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error al agregar usuario: {e}")
            return False

    def agregar_lugar(self, nombre):
        """Agrega un nuevo lugar a la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO lugares (nombre, fecha_registro, usuario_registra) VALUES (?, ?, ?)",
                (nombre, self.get_current_timestamp(), self.current_user)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error al agregar lugar: {e}")
            return False

    def agregar_acuerdo(self, id_acuerdo, acuerdo, responsables, fecha_compromiso):
        """Agrega un nuevo acuerdo a la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO acuerdos (id_acuerdo, acuerdo, responsables, fecha_compromiso, fecha_registro, usuario_registra) VALUES (?, ?, ?, ?, ?, ?)",
                (id_acuerdo, acuerdo, responsables, fecha_compromiso, self.get_current_timestamp(), self.current_user)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error al agregar acuerdo: {e}")
            return False


def db_create():
    root = tk.Tk()
    root.withdraw()  # Ocultamos la ventana principal

    # Crear instancia de la base de datos
    minutas = MinutasDB(root)

    # Cerrar la ventana de tkinter
    root.destroy()

    return global_db_path