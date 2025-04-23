import sqlite3
import os
import getpass
import re
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog
from rutas import DB_PATH


class MinutasDB:
    def __init__(self, root=None, db_path=None):
        self.root = root
        self.current_user = getpass.getuser()
        self.db_created = False
        self.db_path = db_path if db_path is not None else DB_PATH

        if not self.try_create_db():
            error_msg = f"No se pudo crear/acceder a la base de datos en:\n{self.db_path}"
            if self.root:
                messagebox.showerror("Error", error_msg)
            else:
                print(error_msg)
            raise Exception(error_msg)

    def try_create_db(self):
        """Intenta crear/verificar la base de datos en la ubicación especificada"""
        try:
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            # Verificar permisos de escritura
            test_file = os.path.join(db_dir, "test.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)

            self.create_database()
            return True
        except Exception as e:
            print(f"Error en try_create_db: {str(e)}")
            return False

    def create_database(self):
        """Crea la estructura de la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

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
    """Función original que crea/verifica la base de datos principal"""
    root = tk.Tk()
    root.withdraw()

    try:
        minutas = MinutasDB(root)
        root.destroy()
        return minutas.db_path
    except Exception as e:
        root.destroy()
        return str(e)


def sanitizar_nombre(nombre):
    """Limpia caracteres inválidos para nombres de archivo"""
    nombre = re.sub(r'[\\/*?:"<>|]', '_', nombre)
    nombre = nombre.replace(' ', '_').strip()
    return nombre[:50]


def generar_nombre_minuta(objetivo, asuntos, responsables):
    """Genera un nombre de archivo único basado en el contenido"""

    def procesar_campo(texto, max_palabras=3, max_caracteres=15):
        palabras = texto.split()[:max_palabras]
        return ''.join([p[:3] for p in palabras])[:max_caracteres]

    objetivo_limpio = procesar_campo(objetivo) or "Obj"
    asuntos_limpio = procesar_campo(asuntos) or "Asuntos"
    responsables_limpio = procesar_campo(responsables) or "Responsables"

    nombre_base = f"{sanitizar_nombre(objetivo_limpio)}_{sanitizar_nombre(asuntos_limpio)}_{sanitizar_nombre(responsables_limpio)}"
    return nombre_base + ".db"


def crear_nueva_minuta():
    """Interfaz para crear nueva minuta con campos personalizados"""
    ventana = tk.Toplevel()
    ventana.title("Nueva Minuta de Producción")
    ventana.geometry("600x300")

    # Configuración de grid
    ventana.columnconfigure(1, weight=1)
    pad_options = {'padx': 5, 'pady': 5, 'sticky': tk.EW}

    # Campos del formulario
    tk.Label(ventana, text="Objetivo de la reunión:").grid(row=0, column=0, **pad_options)
    objetivo_entry = tk.Entry(ventana, width=60)
    objetivo_entry.grid(row=0, column=1, **pad_options)

    tk.Label(ventana, text="Asuntos principales a tratar:").grid(row=1, column=0, **pad_options)
    asuntos_entry = tk.Entry(ventana, width=60)
    asuntos_entry.grid(row=1, column=1, **pad_options)

    tk.Label(ventana, text="Responsable(s) general(es):").grid(row=2, column=0, **pad_options)
    responsables_entry = tk.Entry(ventana, width=60)
    responsables_entry.grid(row=2, column=1, **pad_options)

    def crear_minuta():
        # Validar campos obligatorios
        if not all([objetivo_entry.get(), asuntos_entry.get(), responsables_entry.get()]):
            messagebox.showerror("Error", "Todos los campos son obligatorios")
            return

        # Generar estructura de directorios
        usuario = getpass.getuser()
        directorio_base = fr"\\mercury\Producción\Minutas Produccion\Program Files\{usuario}"

        try:
            os.makedirs(directorio_base, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo crear el directorio: {str(e)}")
            return

        # Generar nombre de archivo único
        nombre_db = generar_nombre_minuta(
            objetivo_entry.get(),
            asuntos_entry.get(),
            responsables_entry.get()
        )

        # Verificar y hacer único el nombre
        contador = 1
        nombre_base, extension = os.path.splitext(nombre_db)
        ruta_completa = os.path.join(directorio_base, nombre_db)
        while os.path.exists(ruta_completa):
            nombre_db = f"{nombre_base}_{contador}{extension}"
            ruta_completa = os.path.join(directorio_base, nombre_db)
            contador += 1

        # Crear la base de datos
        try:
            MinutasDB(db_path=ruta_completa)
            messagebox.showinfo("Éxito", f"Minuta creada exitosamente en:\n{ruta_completa}")
            ventana.destroy()
            return ruta_completa
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la minuta: {str(e)}")
            return None

    # Botón de acción
    btn_crear = tk.Button(ventana, text="Crear Minuta", command=crear_minuta, bg="#4CAF50", fg="white")
    btn_crear.grid(row=3, column=1, **pad_options)

    ventana.mainloop()