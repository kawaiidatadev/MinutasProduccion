# sub_menus/editar.py (versión actualizada)
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import sqlite3
import getpass
from tkcalendar import DateEntry

def editar_acuerdo(parent_window, db_path):
    # Ocultar el menú principal
    parent_window.withdraw()

    # Crear ventana de edición
    edit_window = tk.Toplevel()
    edit_window.title("Editar Acuerdo Existente")
    edit_window.geometry("1100x850")  # Aumenté el tamaño para los nuevos filtros

    # Centrar la ventana
    screen_width = edit_window.winfo_screenwidth()
    screen_height = edit_window.winfo_screenheight()
    x = (screen_width // 2) - (1100 // 2)
    y = (screen_height // 2) - (850 // 2)
    edit_window.geometry(f"1100x850+{x}+{y}")

    # Estilos
    bg_color = "#f0f0f0"
    header_color = "#2c3e50"
    button_color = "#3498db"
    button_hover = "#2980b9"
    text_color = "#ecf0f1"
    listbox_width = 40

    # Header
    header = tk.Frame(edit_window, bg=header_color, height=40)
    header.pack(fill="x", side="top")

    tk.Label(
        header,
        text="Editar Acuerdo Existente",
        bg=header_color,
        fg=text_color,
        font=("Helvetica", 12, "bold")
    ).pack(side="left", padx=20)

    # Frame para filtros
    filter_frame = tk.Frame(edit_window, bg=bg_color, padx=10, pady=10)
    filter_frame.pack(fill="x")

    # Filtro por fecha de creación
    tk.Label(filter_frame, text="Fecha desde:", bg=bg_color).grid(row=0, column=0, padx=5)
    fecha_desde = DateEntry(
        filter_frame,
        width=12,
        background='darkblue',
        foreground='white',
        date_pattern='yyyy-mm-dd'
    )
    fecha_desde.grid(row=0, column=1, padx=5)

    tk.Label(filter_frame, text="hasta:", bg=bg_color).grid(row=0, column=2, padx=5)
    fecha_hasta = DateEntry(
        filter_frame,
        width=12,
        background='darkblue',
        foreground='white',
        date_pattern='yyyy-mm-dd'
    )
    fecha_hasta.grid(row=0, column=3, padx=5)
    fecha_hasta.set_date(datetime.now())  # Fecha actual por defecto

    # Filtro por responsable
    tk.Label(filter_frame, text="Responsable:", bg=bg_color).grid(row=0, column=4, padx=5)
    responsable_var = tk.StringVar()
    responsable_cb = ttk.Combobox(
        filter_frame,
        textvariable=responsable_var,
        width=20,
        state="readonly"
    )
    responsable_cb.grid(row=0, column=5, padx=5)



    # Botón para aplicar filtros
    def aplicar_filtros():
        cargar_lista_acuerdos()

    tk.Button(
        filter_frame,
        text="Aplicar Filtros",
        command=aplicar_filtros,
        bg=button_color,
        fg=text_color
    ).grid(row=0, column=6, padx=10)

    # Botón para limpiar filtros
    def limpiar_filtros():
        fecha_desde.set_date(datetime.now() - timedelta(days=30))
        fecha_hasta.set_date(datetime.now())
        responsable_var.set('')
        cargar_lista_acuerdos()

    tk.Button(
        filter_frame,
        text="Limpiar",
        command=limpiar_filtros,
        bg="#95a5a6",
        fg=text_color
    ).grid(row=0, column=7, padx=5)

    # Marco principal con grid
    main_frame = tk.Frame(edit_window, bg=bg_color)
    main_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # Configurar grid
    main_frame.columnconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(1, weight=1)

    # Frame para selección de acuerdo
    seleccion_frame = tk.Frame(main_frame, bg=bg_color)
    seleccion_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))

    tk.Label(
        seleccion_frame,
        text="Seleccionar acuerdo a editar:",
        bg=bg_color,
        font=("Helvetica", 10)
    ).pack(side="left")

    # Combobox para seleccionar acuerdo
    acuerdo_var = tk.StringVar()
    acuerdo_cb = ttk.Combobox(
        seleccion_frame,
        textvariable=acuerdo_var,
        font=("Helvetica", 10),
        width=50,
        state="readonly"
    )
    acuerdo_cb.pack(side="left", padx=10)


    # Botón para cargar acuerdo
    def cargar_acuerdo():
        id_acuerdo = acuerdo_var.get().split(" - ")[0]
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT acuerdo, responsables, fecha_compromiso FROM acuerdos WHERE id_acuerdo = ?",
                (id_acuerdo,)
            )
            resultado = cursor.fetchone()
            conn.close()

            if resultado:
                # Limpiar campos
                acuerdo_text.delete("1.0", "end")
                disponibles_listbox.delete(0, "end")
                seleccionados_listbox.delete(0, "end")

                # Llenar campos
                acuerdo_text.insert("1.0", resultado[0])
                fecha_compromiso.set_date(datetime.strptime(resultado[2], "%Y-%m-%d").date())

                # Cargar responsables seleccionados
                responsables = resultado[1].split(", ")
                todos_responsables = []

                # Obtener todos los responsables disponibles
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT nombre FROM usuarios ORDER BY nombre")
                todos_responsables = [r[0] for r in cursor.fetchall()]
                conn.close()

                # Separar disponibles y seleccionados
                for resp in todos_responsables:
                    if resp in responsables:
                        seleccionados_listbox.insert("end", resp)
                    else:
                        disponibles_listbox.insert("end", resp)

                # Habilitar edición
                acuerdo_text.config(state="normal")
                fecha_compromiso.config(state="normal")
                search_entry.config(state="normal")
                disponibles_listbox.config(state="normal")
                seleccionados_listbox.config(state="normal")
                transfer_btn_to.config(state="normal")
                transfer_btn_from.config(state="normal")
                actualizar_btn.config(state="normal")



                # Auto-seleccionar el primer responsable si existe
                if seleccionados_listbox.size() > 0:
                    seleccionados_listbox.selection_set(0)

            else:
                messagebox.showerror("Error", "No se encontró el acuerdo seleccionado")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el acuerdo: {e}")

    tk.Button(
        seleccion_frame,
        text="Cargar Acuerdo",
        command=cargar_acuerdo,
        bg=button_color,
        fg=text_color,
        font=("Helvetica", 10)
    ).pack(side="left")

    # Campo Acuerdo
    tk.Label(
        main_frame,
        text="Acuerdo:",
        bg=bg_color,
        font=("Helvetica", 10)
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 5))

    acuerdo_text = tk.Text(
        main_frame,
        height=10,
        width=80,
        font=("Helvetica", 10),
        wrap="word",
        state="disabled"  # Inicialmente deshabilitado
    )
    acuerdo_text.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 15))



    # Fecha compromiso
    fecha_frame = tk.Frame(main_frame, bg=bg_color)
    fecha_frame.grid(row=3, column=1, sticky="e", pady=(0, 15))

    tk.Label(
        fecha_frame,
        text="Fecha compromiso:",
        bg=bg_color,
        font=("Helvetica", 10)
    ).pack(anchor="w")

    fecha_compromiso = DateEntry(
        fecha_frame,
        width=12,
        background='darkblue',
        foreground='white',
        borderwidth=2,
        date_pattern='yyyy-mm-dd',
        font=("Helvetica", 10),
        state="disabled"  # Inicialmente deshabilitado
    )
    fecha_compromiso.pack(anchor="e")

    # Marco para responsables
    tk.Label(
        main_frame,
        text="Responsables:",
        bg=bg_color,
        font=("Helvetica", 10)
    ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 5))

    resp_main_frame = tk.Frame(main_frame, bg=bg_color)
    resp_main_frame.grid(row=5, column=0, columnspan=2, sticky="nsew")

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
        width=30,
        state="disabled"  # Inicialmente deshabilitado
    )
    search_entry.pack(side="left", padx=5)

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
        font=("Helvetica", 10),
        state="disabled"  # Inicialmente deshabilitado
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

    transfer_btn_to = tk.Button(
        button_transfer_frame,
        text="→",
        command=transfer_to_selected,
        width=5,
        height=2,
        state="disabled"  # Inicialmente deshabilitado
    )
    transfer_btn_to.pack(pady=5)

    transfer_btn_from = tk.Button(
        button_transfer_frame,
        text="←",
        command=transfer_from_selected,
        width=5,
        height=2,
        state="disabled"  # Inicialmente deshabilitado
    )
    transfer_btn_from.pack(pady=5)

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
        font=("Helvetica", 10),
        state="disabled"  # Inicialmente deshabilitado
    )
    seleccionados_listbox.pack(fill="both", expand=True)

    # Función para filtrar responsables
    def filtrar_responsables(*args):
        filtro = search_var.get().lower()
        disponibles_listbox.delete(0, "end")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT nombre FROM usuarios ORDER BY nombre")
        responsables = cursor.fetchall()
        conn.close()

        # Obtener responsables ya seleccionados
        seleccionados = seleccionados_listbox.get(0, "end")

        for resp in responsables:
            if filtro in resp[0].lower() and resp[0] not in seleccionados:
                disponibles_listbox.insert("end", resp[0])

    search_var.trace("w", filtrar_responsables)

    # Botones inferiores
    button_frame = tk.Frame(main_frame, bg=bg_color)
    button_frame.grid(row=6, column=0, columnspan=2, pady=(20, 0), sticky="e")

    # sub_menus/editar.py (actualización)
    def actualizar_acuerdo():
        id_acuerdo = acuerdo_var.get().split(" - ")[0]
        acuerdo = acuerdo_text.get("1.0", "end-1c").strip()
        fecha_comp = fecha_compromiso.get_date()
        responsables = ", ".join(seleccionados_listbox.get(0, "end"))


        if not acuerdo:
            messagebox.showwarning("Advertencia", "Debe ingresar el texto del acuerdo")
            return

        if not seleccionados_listbox.size():
            messagebox.showwarning("Advertencia", "Debe seleccionar al menos un responsable")
            return

        if messagebox.askyesno("Confirmar", "¿Desea actualizar este acuerdo?"):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # 1. Primero guardamos la versión actual en el historial
                cursor.execute(
                    """INSERT INTO historial_acuerdos 
                    (id_acuerdo, acuerdo, responsables, fecha_compromiso, 
                     fecha_modificacion, usuario_modifico, estatus)
                    SELECT id_acuerdo, acuerdo, responsables, fecha_compromiso,
                           ?, ?, estatus
                    FROM acuerdos 
                    WHERE id_acuerdo = ?""",
                    (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        getpass.getuser(),
                        id_acuerdo
                    )
                )

                # 2. Luego actualizamos el acuerdo con los nuevos datos
                cursor.execute(
                    """UPDATE acuerdos 
                    SET acuerdo = ?, 
                        responsables = ?, 
                        fecha_compromiso = ?,
                        fecha_registro = ?,
                        usuario_registra = ?,
                        estatus = 'Editado',
                        fecha_estatus = ?
                    WHERE id_acuerdo = ?""",
                    (
                        acuerdo,
                        responsables,
                        fecha_comp,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        getpass.getuser(),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        id_acuerdo
                    )
                )

                conn.commit()
                conn.close()

                messagebox.showinfo("Éxito", "Acuerdo actualizado correctamente")
                edit_window.destroy()
                parent_window.deiconify()

            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el acuerdo: {e}")

    actualizar_btn = tk.Button(
        button_frame,
        text="Actualizar",
        command=actualizar_acuerdo,
        bg="#2ecc71",
        fg="white",
        font=("Helvetica", 10, "bold"),
        width=10,
        state="disabled"  # Inicialmente deshabilitado
    )
    actualizar_btn.pack(side="right", padx=5)

    # En editar_acuerdo(), después de cargar el acuerdo:
    def ver_historial():
        from sub_menus.historial2 import mostrar_historial
        id_acuerdo = acuerdo_var.get().split(" - ")[0]
        mostrar_historial(edit_window, db_path, id_acuerdo)

    tk.Button(
        button_frame,
        text="Ver Historial",
        command=ver_historial,
        bg="#f39c12",
        fg="white",
        font=("Helvetica", 10),
        width=10
    ).pack(side="right", padx=5)

    def cancelar():
        edit_window.destroy()
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

    # Función para habilitar controles cuando se carga un acuerdo
    def habilitar_controles():
        acuerdo_text.config(state="normal")
        fecha_compromiso.config(state="normal")
        search_entry.config(state="normal")
        disponibles_listbox.config(state="normal")
        seleccionados_listbox.config(state="normal")
        transfer_btn_to.config(state="normal")
        transfer_btn_from.config(state="normal")
        actualizar_btn.config(state="normal")

    # Cargar lista de acuerdos en el combobox
    def cargar_lista_acuerdos():
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Construir consulta con filtros
            query = """SELECT id_acuerdo, acuerdo FROM acuerdos WHERE estatus != 'Cerrado'"""
            params = []

            # Filtro por fecha
            if fecha_desde.get_date():
                query += " AND fecha_registro >= ?"
                params.append(fecha_desde.get_date().strftime("%Y-%m-%d"))
            if fecha_hasta.get_date():
                query += " AND fecha_registro <= ?"
                params.append((fecha_hasta.get_date() + timedelta(days=1)).strftime("%Y-%m-%d"))

            # Filtro por responsable
            if responsable_var.get():
                query += " AND responsables LIKE ?"
                params.append(f"%{responsable_var.get()}%")

            query += " ORDER BY fecha_registro DESC"

            cursor.execute(query, params)
            acuerdos = cursor.fetchall()
            conn.close()

            acuerdo_cb['values'] = [f"{a[0]} - {a[1][:30]}..." for a in acuerdos]

            if acuerdos:
                acuerdo_var.set(acuerdos[0][0])  # Seleccionar el primero por defecto
                # Auto-cargar el primer acuerdo
                cargar_acuerdo()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los acuerdos: {e}")

    # Cargar lista de responsables para el filtro
    def cargar_responsables():
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT nombre FROM usuarios ORDER BY nombre")
            responsables = [r[0] for r in cursor.fetchall()]
            conn.close()
            responsable_cb['values'] = responsables
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los responsables: {e}")

    # Configurar fechas por defecto (últimos 30 días)
    fecha_desde.set_date(datetime.now() - timedelta(days=30))
    fecha_hasta.set_date(datetime.now())

    # Cargar datos iniciales
    cargar_responsables()
    cargar_lista_acuerdos()

    # Configurar evento cuando se selecciona un acuerdo
    acuerdo_cb.bind("<<ComboboxSelected>>", lambda e: habilitar_controles())

    # Configurar el grid para que se expanda correctamente
    main_frame.rowconfigure(5, weight=1)
    list_frame.columnconfigure(0, weight=1)
    list_frame.columnconfigure(2, weight=1)

    # Comportamiento al cerrar
    def on_closing():
        edit_window.destroy()
        parent_window.deiconify()

    edit_window.protocol("WM_DELETE_WINDOW", on_closing)

    edit_window.mainloop()