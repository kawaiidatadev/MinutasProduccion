from common import *
from acuerdos.cerrar_2 import cerrar_acuerdo_seleccionado
from acuerdos.children_window import center_child_window
from acuerdos.editar_comentarios_date import edit_commitment_date
from acuerdos.guardar_responsables import save_responsables
from acuerdos.limpiar_filtros import clear_filters
from audio import texto_a_voz, play_audio_async

def word_acuerdos(root, db_path):
    """Muestra una ventana con el historial de acuerdos y permite su edición"""
    # Crear ventana principal
    window = tk.Toplevel(root)
    window.title("Gestión de Acuerdos")
    window.geometry("1300x700")  # Ventana más grande
    window.configure(bg='#f0f0f0')
    print("Ocultando root 1")
    root.withdraw()

    def maximize_window():
        if sys.platform == 'win32':
            window.state('zoomed')  # Para Windows


    # Maximizar inmediatamente después de crear la ventana
    window.after(100, maximize_window)

    # Configurar para que se maximice cada vez que gana el foco
    window.bind('<FocusIn>', lambda e: maximize_window())

    # Función que se ejecuta al cerrar la ventana
    def on_closing():
        window.destroy()  # Cerrar la ventana secundaria
        root.deiconify()  # Mostrar la ventana principal nuevamente

    # Configurar el protocolo de cierre
    window.protocol("WM_DELETE_WINDOW", on_closing)

    # Definir colores para resaltar cambios
    color_added = '#e6ffe6'  # Verde claro para adiciones
    color_removed = '#ffe6e6'  # Rojo claro para eliminaciones
    color_changed = '#ffffe6'  # Amarillo claro para cambios

    # Estilo para los frames
    style = ttk.Style()
    style.configure('Custom.TFrame', background='#f0f0f0')
    style.configure('Treeview', rowheight=30)  # Altura de fila mayor para múltiples líneas

    # Frame para filtros
    filter_frame = ttk.Frame(window, padding=(10, 10, 10, 10), style='Custom.TFrame')
    filter_frame.pack(fill="x")

    # Filtro por ID de acuerdo
    ttk.Label(filter_frame, text="ID Acuerdo:", background='#f0f0f0').grid(row=0, column=0, sticky="w")
    id_filter = ttk.Entry(filter_frame, width=15)
    id_filter.grid(row=0, column=1, sticky="w", padx=5)

    # Filtro por texto en acuerdo
    ttk.Label(filter_frame, text="Texto en acuerdo:", background='#f0f0f0').grid(row=0, column=2, sticky="w")
    text_filter = ttk.Entry(filter_frame, width=30)
    text_filter.grid(row=0, column=3, sticky="w", padx=5)

    # Filtro por responsable
    ttk.Label(filter_frame, text="Responsable:", background='#f0f0f0').grid(row=0, column=4, sticky="w")
    resp_filter = ttk.Entry(filter_frame, width=20)
    resp_filter.grid(row=0, column=5, sticky="w", padx=5)

    from tkcalendar import DateEntry

    # Crear DateEntry vacío para fecha inicial
    date_from = DateEntry(
        filter_frame,
        width=12,
        background='darkblue',
        foreground='white',
        borderwidth=2,
        date_pattern='yyyy-mm-dd',
        textvariable=tk.StringVar()  # Esto fuerza un campo vacío
    )
    date_from.grid(row=1, column=1, sticky="w", padx=5)
    date_from.delete(0, 'end')  # Asegura que esté vacío

    # Crear DateEntry vacío para fecha final
    date_to = DateEntry(
        filter_frame,
        width=12,
        background='darkblue',
        foreground='white',
        borderwidth=2,
        date_pattern='yyyy-mm-dd',
        textvariable=tk.StringVar()  # Esto fuerza un campo vacío
    )
    date_to.grid(row=1, column=3, sticky="w", padx=5)
    date_to.delete(0, 'end')  # Asegura que esté vacío

    # Filtro por estatus
    ttk.Label(filter_frame, text="Estatus:", background='#f0f0f0').grid(row=1, column=4, sticky="w")
    status_filter = ttk.Combobox(filter_frame, values=["Todos", "Activo", "Editado", "Cerrado"],
                                 state="readonly")
    status_filter.set("Todos")
    status_filter.grid(row=1, column=5, sticky="w", padx=5)

    # Frame para botones de filtrado (izquierda)
    filter_btn_frame = ttk.Frame(filter_frame, style='Custom.TFrame')
    filter_btn_frame.grid(row=0, column=6, rowspan=2, padx=10, sticky='w')

    # Frame para botones especiales (derecha)
    special_btn_frame = ttk.Frame(filter_frame, style='Custom.TFrame')
    special_btn_frame.grid(row=0, column=7, rowspan=2, padx=(0, 10), sticky='e')

    # Configurar estilos para botones especiales
    style.configure('Special.TButton',
                    foreground='white',
                    font=('Helvetica', 10, 'bold'),
                    padding=6,
                    borderwidth=1)

    style.map('Special.TButton',
              foreground=[('pressed', 'white'), ('active', 'white')],
              background=[('pressed', '!disabled', '#2c3e50'), ('active', '#3498db')])

    # Estilo específico para Exportar Excel (verde)
    style.configure('Export.TButton', background='#27ae60')
    style.map('Export.TButton',
              background=[('pressed', '!disabled', '#1e8449'), ('active', '#2ecc71')])

    # Estilo específico para Nuevo Acuerdo (azul)
    style.configure('New.TButton', background='#2980b9')
    style.map('New.TButton',
              background=[('pressed', '!disabled', '#1a5276'), ('active', '#3498db')])

    # Estilo específico para el botón de Play
    style.configure('Play.TButton', background='#9b59b6')
    style.map('Play.TButton',
              background=[('pressed', '!disabled', '#8e44ad'), ('active', '#af7ac5')])

    # Funciones para los botones
    from acuerdos.exp_excels import exportar_excel
    from acuerdos.nuevos_acuerdos import nuevo_acuerdo

    # Función wrapper para nuevo acuerdo
    def ejecutar_excel(event=None):
        exportar_excel(db_path)

    def ejecutar_nuevo_acuerdo(event=None):
        nuevo_acuerdo(window, db_path)

    # Función para leer el acuerdo seleccionado
    def leer_acuerdo():
        selected_item = acuerdos_tree.focus()
        if selected_item:
            # Obtener todos los valores de la fila seleccionada:
            values = acuerdos_tree.item(selected_item, 'values')
            acuerdo_text = values[1]  # Texto del acuerdo
            responsables_text = values[2]  # Nombres de responsables (separados por comas)
            fecha_compromiso = values[5]  # Fecha compromiso en formato dd/mm/aaaa

            # Procesar los responsables para unirlos con " y "
            nombres = [n.strip() for n in responsables_text.split(',')]
            responsables_natural = " y ".join(nombres)

            # Calcular los días restantes para la fecha de compromiso
            from datetime import datetime, date
            try:
                compromiso_date = datetime.strptime(fecha_compromiso, "%d/%m/%Y").date()
                today = date.today()
                diff = (compromiso_date - today).days

                if diff >= 0:
                    fecha_msg = f"y para este acuerdo faltan {diff} días para vencer"
                else:
                    fecha_msg = f"y este acuerdo venció hace {abs(diff)} días."
            except ValueError:
                # En caso de error al convertir la fecha, se omite el mensaje.
                fecha_msg = ""

            # Construir el mensaje final combinando el texto del acuerdo, los responsables y el mensaje de la fecha
            final_text = f"{acuerdo_text}. Responsables: {responsables_natural} {fecha_msg}"
            texto_a_voz(final_text)

    # Botón Exportar a Excel con estilo especial y atajo
    export_btn = ttk.Button(
        special_btn_frame,
        text="📊 Exportar Excel \n        (Ctrl+E)",
        command=ejecutar_excel,
        style='Export.TButton',
        width=22  # Aumentado para incluir el atajo
    )
    export_btn.grid(row=0, column=0, padx=5, pady=2, sticky='e')

    # Botón Nuevo Acuerdo con estilo especial y atajo
    new_btn = ttk.Button(
        special_btn_frame,
        text="➕ Nuevo Acuerdo \n         (Ctrl+N)",
        command=ejecutar_nuevo_acuerdo,
        style='New.TButton',
        width=22  # Aumentado para incluir el atajo
    )
    new_btn.grid(row=0, column=1, padx=5, pady=2, sticky='e')

    # Botón Play para leer el acuerdo (inicialmente deshabilitado)
    play_btn = ttk.Button(
        special_btn_frame,
        text="▶️ Leer Acuerdo",
        command=leer_acuerdo,
        style='Play.TButton',
        width=15,
        state='disabled'
    )
    play_btn.grid(row=0, column=2, padx=5, pady=2, sticky='e')

    # Configurar atajos de teclado
    window.bind('<Control-n>', ejecutar_nuevo_acuerdo)
    window.bind('<Control-N>', ejecutar_nuevo_acuerdo)
    window.bind('<Control-e>', ejecutar_excel)
    window.bind('<Control-E>', ejecutar_excel)

    # Función para habilitar/deshabilitar el botón de play según la selección
    def toggle_play_button(event=None):
        selected_item = acuerdos_tree.focus()
        if selected_item:
            play_btn.state(['!disabled'])
        else:
            play_btn.state(['disabled'])

    # Botones de filtrado normales
    ttk.Button(
        filter_btn_frame,
        text="Filtrar",
        command=lambda: load_acuerdos(acuerdos_tree, db_path, id_filter, text_filter,
                                      resp_filter, date_from, date_to, status_filter)
    ).grid(row=0, column=0, padx=2, pady=2)

    ttk.Button(
        filter_btn_frame,
        text="Limpiar",
        command=lambda: clear_filters(id_filter, text_filter, resp_filter, date_from,
                                      date_to, status_filter, acuerdos_tree, db_path)
    ).grid(row=0, column=1, padx=2, pady=2)

    # Treeview para acuerdos principales
    tree_frame = ttk.Frame(window, style='Custom.TFrame')
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Configurar el ancho de las columnas (actualizado con accion)
    column_widths = {
        "id": 80,
        "acuerdo": 350,  # Ajustado para dar espacio a comentarios
        "responsables": 150,  # Ajustado para dar espacio a comentarios
        "fecha": 120,
        "estatus": 80,
        "fecha_compromiso": 100,
        "comentarios": 250,
        "accion": 80
    }

    acuerdos_tree = ttk.Treeview(
        tree_frame,
        columns=("id", "acuerdo", "responsables", "fecha", "estatus", "fecha_compromiso", "comentarios", "accion"),
        show="headings",
        height=10  # Más filas visibles
    )

    # Configurar columnas
    acuerdos_tree.heading("id", text="ID Acuerdo")
    acuerdos_tree.heading("acuerdo", text="Acuerdo")
    acuerdos_tree.heading("responsables", text="Responsables")
    acuerdos_tree.heading("fecha", text="Última Modificación")
    acuerdos_tree.heading("estatus", text="Estatus")
    acuerdos_tree.heading("fecha_compromiso", text="Fecha Compromiso")
    acuerdos_tree.heading("comentarios", text="Comentarios")
    acuerdos_tree.heading("accion", text="Acción")
    acuerdos_tree.tag_configure('cerrable', foreground='black', font=('TkDefaultFont', 10))
    acuerdos_tree.tag_configure('cerrado', foreground='gray')

    # Aplicar anchos de columnas
    for col, width in column_widths.items():
        acuerdos_tree.column(col, width=width, anchor="w")  # Alineación a la izquierda

    # Scrollbar horizontal para acuerdos
    h_scroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=acuerdos_tree.xview)
    acuerdos_tree.configure(xscrollcommand=h_scroll.set)

    acuerdos_tree.pack(fill="both", expand=True)
    h_scroll.pack(fill="x", pady=(0, 10))

    # Separador
    ttk.Separator(tree_frame, orient="horizontal").pack(fill="x", pady=5)

    # Label para historial
    historial_label = ttk.Label(
        tree_frame,
        text="Historial de modificaciones:",
        font=("Helvetica", 10, "bold"),
        background='#f0f0f0'
    )
    historial_label.pack(anchor="w")

    # Treeview para historial (actualizado con comentarios)
    historial_tree = ttk.Treeview(
        tree_frame,
        columns=("fecha", "usuario", "estatus", "acuerdo", "responsables", "fecha_compromiso", "comentarios"),
        show="headings",
        height=8  # Más filas visibles
    )

    # Configurar tags para resaltado
    historial_tree.tag_configure('added', background=color_added)
    historial_tree.tag_configure('removed', background=color_removed)
    historial_tree.tag_configure('changed', background=color_changed)

    # Configurar columnas del historial
    historial_tree.heading("fecha", text="Fecha Modificación")
    historial_tree.heading("usuario", text="Usuario")
    historial_tree.heading("estatus", text="Estatus")
    historial_tree.heading("acuerdo", text="Acuerdo")
    historial_tree.heading("responsables", text="Responsables")
    historial_tree.heading("fecha_compromiso", text="Fecha Compromiso")
    historial_tree.heading("comentarios", text="Comentarios")

    # Aplicar anchos similares al treeview principal (actualizado)
    historial_tree.column("fecha", width=120, anchor="w")
    historial_tree.column("usuario", width=80, anchor="w")
    historial_tree.column("estatus", width=80, anchor="w")
    historial_tree.column("acuerdo", width=350, anchor="w")
    historial_tree.column("responsables", width=150, anchor="w")
    historial_tree.column("fecha_compromiso", width=100, anchor="w")
    historial_tree.column("comentarios", width=250, anchor="w")

    # Scrollbar horizontal para historial
    h_scroll_hist = ttk.Scrollbar(tree_frame, orient="horizontal", command=historial_tree.xview)
    historial_tree.configure(xscrollcommand=h_scroll_hist.set)

    historial_tree.pack(fill="both", expand=True)
    h_scroll_hist.pack(fill="x")

    # Configurar eventos
    acuerdos_tree.bind("<Double-1>",
                       lambda e: on_double_click(e, acuerdos_tree, historial_tree, historial_label, db_path))
    acuerdos_tree.bind("<<TreeviewSelect>>",
                       lambda e: [load_historial(e, acuerdos_tree, historial_tree, historial_label, db_path),
                                  toggle_play_button()])
    historial_tree.bind("<Button-1>", lambda e: highlight_changes(e, historial_tree))

    # Centrar ventana
    center_window(window)

    # Cargar datos iniciales
    load_acuerdos(acuerdos_tree, db_path, id_filter, text_filter, resp_filter, date_from, date_to, status_filter)

    # Configurar estilo para saltos de línea
    style.configure("Treeview", rowheight=30)



        # Reemplaza el bloque de pygame con esto:
    audio_thread = threading.Thread(target=play_audio_async, daemon=True)
    audio_thread.start()

