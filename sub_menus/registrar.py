# sub_menus/registrar.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import sqlite3
import getpass
from tkcalendar import DateEntry  # Necesitarás instalar: pip install tkcalendar
import os
import platform
from ctypes import windll

def scale_size(size):
    """Escala los tamaños según el DPI del sistema"""
    if platform.system() == 'Windows':
        try:
            windll.user32.SetProcessDPIAware()
            hdc = windll.user32.GetDC(0)
            scale = windll.gdi32.GetDeviceCaps(hdc, 88) / 96  # 88=LOGPIXELSX
            windll.user32.ReleaseDC(0, hdc)
            return int(size * scale)
        except:
            return size
    return size


def registrar_acuerdo(parent_window, db_path):
    # Configurar DPI awareness
    try:
        windll.shcore.SetProcessDpiAwareness(1)
        print("exito")
    except:
        print("vale verga")
        pass

    parent_window.withdraw()

    reg_window = tk.Toplevel()
    reg_window.title("Registrar Nuevo Acuerdo")

    # Usar tamaño escalado
    base_width = scale_size(1000)
    base_height = scale_size(800)

    # Centrar ventana
    screen_width = reg_window.winfo_screenwidth()
    screen_height = reg_window.winfo_screenheight()
    x = (screen_width - base_width) // 2
    y = (screen_height - base_height) // 2
    reg_window.geometry(f"{base_width}x{base_height}+{x}+{y}")

    # Estilos
    bg_color = "#f0f0f0"
    header_color = "#2c3e50"
    button_color = "#3498db"
    button_hover = "#2980b9"
    text_color = "#ecf0f1"
    listbox_width = scale_size(40)  # Ancho escalado para las listas

    # Header
    header = tk.Frame(reg_window, bg=header_color, height=scale_size(40))
    header.pack(fill="x", side="top")

    tk.Label(
        header,
        text="Registrar Nuevo Acuerdo",
        bg=header_color,
        fg=text_color,
        font=("Helvetica", scale_size(12), "bold")
    ).pack(side="left", padx=scale_size(20))

    # Marco principal con grid
    main_frame = tk.Frame(reg_window, bg=bg_color)
    main_frame.pack(fill="both", expand=True, padx=scale_size(20), pady=scale_size(20))

    # Configurar grid
    main_frame.columnconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(1, weight=1)

    # Campo Acuerdo (ocupa 2 columnas)
    tk.Label(
        main_frame,
        text="Acuerdo:",
        bg=bg_color,
        font=("Helvetica", scale_size(10))
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, scale_size(5)))

    acuerdo_text = tk.Text(
        main_frame,
        height=10,
        width=scale_size(80),
        font=("Helvetica", scale_size(10)),
        wrap="word"
    )
    acuerdo_text.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, scale_size(15)))

    # Fecha compromiso (columna derecha)
    fecha_frame = tk.Frame(main_frame, bg=bg_color)
    fecha_frame.grid(row=2, column=1, sticky="e", pady=(0, scale_size(15)))

    tk.Label(
        fecha_frame,
        text="Fecha compromiso:",
        bg=bg_color,
        font=("Helvetica", scale_size(10))
    ).pack(anchor="w")

    fecha_compromiso = DateEntry(
        fecha_frame,
        width=scale_size(12),
        background='darkblue',
        foreground='white',
        borderwidth=2,
        date_pattern='yyyy-mm-dd',
        font=("Helvetica", scale_size(10))
    )
    fecha_compromiso.pack(anchor="e")

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
        height=12,  # Altura aumentada
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
        height=12,  # Altura aumentada
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
        cursor.execute("SELECT DISTINCT nombre FROM usuarios ORDER BY nombre")
        responsables = cursor.fetchall()
        conn.close()

        for resp in responsables:
            if filtro in resp[0].lower():
                disponibles_listbox.insert("end", resp[0])

    search_var.trace("w", filtrar_responsables)

    # Cargar responsables iniciales
    filtrar_responsables()

    # Botones inferiores
    button_frame = tk.Frame(main_frame, bg=bg_color)
    button_frame.grid(row=5, column=0, columnspan=2, pady=(20, 0), sticky="e")

    # sub_menus/registrar.py (actualización)
    def guardar_acuerdo():
        acuerdo = acuerdo_text.get("1.0", "end-1c").strip()
        fecha_comp = fecha_compromiso.get_date()
        responsables = ", ".join(seleccionados_listbox.get(0, "end"))

        if not acuerdo:
            messagebox.showwarning("Advertencia", "Debe ingresar el texto del acuerdo")
            return

        if not seleccionados_listbox.size():
            messagebox.showwarning("Advertencia", "Debe seleccionar al menos un responsable")
            return

        if messagebox.askyesno("Confirmar", "¿Desea guardar este acuerdo?"):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Generar ID de acuerdo único
                id_acuerdo = f"AC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

                cursor.execute(
                    """INSERT INTO acuerdos 
                    (id_acuerdo, acuerdo, responsables, fecha_compromiso, 
                     fecha_registro, usuario_registra, estatus, fecha_estatus)
                    VALUES (?, ?, ?, ?, ?, ?, 'Activo', ?)""",
                    (
                        id_acuerdo,
                        acuerdo,
                        responsables,
                        fecha_comp,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        getpass.getuser(),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                )
                conn.commit()
                conn.close()

                #messagebox.showinfo("Éxito", "Acuerdo registrado correctamente")
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

    # Comportamiento al cerrar
    def on_closing():
        reg_window.destroy()
        parent_window.deiconify()

    reg_window.protocol("WM_DELETE_WINDOW", on_closing)

    # Configurar el grid para que se expanda correctamente
    main_frame.rowconfigure(4, weight=1)
    list_frame.columnconfigure(0, weight=1)
    list_frame.columnconfigure(2, weight=1)

    reg_window.mainloop()