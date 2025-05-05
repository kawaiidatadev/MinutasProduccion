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
            respuesta = True

            if respuesta:
                usuario_actual = "Master"
            else:
                return

        def on_close(event=None):
            """Cerrar la ventana cuando se intenta cerrar o se pierde el foco"""
            if host_window.winfo_exists():  # Evitar errores si ya fue destruida
                host_window.destroy()

        # Crear ventana principal
        host_window = tk.Tk()
        host_window.title("Administración de Host")
        host_window.protocol("WM_DELETE_WINDOW", on_close)  # Al cerrar con la X

        move_to_largest_monitor(host_window)
        # Maximizar la ventana según el sistema operativo
        if sys.platform == 'win32':
            host_window.state('zoomed')  # Para Windows

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

        move_to_largest_monitor(host_window)

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


        # Botones de acción
        ttk.Button(btn_frame, text="Aprobar", command=aprobar_solicitud).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Rechazar", command=rechazar_solicitud).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Actualizar", command=cargar_solicitudes).grid(row=0, column=2, padx=5)

        # Pestaña 2: Mis Hosts
        hosts_frame = ttk.Frame(notebook)
        notebook.add(hosts_frame, text="Mis Hosts")

        # Treeview para hosts del usuario
        hosts_tree = ttk.Treeview(hosts_frame, columns=('db_name', 'fecha_acceso', 'objetivo', 'asuntos', 'direccion'),
                                  show='headings')
        hosts_tree.heading('db_name', text="Base de Datos", anchor=tk.W)
        hosts_tree.heading('fecha_acceso', text="Último Acceso", anchor=tk.W)
        hosts_tree.heading('objetivo', text="Objetivo", anchor=tk.W)
        hosts_tree.heading('asuntos', text="Asuntos", anchor=tk.W)

        # Configurar columnas
        hosts_tree.column('db_name', width=200)
        hosts_tree.column('fecha_acceso', width=150)
        hosts_tree.column('objetivo', width=400)
        hosts_tree.column('asuntos', width=500)
        hosts_tree.column('direccion', width=0, stretch=False)  # Columna oculta

        hosts_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Menú contextual para hosts
        menu_hosts = tk.Menu(hosts_tree, tearoff=0)
        menu_hosts.add_command(label="Eliminar", command=lambda: eliminar_host())

        def mostrar_menu_hosts(event):
            """Muestra el menú contextual al hacer clic derecho"""
            item = hosts_tree.identify_row(event.y)
            if item:
                hosts_tree.selection_set(item)
                menu_hosts.post(event.x_root, event.y_root)

        hosts_tree.bind("<Button-3>", mostrar_menu_hosts)

        # En la función eliminar_host() actualiza la consulta SQL:
        def eliminar_host():
            """Elimina el host seleccionado después de confirmación"""
            item_seleccionado = hosts_tree.selection()
            if not item_seleccionado:
                return

            datos_host = hosts_tree.item(item_seleccionado)['values']
            db_name = datos_host[0]

            respuesta = messagebox.askyesno(
                "Confirmar eliminación",
                f"¿Estás seguro que deseas marcar como eliminada la base de datos:\n\n{db_name}?",
                parent=hosts_frame
            )

            if respuesta:
                try:
                    # Ejecutar con parámetros seguros
                    cursor.execute("""
                        UPDATE dbs
                        SET estatus = 'Eliminada'
                        WHERE db_name COLLATE NOCASE = ?
                        AND usuario_windows COLLATE NOCASE = ?

                    """, (db_name, usuario_actual))

                    conn.commit()

                    if cursor.rowcount > 0:
                        messagebox.showinfo("Éxito",
                                            f"La base de datos {db_name} ha sido marcada como eliminada.",
                                            parent=hosts_frame
                                            )
                        cargar_hosts()
                    else:
                        messagebox.showwarning(
                            "No se pudo eliminar",
                            "No se encontró la base de datos o no cumple con los requisitos para eliminación.\n\n"
                            "Posibles causas:\n"
                            "- La base está actualmente Activa\n"
                            "- No eres el propietario registrado\n"
                            "- Ya fue eliminada previamente",
                            parent=hosts_frame
                        )
                except Exception as e:
                    messagebox.showerror(
                        "Error",
                        f"Error al eliminar:\n{str(e)}",
                        parent=hosts_frame
                    )

        def conectar_otro_host():
            """Conectar al host seleccionado en Otros Hosts"""
            seleccion = otros_hosts_tree.selection()
            if seleccion:
                direccion = otros_hosts_tree.item(seleccion[0])['values'][5]
                messagebox.showinfo("Conectar", f"Conectando a: {direccion}", parent=otros_hosts_frame)
                print(f'Aqui es host Externo: {direccion}')
                from test_consulta_ordenada import registrar_ingreso
                registrar_ingreso(direccion, MASTER, usuario_actual, 3)

        def conectar_host():
            """Conectar al host seleccionado"""
            seleccion = hosts_tree.selection()
            if seleccion:

                db_name = hosts_tree.item(seleccion[0])['values'][0]

                # Consultar la dirección completa desde la base de datos
                cursor.execute("""
                    SELECT direccion 
                    FROM dbs 
                    WHERE db_name = ? 
                    AND usuario_windows = ?
                """, (db_name, usuario_actual))

                resultado = cursor.fetchone()
                if resultado:
                    direccion = resultado[0]
                    messagebox.showinfo("Conectar", f"Conectando a: {direccion}", parent=hosts_frame)
                    print(f'Aqui es host personal: {direccion}')
                    from test_consulta_ordenada import registrar_ingreso
                    registrar_ingreso(direccion, MASTER, usuario_actual, 3)
                else:
                    messagebox.showerror("Error", "No se pudo encontrar la dirección de la base de datos",
                                         parent=hosts_frame)

        def cargar_hosts():
            """Cargar los hosts del usuario"""
            hosts_tree.delete(*hosts_tree.get_children())
            cursor.execute("""
                SELECT db_name, fecha_de_ultimo_acceso, objetivo, asuntos, direccion
                FROM dbs
                WHERE usuario_windows = ? AND estatus == 'Activa'
                ORDER BY fecha_de_ultimo_acceso DESC
            """, (usuario_actual,))

            for host in cursor.fetchall():
                # Insertamos todos los valores pero solo mostramos los primeros 4
                hosts_tree.insert('', tk.END, values=host[:4] + ('',) + host[4:])




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

        # Pestaña 4: Otros Host
        # Pestaña 4: Otros Host
        otros_hosts_frame = ttk.Frame(notebook)
        notebook.add(otros_hosts_frame, text="Otros Host")

        # Treeview para otros hosts con columna adicional para el estado
        otros_hosts_tree = ttk.Treeview(
            otros_hosts_frame,
            columns=('db_name', 'usuario_windows', 'objetivo', 'asuntos', 'fecha_creacion', 'direccion', 'estado'),
            show='headings'
        )

        # Configurar encabezados
        otros_hosts_tree.heading('db_name', text="Base de Datos", anchor=tk.W)
        otros_hosts_tree.heading('usuario_windows', text="Propietario", anchor=tk.W)
        otros_hosts_tree.heading('objetivo', text="Objetivo", anchor=tk.W)
        otros_hosts_tree.heading('asuntos', text="Asuntos", anchor=tk.W)
        otros_hosts_tree.heading('fecha_creacion', text="Fecha Creación", anchor=tk.W)
        otros_hosts_tree.heading('estado', text="Estado", anchor=tk.W)

        # Ocultar columna de dirección
        otros_hosts_tree.column('direccion', width=0, stretch=False)

        # Configurar columnas visibles
        otros_hosts_tree.column('db_name', width=200)
        otros_hosts_tree.column('usuario_windows', width=150)
        otros_hosts_tree.column('objetivo', width=300)
        otros_hosts_tree.column('asuntos', width=400)
        otros_hosts_tree.column('fecha_creacion', width=150)
        otros_hosts_tree.column('estado', width=120)

        # Configurar estilos para diferentes estados
        otros_hosts_tree.tag_configure('pendiente', foreground='orange')
        otros_hosts_tree.tag_configure('aprobado', foreground='green')
        otros_hosts_tree.tag_configure('rechazado', foreground='red')
        otros_hosts_tree.tag_configure('disponible', foreground='blue')

        otros_hosts_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Botón de solicitar permiso
        btn_solicitar = ttk.Button(otros_hosts_frame, text="Solicitar permiso", state=tk.DISABLED)
        btn_solicitar.pack(pady=10)

        # Botón para ver dirección
        btn_ver_direccion = ttk.Button(
            otros_hosts_frame,
            text="Conectar",
            state=tk.DISABLED,
            command=conectar_otro_host
        )
        btn_ver_direccion.pack(pady=10)

        def cargar_otros_hosts():
            """Cargar otros hosts disponibles con su estado actual"""
            otros_hosts_tree.delete(*otros_hosts_tree.get_children())

            cursor.execute("""
                SELECT 
                    d.db_name, 
                    d.usuario_windows, 
                    d.objetivo, 
                    d.asuntos, 
                    d.fecha_creacion,
                    d.direccion, 
                    d.id,
                    CASE 
                        WHEN EXISTS (
                            SELECT 1 FROM solicitudes_acceso 
                            WHERE db_id = d.id 
                            AND usuario_solicitante = ? 
                            AND estatus = 'pendiente'
                        ) THEN 'pendiente'
                        WHEN EXISTS (
                            SELECT 1 FROM solicitudes_acceso 
                            WHERE db_id = d.id 
                            AND usuario_solicitante = ? 
                            AND estatus = 'aprobado'
                        ) THEN 'aprobado'
                        WHEN EXISTS (
                            SELECT 1 FROM solicitudes_acceso 
                            WHERE db_id = d.id 
                            AND usuario_solicitante = ? 
                            AND estatus = 'rechazado'
                        ) THEN 'rechazado'
                        ELSE 'disponible'
                    END as estado
                FROM dbs d
                WHERE d.estatus = 'Activa' 
                AND usuario_windows != 'Master'
                AND d.usuario_windows COLLATE NOCASE != ?
            """, (usuario_actual, usuario_actual, usuario_actual, usuario_actual))

            for db in cursor.fetchall():
                db_id = db[6]
                estado = db[7].lower()  # Convertir a minúsculas para los tags

                # Mostrar estado con formato
                estado_mostrar = {
                    'pendiente': '🟠 Pendiente',
                    'aprobado': '🟢 Aprobado',
                    'rechazado': '🔴 Rechazado',
                    'disponible': '🔵 Disponible'
                }.get(estado, estado)

                # Valores a mostrar (excluyendo el ID)
                valores_mostrar = (db[0], db[1], db[2], db[3], db[4], db[5], estado_mostrar)

                otros_hosts_tree.insert(
                    '', tk.END,
                    values=valores_mostrar,
                    iid=db_id,
                    tags=(estado,)
                )

        def ver_direccion(tree):
            """Mostrar la dirección del host seleccionado"""
            seleccion = tree.selection()
            if not seleccion:
                return

            item = seleccion[0]
            direccion = tree.item(item, "values")[5]  # Índice 5 corresponde a dirección
            messagebox.showinfo("Dirección", f"Dirección del host:\n{direccion}", parent=otros_hosts_frame)


        def on_select_otros_hosts(event):
            """Manejar selección de filas"""
            seleccion = otros_hosts_tree.selection()
            btn_solicitar.config(state=tk.DISABLED)
            btn_ver_direccion.config(state=tk.DISABLED)

            if seleccion:
                item = seleccion[0]
                estado = otros_hosts_tree.item(item, 'tags')[0]  # Obtener el tag de estado

                if estado == 'aprobado':
                    btn_ver_direccion.config(state=tk.NORMAL)
                elif estado in ['disponible', 'rechazado']:
                    btn_solicitar.config(state=tk.NORMAL)
                else:
                    otros_hosts_tree.selection_remove(item)
                    if estado == 'pendiente':
                        messagebox.showinfo("Información",
                                            "Ya tiene una solicitud pendiente para esta base de datos",
                                            parent=otros_hosts_frame)
                    elif estado == 'aprobado':
                        messagebox.showinfo("Información",
                                            "Ya tiene acceso aprobado a esta base de datos",
                                            parent=otros_hosts_frame)

        import getpass  # Asegúrate de importar esto al inicio del archivo si no lo tienes ya

        def solicitar_acceso():
            """Crear solicitud de acceso"""
            seleccion = otros_hosts_tree.selection()
            if not seleccion:
                return

            db_id = seleccion[0]
            db_name = otros_hosts_tree.item(seleccion[0], 'values')[0]

            try:
                solicitante = usuario_actual
                if solicitante.lower() == "master":
                    solicitante = getpass.getuser()  # Obtener usuario de Windows si es "Master"

                # Insertar nueva solicitud
                cursor.execute("""
                    INSERT INTO solicitudes_acceso 
                    (db_id, usuario_solicitante, fecha_solicitud, estatus)
                    VALUES (?, ?, ?, 'pendiente')
                """, (db_id, solicitante, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

                conn.commit()
                messagebox.showinfo("Éxito",
                                    f"Solicitud enviada para: {db_name}",
                                    parent=otros_hosts_frame)

                # Actualizar la vista
                cargar_otros_hosts()
                btn_solicitar.config(state=tk.DISABLED)

            except sqlite3.IntegrityError:
                messagebox.showwarning("Advertencia",
                                       "Ya existe una solicitud para esta base de datos",
                                       parent=otros_hosts_frame)
            except Exception as e:
                messagebox.showerror("Error",
                                     f"Error al enviar solicitud:\n{str(e)}",
                                     parent=otros_hosts_frame)

        # Configurar eventos
        btn_solicitar.config(command=solicitar_acceso)
        otros_hosts_tree.bind('<<TreeviewSelect>>', on_select_otros_hosts)

        # Cargar datos iniciales
        cargar_otros_hosts()


        # Configurar eventos
        btn_solicitar.config(command=solicitar_acceso)
        otros_hosts_tree.bind('<<TreeviewSelect>>', on_select_otros_hosts)

        # Cargar datos iniciales
        cargar_otros_hosts()

        def cargar_hosts_compartidos():
            """Cargar los hosts compartidos"""
            compartidos_tree.delete(*compartidos_tree.get_children())
            cursor.execute("""
                       SELECT d.db_name, s.usuario_solicitante, s.fecha_respuesta
                       FROM solicitudes_acceso s
                       JOIN dbs d ON s.db_id = d.id
                       WHERE s.estatus = 'aprobado'
                       AND d.usuario_windows = ?
                       AND d.estatus = 'Activa'
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


        # Vincular evento de clic derecho
        compartidos_tree.bind("<Button-3>", mostrar_menu_contextual)

        # Cargar datos de hosts compartidos
        cargar_hosts_compartidos()

        # Cargar datos iniciales
        cargar_solicitudes()
        cargar_hosts()
        cargar_hosts_compartidos()  # Nueva línea
        move_to_largest_monitor(host_window)
        # Iniciar el bucle principal de la GUI
        host_window.mainloop()  # ¡Añadir esta línea!

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
                            FROM solicitudes_acceso s
                            JOIN dbs d ON s.db_id = d.id
                            WHERE s.estatus = 'pendiente'
                            AND d.usuario_windows = ?
                        """, (usuario_actual,))

                return cursor.fetchone()[0]
        return 0
    except Exception as e:
        print(f"Error obteniendo solicitudes pendientes: {str(e)}")
        return 0
    finally:
        if conn:  # Cerrar la conexión si existe
            conn.close()