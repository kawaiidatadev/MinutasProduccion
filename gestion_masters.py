# gestion_masters.py
from common import *
from rutas import MASTER
from acuerdos.ventana_names import move_to_largest_monitor
from tkinter import Menu

def host(db_path):
    """Función principal para gestionar hosts y solicitudes"""
    try:
        usuario_actual = os.getlogin()
        conn = sqlite3.connect(MASTER)
        cursor = conn.cursor()

        # Verificar si es propietario de alguna base de datos
        cursor.execute("SELECT COUNT(*) FROM dbs WHERE usuario_windows = ?", (usuario_actual,))
        if cursor.fetchone()[0] == 0:
            # Si no es propietario, usar la base de datos "Master" para pruebas
            respuesta = messagebox.askyesno("Información",
                                            "No eres propietario de ninguna base de datos registrada.\n"
                                            "¿Deseas usar la base de datos de prueba 'Master'?")

            if respuesta:
                usuario_actual = "Master"
            else:
                return

        # Crear ventana principal
        host_window = tk.Tk()
        host_window.title("Administración de Host")
        move_to_largest_monitor(host_window)

        # Crear notebook (pestañas)
        notebook = ttk.Notebook(host_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Pestaña 1: Gestión de solicitudes
        solicitudes_frame = ttk.Frame(notebook)
        notebook.add(solicitudes_frame, text="Gestión de Solicitudes")

        # Treeview para solicitudes pendientes
        solicitudes_tree = ttk.Treeview(solicitudes_frame, columns=('id', 'solicitante', 'db_name', 'fecha'),
                                        show='headings')
        solicitudes_tree.heading('id', text="ID", anchor=tk.W)
        solicitudes_tree.heading('solicitante', text="Usuario Solicitante", anchor=tk.W)
        solicitudes_tree.heading('db_name', text="Base de Datos", anchor=tk.W)
        solicitudes_tree.heading('fecha', text="Fecha Solicitud", anchor=tk.W)

        # Configurar columnas
        solicitudes_tree.column('id', width=50, stretch=tk.NO)
        solicitudes_tree.column('solicitante', width=150)
        solicitudes_tree.column('db_name', width=200)
        solicitudes_tree.column('fecha', width=150)

        solicitudes_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame para botones
        btn_frame = ttk.Frame(solicitudes_frame)
        btn_frame.pack(pady=10)

        def cargar_solicitudes():
            """Cargar las solicitudes pendientes"""
            solicitudes_tree.delete(*solicitudes_tree.get_children())
            cursor.execute("""
                SELECT s.id, s.usuario_solicitante, d.db_name, s.fecha_solicitud
                FROM solicitudes_acceso s
                JOIN dbs d ON s.db_id = d.id
                WHERE s.estatus = 'pendiente'
                AND d.usuario_windows = ?
                AND s.usuario_solicitante != ?
                ORDER BY s.fecha_solicitud DESC
            """, (usuario_actual, usuario_actual))

            for solicitud in cursor.fetchall():
                solicitudes_tree.insert('', tk.END, values=solicitud)

        import datetime

        def aprobar_solicitud():
            """Aprobar la solicitud seleccionada"""
            seleccion = solicitudes_tree.selection()
            if seleccion:
                solicitud_id = solicitudes_tree.item(seleccion[0])['values'][0]
                fecha_respuesta = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("""
                    UPDATE solicitudes_acceso 
                    SET estatus = 'aprobado', fecha_respuesta = ? 
                    WHERE id = ?
                """, (fecha_respuesta, solicitud_id))
                conn.commit()
                cargar_solicitudes()
                messagebox.showinfo("Éxito", "Solicitud aprobada correctamente.")

        def rechazar_solicitud():
            """Rechazar la solicitud seleccionada"""
            seleccion = solicitudes_tree.selection()
            if seleccion:
                solicitud_id = solicitudes_tree.item(seleccion[0])['values'][0]
                cursor.execute("""
                    UPDATE solicitudes_acceso 
                    SET estatus = 'rechazado' 
                    WHERE id = ?
                """, (solicitud_id,))
                conn.commit()
                cargar_solicitudes()
                messagebox.showinfo("Éxito", "Solicitud rechazada correctamente.")

        # Botones de acción
        ttk.Button(btn_frame, text="Aprobar", command=aprobar_solicitud).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Rechazar", command=rechazar_solicitud).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Actualizar", command=cargar_solicitudes).grid(row=0, column=2, padx=5)

        # Pestaña 2: Mis Hosts
        hosts_frame = ttk.Frame(notebook)
        notebook.add(hosts_frame, text="Mis Hosts")

        # Treeview para hosts del usuario
        hosts_tree = ttk.Treeview(hosts_frame, columns=('db_name', 'fecha_acceso', 'objetivo', 'asuntos'), show='headings')
        hosts_tree.heading('db_name', text="Base de Datos", anchor=tk.W)
        hosts_tree.heading('fecha_acceso', text="Último Acceso", anchor=tk.W)
        hosts_tree.heading('objetivo', text="objetivo", anchor=tk.W)
        hosts_tree.heading('asuntos', text="asuntos", anchor=tk.W)

        # Configurar columnas
        hosts_tree.column('db_name', width=200)
        hosts_tree.column('fecha_acceso', width=150)
        hosts_tree.column('objetivo', width=400)
        hosts_tree.column('asuntos', width=500)

        hosts_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def cargar_hosts():
            """Cargar los hosts del usuario"""
            hosts_tree.delete(*hosts_tree.get_children())
            cursor.execute("""
                SELECT db_name, fecha_de_ultimo_acceso, objetivo, asuntos
                FROM dbs
                WHERE usuario_windows = ?
                ORDER BY fecha_de_ultimo_acceso DESC
            """, (usuario_actual,))

            for host in cursor.fetchall():
                hosts_tree.insert('', tk.END, values=host)

        def conectar_host():
            """Conectar al host seleccionado"""
            seleccion = hosts_tree.selection()
            if seleccion:
                direccion = hosts_tree.item(seleccion[0])['values'][2]
                messagebox.showinfo("Conectar", f"Conectando a: {direccion}")
                # Aquí iría la lógica real de conexión

        # Botón de conectar
        ttk.Button(hosts_frame, text="Conectar", command=conectar_host).pack(pady=10)

        # Pestaña 3: Host Compartidos
        compartidos_frame = ttk.Frame(notebook)
        notebook.add(compartidos_frame, text="Host Compartidos")

        # Treeview para hosts compartidos
        compartidos_tree = ttk.Treeview(compartidos_frame, columns=('db_name', 'usuario', 'fecha_aprobacion'),
                                        show='headings')
        compartidos_tree.heading('db_name', text="Base de Datos", anchor=tk.W)
        compartidos_tree.heading('usuario', text="Usuario", anchor=tk.W)
        compartidos_tree.heading('fecha_aprobacion', text="Fecha Aprobación", anchor=tk.W)

        # Configurar columnas
        compartidos_tree.column('db_name', width=200)
        compartidos_tree.column('usuario', width=150)
        compartidos_tree.column('fecha_aprobacion', width=150)

        compartidos_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Menú contextual para retirar permisos
        menu_contextual = Menu(compartidos_tree, tearoff=0)
        menu_contextual.add_command(label="Retirar permiso", command=lambda: retirar_permiso())

        def cargar_hosts_compartidos():
            """Cargar los hosts compartidos"""
            compartidos_tree.delete(*compartidos_tree.get_children())
            cursor.execute("""
                       SELECT d.db_name, s.usuario_solicitante, s.fecha_respuesta
                       FROM solicitudes_acceso s
                       JOIN dbs d ON s.db_id = d.id
                       WHERE s.estatus = 'aprobado'
                       AND d.usuario_windows = ?
                       ORDER BY s.fecha_respuesta DESC
                   """, (usuario_actual,))

            for registro in cursor.fetchall():
                compartidos_tree.insert('', tk.END, values=registro)

        def mostrar_menu_contextual(event):
            """Mostrar menú contextual al hacer clic derecho"""
            item = compartidos_tree.identify_row(event.y)
            if item:
                compartidos_tree.selection_set(item)
                menu_contextual.post(event.x_root, event.y_root)

        def retirar_permiso():
            """Cambiar el estatus a rechazado"""
            seleccion = compartidos_tree.selection()
            if seleccion:
                db_name = compartidos_tree.item(seleccion[0])['values'][0]
                usuario = compartidos_tree.item(seleccion[0])['values'][1]

                cursor.execute("""
                           UPDATE solicitudes_acceso 
                           SET estatus = 'rechazado' 
                           WHERE id = (
                               SELECT s.id 
                               FROM solicitudes_acceso s
                               JOIN dbs d ON s.db_id = d.id
                               WHERE d.db_name = ?
                               AND s.usuario_solicitante = ?
                               AND s.estatus = 'aprobado'
                           )
                       """, (db_name, usuario))
                conn.commit()
                cargar_hosts_compartidos()
                messagebox.showinfo("Éxito", "Permiso retirado correctamente.")

        # Vincular evento de clic derecho
        compartidos_tree.bind("<Button-3>", mostrar_menu_contextual)

        # Cargar datos de hosts compartidos
        cargar_hosts_compartidos()

        # Cargar datos iniciales
        cargar_solicitudes()
        cargar_hosts()
        cargar_hosts_compartidos()  # Nueva línea
        host_window.mainloop()

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()


def get_pending_requests_count(db_path):
    """Obtener el número de solicitudes pendientes para una base de datos específica"""
    try:
        usuario_actual = os.getlogin()
        conn = sqlite3.connect(MASTER)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, usuario_windows 
            FROM dbs 
            WHERE direccion = ?
        """, (db_path,))

        db_info = cursor.fetchone()

        if db_info:
            db_id, usuario_db = db_info[0], db_info[1]

            # Solo contar si el usuario es el propietario
            if usuario_actual.lower() == usuario_db.lower():
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM solicitudes_acceso 
                    WHERE db_id = ? 
                    AND estatus = 'pendiente'
                """, (db_id,))
                return cursor.fetchone()[0]
        return 0
    except Exception as e:
        print(f"Error obteniendo solicitudes pendientes: {str(e)}")
        return 0
    finally:
        if 'conn' in locals():
            conn.close()