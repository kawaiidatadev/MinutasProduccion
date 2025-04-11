from common import *
from acuerdos.center_window import center_window
def nuevo_acuerdo(parent_window, db_path):
    print("Nuevo Acuerdo")  # Aquí iría la lógica para crear nuevo acuerdo
    registrar_acuerdo(parent_window, db_path)


def registrar_acuerdo(parent_window, db_path):
    listbox_width = 30
    parent_window.withdraw()

    reg_window = tk.Toplevel()
    reg_window.title("Registrar Nuevo Acuerdo")

    # Tamaño base de la ventana (sin escalado)
    base_width = 800
    base_height = 825
    reg_window.geometry(f"{base_width}x{base_height}")

    # Centrar la ventana
    center_window(reg_window)

    # Estilos
    bg_color = "#f0f0f0"
    header_color = "#2c3e50"
    button_color = "#3498db"
    button_hover = "#2980b9"
    text_color = "#ecf0f1"
    font_normal = ("Helvetica", 10)
    font_bold = ("Helvetica", 10, "bold")
    font_title = ("Helvetica", 12, "bold")

    # Header
    header = tk.Frame(reg_window, bg=header_color, height=40)
    header.pack(fill="x", side="top")

    tk.Label(
        header,
        text="Registrar Nuevo Acuerdo",
        bg=header_color,
        fg=text_color,
        font=font_title
    ).pack(side="left", padx=20)

    # Marco principal con grid
    main_frame = tk.Frame(reg_window, bg=bg_color)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Configurar grid
    main_frame.columnconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(1, weight=1)

    # Campo Acuerdo (ocupa 2 columnas)
    tk.Label(
        main_frame,
        text="Acuerdo:",
        bg=bg_color,
        font=font_bold
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

    acuerdo_text = tk.Text(
        main_frame,
        height=10,
        width=80,
        font=font_normal,
        wrap="word"
    )
    acuerdo_text.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 15))
    acuerdo_text.focus_set()

    # Fecha compromiso (columna derecha)
    fecha_frame = tk.Frame(main_frame, bg=bg_color)
    fecha_frame.grid(row=2, column=1, sticky="e", pady=(0, 15))

    # Variable para controlar el estado del botón "No aplica"
    no_aplica_var = tk.BooleanVar(value=False)

    def toggle_no_aplica():
        if no_aplica_var.get():
            fecha_compromiso.config(state='normal')
            no_aplica_btn.config(relief='raised', bg=button_color)
            no_aplica_var.set(False)
        else:
            fecha_compromiso.config(state='disabled')
            no_aplica_btn.config(relief='sunken', bg='#e74c3c')
            no_aplica_var.set(True)

    # Botón "No aplica" (CORREGIDO)
    no_aplica_btn = tk.Button(
        fecha_frame,
        text="No aplica fecha",
        command=toggle_no_aplica,
        bg=button_color,
        fg=text_color,
        relief='raised'
    )
    no_aplica_btn.pack(side='right', padx=(10, 0))

    tk.Label(
        fecha_frame,
        text="Fecha compromiso:",
        bg=bg_color,
        font=("Helvetica", 10)
    ).pack(side='left')

    fecha_compromiso = DateEntry(
        fecha_frame,
        width=12,
        background='darkblue',
        foreground='white',
        borderwidth=2,
        date_pattern='yyyy-mm-dd',
        font=("Helvetica", 10)
    )
    fecha_compromiso.pack(side='left')

    # Marco para responsables (ocupa 2 columnas)
    tk.Label(
        main_frame,
        text="Responsables:",
        bg=bg_color,
        font=("Helvetica", 10)
    ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 5))

    # Frame para el buscador y listas
    resp_main_frame = tk.Frame(main_frame, bg=bg_color)
    resp_main_frame.grid(row=4, column=0, columnspan=2, sticky="nsew")

    # Frame para el buscador
    search_frame = tk.Frame(resp_main_frame, bg=bg_color)
    search_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        search_frame,
        text="Buscar responsable:",
        bg=bg_color,
        font=("Helvetica", 10)
    ).pack(side="left")

    search_var = tk.StringVar()
    search_entry = tk.Entry(
        search_frame,
        textvariable=search_var,
        font=("Helvetica", 10),
        width=30
    )
    search_entry.pack(side="left", padx=5)

    # Frame para agregar nuevo responsable
    new_resp_frame = tk.Frame(resp_main_frame, bg=bg_color)
    new_resp_frame.pack(fill="x", pady=(10, 0))

    tk.Label(
        new_resp_frame,
        text="Agregar nuevo responsable:",
        bg=bg_color,
        font=("Helvetica", 10)
    ).pack(side="left")

    new_resp_var = tk.StringVar()
    new_resp_entry = tk.Entry(
        new_resp_frame,
        textvariable=new_resp_var,
        font=("Helvetica", 10),
        width=30
    )
    new_resp_entry.pack(side="left", padx=5)

    def agregar_nuevo_responsable():
        nuevo = new_resp_var.get().strip()
        if not nuevo:
            messagebox.showwarning("Advertencia", "Debe ingresar un nombre")
            return

        # Verificar si ya existe en la lista de disponibles
        items = disponibles_listbox.get(0, "end")
        if nuevo in items:
            messagebox.showwarning("Advertencia", "Este responsable ya existe")
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Verificar si ya existe en la tabla usuarios
            cursor.execute("SELECT nombre FROM usuarios WHERE nombre = ?", (nuevo,))
            if not cursor.fetchone():
                # Obtener fecha y hora actual en México (considerando zona horaria)
                from datetime import datetime
                import pytz
                tz_mexico = pytz.timezone('America/Mexico_City')
                fecha_actual = datetime.now(tz_mexico).strftime("%Y-%m-%d %H:%M:%S")

                # Obtener usuario de Windows actual
                import getpass
                usuario_actual = getpass.getuser()

                # Insertar nuevo usuario con todos los campos
                cursor.execute(
                    """INSERT INTO usuarios 
                    (nombre, fecha_registro, usuario_registra, estatus) 
                    VALUES (?, ?, ?, 'Activo')""",
                    (
                        nuevo,
                        fecha_actual,
                        usuario_actual
                    )
                )
                conn.commit()

            conn.close()


            # Agregar a la lista de disponibles y seleccionarlo
            disponibles_listbox.insert("end", nuevo)
            disponibles_listbox.selection_clear(0, "end")
            disponibles_listbox.selection_set("end")
            new_resp_var.set("")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el responsable: {e}")

    tk.Button(
        new_resp_frame,
        text="Agregar",
        command=agregar_nuevo_responsable,
        bg="#27ae60",
        fg="white",
        font=("Helvetica", 8)
    ).pack(side="left", padx=5)

    # Frame para las listas
    list_frame = tk.Frame(resp_main_frame, bg=bg_color)
    list_frame.pack(fill="both", expand=True)

    # Lista de disponibles
    disponibles_frame = tk.Frame(list_frame, bg=bg_color)
    disponibles_frame.grid(row=0, column=0, padx=5, sticky="nsew")

    tk.Label(
        disponibles_frame,
        text="Disponibles",
        bg=bg_color,
        font=("Helvetica", 10, "bold")
    ).pack()

    disponibles_listbox = tk.Listbox(
        disponibles_frame,
        height=12,
        width=listbox_width,
        selectmode="multiple",
        font=("Helvetica", 10)
    )
    disponibles_listbox.pack(fill="both", expand=True)

    # Botones de transferencia
    button_transfer_frame = tk.Frame(list_frame, bg=bg_color)
    button_transfer_frame.grid(row=0, column=1, padx=10)

    def transfer_to_selected():
        selected = disponibles_listbox.curselection()
        for i in selected[::-1]:
            item = disponibles_listbox.get(i)
            seleccionados_listbox.insert("end", item)
            disponibles_listbox.delete(i)

    def transfer_from_selected():
        selected = seleccionados_listbox.curselection()
        for i in selected[::-1]:
            item = seleccionados_listbox.get(i)
            disponibles_listbox.insert("end", item)
            seleccionados_listbox.delete(i)

    tk.Button(
        button_transfer_frame,
        text="→",
        command=transfer_to_selected,
        width=5,
        height=2
    ).pack(pady=5)

    tk.Button(
        button_transfer_frame,
        text="←",
        command=transfer_from_selected,
        width=5,
        height=2
    ).pack(pady=5)

    # Lista de seleccionados
    seleccionados_frame = tk.Frame(list_frame, bg=bg_color)
    seleccionados_frame.grid(row=0, column=2, padx=5, sticky="nsew")

    tk.Label(
        seleccionados_frame,
        text="Seleccionados",
        bg=bg_color,
        font=("Helvetica", 10, "bold")
    ).pack()

    seleccionados_listbox = tk.Listbox(
        seleccionados_frame,
        height=12,
        width=listbox_width,
        selectmode="multiple",
        font=("Helvetica", 10)
    )
    seleccionados_listbox.pack(fill="both", expand=True)

    # Función para filtrar responsables
    def filtrar_responsables(*args):
        filtro = search_var.get().lower()
        disponibles_listbox.delete(0, "end")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # Nueva consulta usando split recursivo sin JSON
            cursor.execute("""
                WITH RECURSIVE split_responsables AS (
                    SELECT 
                        substr(responsables || ',', 0, instr(responsables || ',', ',')) AS nombre,
                        substr(responsables, instr(responsables || ',', ',') + 1) AS remaining
                    FROM acuerdos
                    WHERE responsables != '' AND responsables IS NOT NULL

                    UNION ALL

                    SELECT
                        substr(remaining, 0, instr(remaining || ',', ',')),
                        substr(remaining, instr(remaining || ',', ',') + 1)
                    FROM split_responsables
                    WHERE remaining != ''
                ),
                cleaned_names AS (
                    SELECT trim(nombre) AS nombre
                    FROM split_responsables
                    WHERE nombre != ''
                ),
                frecuentes AS (
                    SELECT nombre, COUNT(*) as frecuencia
                    FROM cleaned_names
                    GROUP BY nombre
                    ORDER BY frecuencia DESC
                ),
                todos_usuarios AS (
                    SELECT nombre, 0 as frecuencia
                    FROM usuarios
                )
                SELECT nombre FROM (
                    SELECT nombre, frecuencia FROM frecuentes
                    UNION
                    SELECT nombre, frecuencia FROM todos_usuarios
                    WHERE nombre NOT IN (SELECT nombre FROM frecuentes)
                )
                ORDER BY frecuencia DESC, nombre ASC
            """)

            responsables = cursor.fetchall()

            # Limpiar nombres y filtrar
            unique_names = {resp[0].strip() for resp in responsables if resp[0].strip()}
            sorted_names = sorted(unique_names, key=lambda x: (-sum(1 for r in responsables if r[0].strip() == x), x))

            for nombre in sorted_names:
                if filtro in nombre.lower():
                    disponibles_listbox.insert("end", nombre)

        except sqlite3.Error as e:
            print(f"Error en consulta SQL: {e}")
        finally:
            conn.close()

        for resp in responsables:
            if filtro in resp[0].lower():
                disponibles_listbox.insert("end", resp[0])

    search_var.trace("w", filtrar_responsables)
    filtrar_responsables()  # Cargar inicialmente

    # Botones inferiores
    button_frame = tk.Frame(main_frame, bg=bg_color)
    button_frame.grid(row=5, column=0, columnspan=2, pady=(20, 0), sticky="e")

    def guardar_acuerdo():
        acuerdo = acuerdo_text.get("1.0", "end-1c").strip()

        # Obtener la fecha del calendario (DateEntry) independientemente del checkbox
        fecha_calendario = fecha_compromiso.get_date()

        # Manejar el caso de "No aplica"
        if no_aplica_var.get():
            comentarios = "Sin fecha compromiso"
        else:
            comentarios = ""  # O puedes usar None si prefieres

        responsables = ", ".join(seleccionados_listbox.get(0, "end"))

        if not acuerdo:
            messagebox.showwarning("Advertencia", "Debe ingresar el texto del acuerdo")
            return

        if not seleccionados_listbox.size():
            messagebox.showwarning("Advertencia", "Debe seleccionar al menos un responsable")
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Generar ID de acuerdo único
            id_acuerdo = f"AC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Obtener fecha y hora actual
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                """INSERT INTO acuerdos 
                (id_acuerdo, acuerdo, responsables, fecha_compromiso, 
                 fecha_registro, usuario_registra, estatus, fecha_estatus, comentarios)
                VALUES (?, ?, ?, ?, ?, ?, 'Activo', ?, ?)""",
                (
                    id_acuerdo,
                    acuerdo,
                    responsables,
                    fecha_calendario,  # Siempre la fecha del calendario
                    fecha_actual,
                    getpass.getuser(),
                    fecha_actual,
                    comentarios  # "Sin fecha compromiso" o vacío
                )
            )
            conn.commit()
            conn.close()

            messagebox.showinfo("Éxito", "Acuerdo registrado correctamente")
            reg_window.destroy()
            parent_window.deiconify()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el acuerdo: {e}")
    tk.Button(
        button_frame,
        text="Guardar",
        command=guardar_acuerdo,
        bg="#2ecc71",
        fg="white",
        font=("Helvetica", 10, "bold"),
        width=10
    ).pack(side="right", padx=5)

    def cancelar():
        reg_window.destroy()
        parent_window.deiconify()

    tk.Button(
        button_frame,
        text="Cancelar",
        command=cancelar,
        bg="#e74c3c",
        fg="white",
        font=("Helvetica", 10),
        width=10
    ).pack(side="right", padx=5)

    def on_closing():
        reg_window.destroy()
        parent_window.deiconify()

    reg_window.protocol("WM_DELETE_WINDOW", on_closing)

    # Configurar el grid para que se expanda correctamente
    main_frame.rowconfigure(4, weight=1)
    list_frame.columnconfigure(0, weight=1)
    list_frame.columnconfigure(2, weight=1)

    reg_window.mainloop()