from acuerdos.center_window import center_window
from acuerdos.carga_acuerdos import load_acuerdos
from acuerdos.cargar_historial import load_historial, highlight_changes


def on_double_click(event, acuerdos_tree, historial_tree, historial_label, db_path):
    """Manejador de doble clic en la tabla de acuerdos"""
    region = acuerdos_tree.identify("region", event.x, event.y)
    if region == "cell":
        column = acuerdos_tree.identify_column(event.x)
        item = acuerdos_tree.identify_row(event.y)
        values = acuerdos_tree.item(item, "values")

        # Verificar si el acuerdo está cerrado
        if values and len(values) > 4 and values[4] == "Cerrado":
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Obtener la ruta del PDF más reciente para este acuerdo
                cursor.execute(
                    """SELECT ruta_pdf FROM historial_acuerdos 
                    WHERE id_acuerdo = ? AND estatus = 'Cerrado'
                    ORDER BY fecha_modificacion DESC LIMIT 1""",
                    (values[0],)  # values[0] es el id_acuerdo
                )

                result = cursor.fetchone()
                conn.close()

                if result and result[0]:
                    pdf_path = result[0]
                    # Obtener el directorio contenedor del PDF
                    folder_path = os.path.dirname(pdf_path)

                    # Verificar si la ruta existe
                    if os.path.exists(folder_path):
                        # Abrir el explorador de archivos en esa ubicación
                        os.startfile(folder_path)
                    else:
                        messagebox.showwarning(
                            "Ruta no encontrada",
                            f"No se encontró la carpeta del acuerdo:\n{folder_path}"
                        )
                else:
                    messagebox.showinfo(
                        "Información",
                        "No se encontró el PDF asociado a este acuerdo cerrado"
                    )
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la carpeta del acuerdo: {str(e)}")
            return

        # Resto de la lógica para acuerdos no cerrados
        if column == "#2":  # Columna de Acuerdo
            edit_agreement_text(item, acuerdos_tree, historial_tree, historial_label, db_path)
        elif column == "#3":  # Columna de Responsables
            edit_responsables(item, acuerdos_tree, historial_tree, historial_label, db_path)
        elif column == "#6":  # Columna de Fecha Compromiso
            edit_commitment_date(item, acuerdos_tree, historial_tree, historial_label, db_path)
        elif column == "#7":  # Columna de Comentarios
            from acuerdos.edit_coms import edit_comments
            edit_comments(item, acuerdos_tree, historial_tree, historial_label, db_path)
        elif column == "#8":  # Columna de Acción
            if values and values[7] == "Cerrar":  # Si dice "Cerrar"
                id_acuerdo = values[0]
                # Si sale bien cerrar_acuerdo_seleccionado, se debe de actualizar la tabla de acuerdos.
                if cerrar_acuerdo_seleccionado(id_acuerdo, acuerdos_tree, db_path):
                    # If closing was successful, refresh the agreements table
                    load_acuerdos(acuerdos_tree, db_path, id_filter, text_filter,
                                  resp_filter, date_from, date_to, status_filter)

