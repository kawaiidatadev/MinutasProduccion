from rutas import DB_PATH
from common import *
from acuerdos.ventana_names import move_to_largest_monitor
from sql.nombre import sanitizar_nombre


class MasterDBManager:
    """Clase para manejar la conexión con la base de datos maestra"""

    def __init__(self):
        self.master_db_path = r"\\mercury\Producción\Minutas Produccion\Program Files\dbs_rutas\master.db"
        self.current_user = getpass.getuser()
        self.ensure_master_table()  # Crear tabla si no existe

    def user_exists(self):
        try:
            conn = sqlite3.connect(self.master_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM dbs WHERE usuario_windows = ? LIMIT 1", (self.current_user,))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"Error checking if user exists: {e}")
            return False
        finally:
            conn.close()

    def get_default_db(self):
        try:
            conn = sqlite3.connect(self.master_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT direccion FROM dbs WHERE db_name = 'Default' LIMIT 1")
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Error retrieving default DB: {e}")
            return None
        finally:
            conn.close()

    def ensure_master_table(self):
        """Crea la estructura de la tabla maestra si no existe"""
        try:
            conn = sqlite3.connect(self.master_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dbs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_windows TEXT NOT NULL,
                    db_name TEXT NOT NULL UNIQUE,
                    objetivo TEXT,
                    asuntos TEXT,
                    fecha_creacion DATETIME,
                    estatus TEXT DEFAULT 'Activa',
                    direccion TEXT UNIQUE,
                    fecha_de_ultimo_acceso DATETIME
                )
            """)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"Error al crear tabla maestra: {str(e)}")
            raise

    def get_most_recent_db(self):
        """Obtiene la ruta de la base de datos más reciente del usuario actual"""
        try:
            conn = sqlite3.connect(self.master_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT direccion 
                FROM dbs 
                WHERE usuario_windows = ? 
                ORDER BY fecha_de_ultimo_acceso DESC 
                LIMIT 1
            """, (self.current_user,))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Error al consultar master.db: {str(e)}")
            return None
        finally:
            conn.close()


class MinutasDB:
    def __init__(self, root=None, db_path=None, is_default=True):  # Nuevo parámetro
        self.root = root
        self.current_user = getpass.getuser()
        self.db_created = False
        self.is_default = is_default  # Nuevo atributo

        master_manager = MasterDBManager()
        # Paso 1: Verificar si el usuario actual existe en la tabla dbs
        if not master_manager.user_exists():
            # Paso 2: Obtener la DB por defecto
            default_db_path = master_manager.get_default_db()

            if default_db_path:
                self.db_path = default_db_path
                self.is_default = True  # Flag opcional para saber que se usó la default
            else:
                raise Exception("No se encontró la base de datos predeterminada 'Default'.")
        else:
            # El usuario existe, obtener su DB más reciente
            most_recent_db = master_manager.get_most_recent_db()

            if most_recent_db:
                self.db_path = most_recent_db
                self.is_default = False
            else:
                # Usuario existe pero no tiene DBs aún. Se genera una nueva.
                default_dir = fr"\\mercury\Producción\Minutas Produccion\Program Files\{self.current_user}"
                self.db_path = self.generate_unique_db_path(default_dir)
                self.is_default = False


        if not self.try_create_db():
            error_msg = f"No se pudo crear/acceder a la base de datos en:\n{self.db_path}"
            if self.root:
                messagebox.showerror("Error", error_msg)
            else:
                print(error_msg)
            raise Exception(error_msg)

    def generate_unique_db_path(self, directory):
        """Genera una ruta única para la base de datos"""
        base_name = "minuta_principal"
        counter = 1
        while True:
            new_name = f"{base_name}_{datetime.now().strftime('%Y%m%d')}_{counter}.db"
            full_path = os.path.join(directory, new_name)
            if not os.path.exists(full_path):
                return full_path
            counter += 1

    def try_create_db(self):
        """Intenta crear/verificar la base de datos en la ubicación especificada"""
        try:
            db_dir = os.path.dirname(self.db_path)

            # Crear directorio si no existe
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            # Verificar permisos de escritura
            if not os.access(db_dir, os.W_OK):
                raise PermissionError(f"No hay permisos de escritura en: {db_dir}")

            # Crear DB si no existe
            if not os.path.exists(self.db_path):
                self.create_database()

            # Verificar integridad de la DB
            with sqlite3.connect(self.db_path) as test_conn:
                test_conn.execute("SELECT name FROM sqlite_master WHERE type='table';")

            return True

        except Exception as e:
            print(f"Error en try_create_db: {str(e)}")
            return False

    def create_database(self):
        """Crea la estructura de la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            from sql.querys import tabla_acuerdos, historial_acuerdos, usuarios
            cursor.execute(tabla_acuerdos)
            cursor.execute(historial_acuerdos)
            cursor.execute(usuarios)
            conn.commit()
            conn.close()
            if self.is_default:
                self.update_master_db()

        except sqlite3.Error as e:
            raise Exception(f"Error al crear la base de datos: {e}")

    def update_master_db(self):
        """Actualiza o inserta la entrada en master.db"""
        try:
            if not self.is_default:
                return  # No registrar si no es default
            master_manager = MasterDBManager()
            conn = sqlite3.connect(master_manager.master_db_path)
            cursor = conn.cursor()

            # Verificar si ya existe el registro
            cursor.execute("SELECT id FROM dbs WHERE direccion = ?", (self.db_path,))
            exists = cursor.fetchone()

            if exists:
                update_query = """
                UPDATE dbs 
                SET fecha_de_ultimo_acceso = datetime('now') 
                WHERE direccion = ?
                """
                cursor.execute(update_query, (self.db_path,))
            else:
                insert_query = """
                INSERT INTO dbs (
                    usuario_windows, 
                    db_name, 
                    objetivo, 
                    asuntos, 
                    fecha_creacion, 
                    estatus, 
                    direccion, 
                    fecha_de_ultimo_acceso
                ) VALUES (?, ?, ?, ?, datetime('now'), ?, ?, datetime('now'))
                """
                db_name = os.path.basename(self.db_path)
                cursor.execute(insert_query, (
                    self.current_user,
                    db_name,
                    "Minuta principal",
                    "Seguimiento de acuerdos generales",
                    "Activa",
                    self.db_path
                ))

            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"Error al actualizar/insertar en master.db: {str(e)}")
            raise

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


def mostrar_mensaje_temporal(mensaje, duracion=1000):  # Duración en milisegundos (1000 ms = 1 segundo)
    ventana_mensaje = tk.Toplevel()
    ventana_mensaje.title("Información")
    ventana_mensaje.geometry("300x100")  # Tamaño fijo
    ventana_mensaje.resizable(False, False)  # No se puede redimensionar
    ventana_mensaje.transient()  # Se coloca encima de la ventana principal
    ventana_mensaje.attributes('-topmost', True)  # Siempre arriba
    ventana_mensaje.overrideredirect(True)  # Quita los botones de cerrar/minimizar/mover
    move_to_largest_monitor(ventana_mensaje)

    label = tk.Label(ventana_mensaje, text=mensaje, font=("Arial", 12))
    label.pack(expand=True, fill="both")

    # Cerrar la ventana después de la duración especificada
    ventana_mensaje.after(duracion, ventana_mensaje.destroy)


def crear_nueva_minuta():
    """Interfaz moderna para crear nueva minuta"""
    ventana = tk.Toplevel()
    ventana.title("Nueva Minuta")
    ventana.configure(bg='#f5f5f5')
    move_to_largest_monitor(ventana)


    # Primero definimos todas las funciones internas
    def actualizar_ui(event=None):
        """Actualiza la interfaz en tiempo real"""
        for entry, help_text, counter, max_len in entries:
            texto = entry.get()
            length = len(texto)

            # Actualizar contador
            counter.config(text=f"{length}/{max_len}",
                         fg='#e74c3c' if length > max_len else '#999999')

            # Cambiar color del borde si hay error
            entry.config(highlightcolor='#e74c3c' if length > max_len else '#3498db')

            # Ocultar placeholder si hay texto
            help_text.config(fg='#ffffff' if texto else '#999999')

    def validar_campos():
        """Valida todos los campos del formulario"""
        errors = []
        nombre = entries[0][0].get().strip()
        objetivo = entries[1][0].get().strip()
        asuntos = entries[2][0].get().strip()

        if not nombre:
            errors.append("El nombre de la minuta es obligatorio")
        if len(nombre) > 30:
            errors.append("El nombre no puede exceder 30 caracteres")
        if len(objetivo) > 50:
            errors.append("El objetivo no puede exceder 50 caracteres")
        if len(asuntos) > 50:
            errors.append("Los asuntos no pueden exceder 50 caracteres")

        if errors:
            messagebox.showerror("Errores en el formulario", "\n".join(errors))
            return False
        return True

    def registrar_nueva_db_en_master(ruta, nombre, objetivo, asuntos):
        """Registra en la base de datos maestra"""
        try:
            master_manager = MasterDBManager()
            conn = sqlite3.connect(master_manager.master_db_path)
            cursor = conn.cursor()

            insert_query = """
            INSERT INTO dbs (
                usuario_windows, db_name, objetivo, asuntos, 
                fecha_creacion, estatus, direccion, fecha_de_ultimo_acceso
            ) VALUES (?, ?, ?, ?, datetime('now'), ?, ?, datetime('now'))
            """

            cursor.execute(insert_query, (
                master_manager.current_user,
                nombre,
                objetivo,
                asuntos,
                "Activa",
                ruta
            ))

            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            print(f"Error al registrar en master.db: {str(e)}")

    def crear_minuta():
        """Procesa la creación de la minuta"""
        if not validar_campos():
            return

        nombre_minuta = sanitizar_nombre(entries[0][0].get())
        objetivo = entries[1][0].get().strip()
        asuntos = entries[2][0].get().strip()

        usuario = getpass.getuser()
        directorio_base = fr"\\mercury\Producción\Minutas Produccion\Program Files\{usuario}"

        try:
            os.makedirs(directorio_base, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo crear el directorio:\n{str(e)}")
            return

        if not nombre_minuta.lower().endswith('.db'):
            nombre_minuta += ".db"

        ruta_completa = os.path.join(directorio_base, nombre_minuta)

        if os.path.exists(ruta_completa):
            mostrar_mensaje_temporal("Ya existe una minuta con ese nombre.\nPor favor use un nombre diferente.", 2000)
            return

        try:

            MinutasDB(db_path=ruta_completa)
            registrar_nueva_db_en_master(ruta_completa, nombre_minuta, objetivo, asuntos)
            mostrar_mensaje_temporal("Se creó la minuta", 1500)  # 1000 ms = 1 segundo
            ventana.destroy()


        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la minuta:\n{str(e)}")

    # Ahora creamos la interfaz gráfica
    # Frame principal con padding consistente
    main_frame = tk.Frame(ventana, bg='#ffffff', padx=30, pady=25)
    main_frame.pack(expand=True, fill=tk.BOTH)

    # Título centrado con espacio adecuado
    tk.Label(main_frame, text="Crear Nueva Minuta",
            font=('Helvetica', 16, 'bold'), bg='#ffffff', fg='#333333'
            ).pack(pady=(0, 25))

    # Frame para los campos del formulario
    form_frame = tk.Frame(main_frame, bg='#ffffff')
    form_frame.pack(fill=tk.X, padx=10)

    # Estilos reutilizables
    campo_style = {
        'font': ('Helvetica', 10),
        'bg': '#ffffff',
        'bd': 1,
        'relief': tk.SOLID,
        'highlightthickness': 1,
        'highlightcolor': '#3498db',
        'highlightbackground': '#dddddd'
    }
    label_style = {
        'font': ('Helvetica', 10, 'bold'),
        'bg': '#ffffff',
        'fg': '#555555'
    }
    help_style = {
        'font': ('Helvetica', 8),
        'bg': '#ffffff',
        'fg': '#999999'
    }

    # Campos del formulario
    campos = [
        ("Nombre de la minuta", 30, "Ej: Reunión Semanal - Proyecto X"),
        ("Objetivo principal", 50, "Ej: Revisar avances del sprint actual"),
        ("Asuntos a tratar", 50, "Ej: Resolución de problemas técnicos")
    ]

    entries = []
    for label, max_len, placeholder in campos:
        # Frame para cada campo
        field_frame = tk.Frame(form_frame, bg='#ffffff')
        field_frame.pack(fill=tk.X, pady=8)

        # Label
        tk.Label(field_frame, text=f"{label} (máx. {max_len} chars):",
                **label_style).pack(anchor=tk.W)

        # Entry
        entry = tk.Entry(field_frame, width=50, **campo_style)
        entry.pack(fill=tk.X, pady=2)

        # Frame para ayuda y contador
        bottom_frame = tk.Frame(field_frame, bg='#ffffff')
        bottom_frame.pack(fill=tk.X)

        # Texto de ayuda
        help_text = tk.Label(bottom_frame, text=placeholder, **help_style)
        help_text.pack(side=tk.LEFT)

        # Contador de caracteres
        counter = tk.Label(bottom_frame, text=f"0/{max_len}", **help_style)
        counter.pack(side=tk.RIGHT)

        entries.append((entry, help_text, counter, max_len))

    # Frame para el botón de acción
    button_frame = tk.Frame(main_frame, bg='#ffffff')
    button_frame.pack(fill=tk.X, pady=(20, 0), padx=10)

    # Botón de creación con estilo moderno
    btn_crear = tk.Button(
        button_frame,
        text="CREAR MINUTA",
        command=crear_minuta,
        bg='#3498db',
        fg='white',
        font=('Helvetica', 10, 'bold'),
        bd=0,
        padx=30,
        pady=8,
        cursor='hand2',
        activebackground='#2980b9'
    )
    btn_crear.pack(side=tk.RIGHT)

    # Configurar eventos
    for entry, *_ in entries:
        entry.bind('<KeyRelease>', actualizar_ui)
        entry.bind('<FocusIn>', lambda e: actualizar_ui())
        entry.bind('<FocusOut>', lambda e: actualizar_ui())
        # Agregar evento Enter para cada entry
        entry.bind('<Return>', lambda e: crear_minuta())

    ventana.mainloop()