def edit_agreement_text(item, acuerdos_tree, historial_tree, historial_label, db_path):
    """Permite editar el texto del acuerdo con doble clic"""
    current_text = acuerdos_tree.item(item, "values")[1]

    # Crear ventana de edición
    edit_window = tk.Toplevel(acuerdos_tree.winfo_toplevel())
    edit_window.title("Editar Acuerdo")
    edit_window.transient(acuerdos_tree.winfo_toplevel())
    edit_window.grab_set()

    # Área de texto con scroll
    text_frame = ttk.Frame(edit_window)
    text_frame.pack(fill="both", expand=True, padx=10, pady=10)

    text_scroll = ttk.Scrollbar(text_frame)
    text_scroll.pack(side="right", fill="y")

    text_edit = tk.Text(
        text_frame,
        wrap="word",
        height=10,
        width=60,
        yscrollcommand=text_scroll.set
    )
    text_edit.pack(fill="both", expand=True)
    text_edit.insert("1.0", current_text)
    text_edit.focus_set()
    text_edit.mark_set("insert", "end")  # Cursor al final
    text_edit.see("end")  # Asegurar que el final sea visible
    text_scroll.config(command=text_edit.yview)



    # Función para guardar con Enter
    def on_enter(event):
        save_agreement_text(item, text_edit.get("1.0", "end-1c"), edit_window,
                            acuerdos_tree, historial_tree, historial_label, db_path)

    text_edit.bind("<Return>", on_enter)

    # Botones
    btn_frame = ttk.Frame(edit_window)
    btn_frame.pack(fill="x", padx=10, pady=10)

    ttk.Button(
        btn_frame,
        text="Guardar",
        command=lambda: save_agreement_text(item, text_edit.get("1.0", "end-1c"), edit_window,
                                            acuerdos_tree, historial_tree, historial_label, db_path)
    ).pack(side="right", padx=5)

    ttk.Button(
        btn_frame,
        text="Cancelar",
        command=edit_window.destroy
    ).pack(side="right", padx=5)

    # Centrar ventana
    center_child_window(edit_window, acuerdos_tree.winfo_toplevel())


def save_agreement_text(item, new_text, edit_window, acuerdos_tree, historial_tree, historial_label, db_path):
    """Guarda el texto editado del acuerdo"""
    old_text = acuerdos_tree.item(item, "values")[1]

    if new_text.strip() == old_text.strip():
        edit_window.destroy()
        return

    id_acuerdo = acuerdos_tree.item(item, "values")[0]

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Obtener el usuario actual de Windows
        usuario_actual = os.getlogin()

        # Registrar en historial antes de actualizar
        cursor.execute(
            """INSERT INTO historial_acuerdos 
            (id_acuerdo, acuerdo, responsables, fecha_compromiso, fecha_modificacion, usuario_modifico, estatus)
            SELECT id_acuerdo, acuerdo, responsables, fecha_compromiso, datetime('now'), ?, estatus 
            FROM acuerdos WHERE id_acuerdo = ?""",
            (usuario_actual, id_acuerdo)
        )

        # Actualizar acuerdo
        cursor.execute(
            "UPDATE acuerdos SET acuerdo = ?, fecha_estatus = datetime('now'), estatus = 'Editado' WHERE id_acuerdo = ?",
            (new_text, id_acuerdo)
        )

        conn.commit()
        conn.close()

        # Actualizar interfaz
        values = list(acuerdos_tree.item(item, "values"))
        values[1] = new_text
        acuerdos_tree.item(item, values=values)

        # Recargar historial si este acuerdo está seleccionado
        if acuerdos_tree.focus() == item:
            load_historial(None, acuerdos_tree, historial_tree, historial_label, db_path)

        edit_window.destroy()

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo actualizar el acuerdo: {e}")


def edit_responsables(item, acuerdos_tree, historial_tree, historial_label, db_path):
    """Permite editar los responsables con doble clic"""
    current_responsables = acuerdos_tree.item(item, "values")[2]
    id_acuerdo = acuerdos_tree.item(item, "values")[0]

    # Crear ventana
    resp_window = tk.Toplevel(acuerdos_tree.winfo_toplevel())
    resp_window.title("Editar Responsables")
    resp_window.geometry("700x500")  # <<< Ajusta el ancho y alto aquí
    resp_window.transient(acuerdos_tree.winfo_toplevel())
    resp_window.grab_set()



    # Obtener responsables
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT nombre FROM usuarios WHERE nombre != '' AND estatus != 'Eliminado'")
        all_responsables = set()
        for row in cursor.fetchall():
            all_responsables.update(row[0].split(", "))
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron cargar los responsables: {e}")
        return

    all_responsables = sorted(all_responsables)
    current_selection = current_responsables.split(", ") if current_responsables else []
    disponibles = [r for r in all_responsables if r not in current_selection]

    # Frame principal
    main_frame = ttk.Frame(resp_window)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # ===== Buscador dinámico =====
    search_var = tk.StringVar()

    search_frame = ttk.Frame(main_frame)
    search_frame.pack(fill="x", pady=5)
    ttk.Label(search_frame, text="Buscar responsable:").pack(side="left")
    search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
    search_entry.pack(side="left", padx=5)
    search_entry.focus()  # Enfocar al abrir

    # Subframe listas
    listas_frame = ttk.Frame(main_frame)
    listas_frame.pack(fill="both", expand=True)

    # Lista disponibles
    disponibles_label = ttk.Label(listas_frame, text="Disponibles")
    disponibles_label.grid(row=0, column=0)
    disponibles_listbox = tk.Listbox(listas_frame, selectmode="multiple", height=10, width=45)
    disponibles_listbox.grid(row=1, column=0, padx=5, pady=5)

    # Lista seleccionados
    seleccionados_label = ttk.Label(listas_frame, text="Seleccionados")
    seleccionados_label.grid(row=0, column=2)
    seleccionados_listbox = tk.Listbox(listas_frame, selectmode="multiple", height=10, width=45)
    seleccionados_listbox.grid(row=1, column=2, padx=5, pady=5)

    # Crear menú contextual
    context_menu = tk.Menu(resp_window, tearoff=0)
    context_menu.add_command(label="Editar nombre", command=lambda: editar_nombre_seleccionado())
    context_menu.add_command(label="Eliminar nombre", command=lambda: eliminar_nombre_seleccionado())

    def mostrar_menu(event):
        # Determinar en qué listbox se hizo clic
        widget = event.widget
        try:
            if widget.curselection():
                context_menu.post(event.x_root, event.y_root)
        except:
            pass

    # Vincular menú contextual a ambos listboxes
    disponibles_listbox.bind("<Button-3>", mostrar_menu)
    seleccionados_listbox.bind("<Button-3>", mostrar_menu)

    # Función para editar nombre
    def editar_nombre_seleccionado():
        # Determinar qué listbox está activo
        active_listbox = resp_window.focus_get()
        if not isinstance(active_listbox, tk.Listbox):
            return

        seleccion = active_listbox.curselection()
        if not seleccion:
            return

        index = seleccion[0]
        nombre_actual = active_listbox.get(index)

        # Ventana para editar
        edit_window = tk.Toplevel(resp_window)
        edit_window.title("Editar nombre")

        ttk.Label(edit_window, text="Nuevo nombre:").pack(padx=10, pady=5)
        nuevo_nombre_entry = ttk.Entry(edit_window, width=30)
        nuevo_nombre_entry.pack(padx=10, pady=5)
        nuevo_nombre_entry.insert(0, nombre_actual)

        def guardar_cambios():
            nuevo_nombre = nuevo_nombre_entry.get().strip()
            if nuevo_nombre and nuevo_nombre != nombre_actual:
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()

                    # Actualizar en la tabla usuarios
                    cursor.execute("UPDATE usuarios SET nombre = ? WHERE nombre = ?",
                                   (nuevo_nombre, nombre_actual))

                    # Actualizar en el listbox
                    active_listbox.delete(index)
                    active_listbox.insert(index, nuevo_nombre)

                    # Actualizar la lista de disponibles si es necesario
                    if active_listbox == disponibles_listbox:
                        if nombre_actual in disponibles:
                            disponibles.remove(nombre_actual)
                            disponibles.append(nuevo_nombre)
                            disponibles.sort()

                    conn.commit()
                    conn.close()

                    edit_window.destroy()
                    messagebox.showinfo("Éxito", "Nombre actualizado correctamente")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo actualizar el nombre: {e}")

        ttk.Button(edit_window, text="Guardar", command=guardar_cambios).pack(pady=10)

    # Función para eliminar nombre
    def eliminar_nombre_seleccionado():
        active_listbox = resp_window.focus_get()
        if not isinstance(active_listbox, tk.Listbox):
            return

        seleccion = active_listbox.curselection()
        if not seleccion:
            return

        index = seleccion[0]
        nombre = active_listbox.get(index)

        if messagebox.askyesno("Confirmar", f"¿Está seguro de marcar como eliminado a {nombre}?"):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Actualizar el estatus en lugar de eliminar
                cursor.execute("UPDATE usuarios SET estatus = 'Eliminado' WHERE nombre = ?", (nombre,))

                # Eliminar del listbox (opcional, depende de si quieres seguir mostrándolo)
                active_listbox.delete(index)

                # Actualizar la lista de disponibles si es necesario
                if active_listbox == disponibles_listbox and nombre in disponibles:
                    disponibles.remove(nombre)

                conn.commit()
                conn.close()

                messagebox.showinfo("Éxito", "Usuario marcado como eliminado correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el usuario: {e}")

    # Flechas
    btns_frame = ttk.Frame(listas_frame)
    btns_frame.grid(row=1, column=1)
    ttk.Button(btns_frame, text="→", command=lambda: mover_seleccion(disponibles_listbox, seleccionados_listbox)).pack(pady=2)
    ttk.Button(btns_frame, text="←", command=lambda: mover_seleccion(seleccionados_listbox, disponibles_listbox)).pack(pady=2)

    # Llenar listas iniciales
    for r in disponibles:
        disponibles_listbox.insert("end", r)
    for r in current_selection:
        seleccionados_listbox.insert("end", r)

    # Buscador dinámico
    def update_disponibles(*args):
        term = search_var.get().lower()
        disponibles_listbox.delete(0, "end")
        for r in disponibles:
            if term in r.lower():
                disponibles_listbox.insert("end", r)

    search_var.trace_add("write", update_disponibles)

    # ===== Nuevo responsable =====
    new_frame = ttk.Frame(resp_window)
    new_frame.pack(fill="x", padx=10, pady=5)
    ttk.Label(new_frame, text="Nuevo responsable:").pack(side="left")
    new_resp_entry = ttk.Entry(new_frame, width=30)
    new_resp_entry.pack(side="left", padx=5)


    # ===== Botones =====
    btn_frame = ttk.Frame(resp_window)
    btn_frame.pack(fill="x", padx=10, pady=10)

    def guardar_todo():
        seleccionados = [seleccionados_listbox.get(i) for i in range(seleccionados_listbox.size())]
        nuevo = new_resp_entry.get().strip()
        if nuevo:
            seleccionados.append(nuevo)
        save_responsables(
            item, seleccionados, resp_window,
            acuerdos_tree, historial_tree, historial_label, db_path
        )

    ttk.Button(btn_frame, text="Guardar", command=guardar_todo).pack(side="right", padx=5)
    ttk.Button(btn_frame, text="Cancelar", command=resp_window.destroy).pack(side="right", padx=5)

    # Atajo para enter
    resp_window.bind("<Return>", lambda event: guardar_todo())

    # Centrar
    center_child_window(resp_window, acuerdos_tree.winfo_toplevel())


def mover_seleccion(origen, destino):
    """Mueve ítems seleccionados de un listbox a otro"""
    seleccionados = list(origen.curselection())
    valores = [origen.get(i) for i in seleccionados]
    for i in reversed(seleccionados):  # Eliminar de abajo hacia arriba
        origen.delete(i)
    for v in valores:
        if v not in destino.get(0, "end"):
            destino.insert("end", v)