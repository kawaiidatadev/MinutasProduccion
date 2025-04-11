# sub_menus/cerrar.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import sqlite3
from tkcalendar import DateEntry
# Importar timedelta correctamente
from datetime import timedelta
import os
import shutil
import getpass
from datetime import datetime, timedelta
import sqlite3
from tkinter import filedialog
import os
import shutil
import getpass
from datetime import datetime, timedelta
import sqlite3
from tkinter import filedialog
from fpdf import FPDF  # Para generar PDFs



def cerrar_acuerdo(parent_window, db_path):
    # Ocultar el menú principal
    parent_window.withdraw()

    # Crear ventana de cierre
    close_window = tk.Toplevel()
    close_window.title("Cerrar Acuerdos")
    close_window.geometry("1200x700")

    # Centrar la ventana
    screen_width = close_window.winfo_screenwidth()
    screen_height = close_window.winfo_screenheight()
    x = (screen_width // 2) - (1200 // 2)
    y = (screen_height // 2) - (700 // 2)
    close_window.geometry(f"1200x700+{x}+{y}")

    # Estilos
    bg_color = "#f0f0f0"
    header_color = "#2c3e50"
    button_color = "#3498db"
    button_hover = "#2980b9"
    text_color = "#ecf0f1"
    close_button_color = "#e74c3c"
    close_button_hover = "#c0392b"

    # Header
    header = tk.Frame(close_window, bg=header_color, height=40)
    header.pack(fill="x", side="top")

    tk.Label(
        header,
        text="Cerrar Acuerdos",
        bg=header_color,
        fg=text_color,
        font=("Helvetica", 12, "bold")
    ).pack(side="left", padx=20)

    # Frame para filtros
    filter_frame = tk.Frame(close_window, bg=bg_color, padx=10, pady=10)
    filter_frame.pack(fill="x")

    # Filtro por ID de acuerdo
    tk.Label(filter_frame, text="ID Acuerdo:", bg=bg_color).grid(row=0, column=0, padx=5)
    id_filter = tk.Entry(filter_frame, width=15)
    id_filter.grid(row=0, column=1, padx=5)

    # Filtro por texto en acuerdo
    tk.Label(filter_frame, text="Texto en acuerdo:", bg=bg_color).grid(row=0, column=2, padx=5)
    text_filter = tk.Entry(filter_frame, width=30)
    text_filter.grid(row=0, column=3, padx=5)

    # Filtro por responsable
    tk.Label(filter_frame, text="Responsable:", bg=bg_color).grid(row=0, column=4, padx=5)
    resp_filter = tk.Entry(filter_frame, width=20)
    resp_filter.grid(row=0, column=5, padx=5)

    # Filtro por fecha
    tk.Label(filter_frame, text="Fecha desde:", bg=bg_color).grid(row=1, column=0, padx=5)
    fecha_desde = DateEntry(
        filter_frame,
        width=12,
        background='darkblue',
        foreground='white',
        date_pattern='yyyy-mm-dd'
    )
    fecha_desde.grid(row=1, column=1, padx=5)

    tk.Label(filter_frame, text="hasta:", bg=bg_color).grid(row=1, column=2, padx=5)
    fecha_hasta = DateEntry(
        filter_frame,
        width=12,
        background='darkblue',
        foreground='white',
        date_pattern='yyyy-mm-dd'
    )
    fecha_hasta.grid(row=1, column=3, padx=5)
    fecha_hasta.set_date(datetime.now())

    # Botones de filtrado
    btn_frame = tk.Frame(filter_frame, bg=bg_color)
    btn_frame.grid(row=0, column=6, rowspan=2, padx=10)

    def aplicar_filtros():
        cargar_acuerdos()

    tk.Button(
        btn_frame,
        text="Aplicar Filtros",
        command=aplicar_filtros,
        bg=button_color,
        fg=text_color,
        width=15
    ).pack(pady=2)

    def limpiar_filtros():
        id_filter.delete(0, "end")
        text_filter.delete(0, "end")
        resp_filter.delete(0, "end")
        fecha_desde.set_date(datetime.now() - timedelta(days=30))
        fecha_hasta.set_date(datetime.now())
        cargar_acuerdos()

    tk.Button(
        btn_frame,
        text="Limpiar Filtros",
        command=limpiar_filtros,
        bg="#95a5a6",
        fg=text_color,
        width=15
    ).pack(pady=2)

    # Frame principal para la tabla
    main_frame = tk.Frame(close_window, bg=bg_color)
    main_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # Treeview para mostrar los acuerdos
    tree_frame = tk.Frame(main_frame, bg=bg_color)
    tree_frame.pack(fill="both", expand=True)

    # Scrollbars
    y_scroll = ttk.Scrollbar(tree_frame)
    y_scroll.pack(side="right", fill="y")

    x_scroll = ttk.Scrollbar(tree_frame, orient="horizontal")
    x_scroll.pack(side="bottom", fill="x")

    # Crear el Treeview
    columns = ("id", "acuerdo", "responsables", "fecha_compromiso", "estatus", "accion")
    tree = ttk.Treeview(
        tree_frame,
        columns=columns,
        yscrollcommand=y_scroll.set,
        xscrollcommand=x_scroll.set,
        selectmode="extended",
        height=15
    )

    # Configurar scrollbars
    y_scroll.config(command=tree.yview)
    x_scroll.config(command=tree.xview)

    # Configurar columnas
    tree.heading("id", text="ID Acuerdo")
    tree.heading("acuerdo", text="Acuerdo")
    tree.heading("responsables", text="Responsables")
    tree.heading("fecha_compromiso", text="Fecha Compromiso")
    tree.heading("estatus", text="Estatus")
    tree.heading("accion", text="Acción")

    tree.column("id", width=120, anchor="w")
    tree.column("acuerdo", width=300, anchor="w")
    tree.column("responsables", width=200, anchor="w")
    tree.column("fecha_compromiso", width=120, anchor="center")
    tree.column("estatus", width=100, anchor="center")
    tree.column("accion", width=120, anchor="center")

    tree.pack(fill="both", expand=True)

    # Función para cerrar un acuerdo
    def cerrar_acuerdo_seleccionado(id_acuerdo):
        # Crear ventana para capturar detalles del cierre
        details_window = tk.Toplevel()
        details_window.title(f"Cerrar Acuerdo {id_acuerdo}")
        details_window.geometry("600x500")

        # Centrar la ventana
        center_window(details_window)

        # Estilos
        bg_color = "#f0f0f0"
        header_color = "#2c3e50"
        text_color = "#ecf0f1"

        # Header
        header = tk.Frame(details_window, bg=header_color, height=40)
        header.pack(fill="x", side="top")

        tk.Label(
            header,
            text=f"Cerrar Acuerdo {id_acuerdo}",
            bg=header_color,
            fg=text_color,
            font=("Helvetica", 12, "bold")
        ).pack(side="left", padx=20)

        # Frame principal
        main_frame = tk.Frame(details_window, bg=bg_color, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)

        # Comentarios del cierre
        tk.Label(main_frame, text="Comentarios del cierre:", bg=bg_color).pack(anchor="w")
        comentarios_text = tk.Text(main_frame, height=8, width=70)
        comentarios_text.pack(pady=5)

        # Frame para evidencias
        evidence_frame = tk.Frame(main_frame, bg=bg_color)
        evidence_frame.pack(fill="x", pady=10)

        # Lista de archivos a subir
        files_to_upload = []

        def add_evidence_file():
            file_paths = filedialog.askopenfilenames(
                title="Seleccionar archivos de evidencia",
                filetypes=[("Todos los archivos", "*.*")]
            )
            if file_paths:
                for file_path in file_paths:
                    files_to_upload.append(file_path)
                    file_name = os.path.basename(file_path)
                    evidence_list.insert("end", file_name)

        def remove_evidence_file():
            selected = evidence_list.curselection()
            if selected:
                index = selected[0]
                files_to_upload.pop(index)
                evidence_list.delete(index)

        # Lista de evidencias
        evidence_label = tk.Label(evidence_frame, text="Archivos de evidencia:", bg=bg_color)
        evidence_label.grid(row=0, column=0, columnspan=2, sticky="w")

        evidence_list = tk.Listbox(evidence_frame, height=4, width=50)
        evidence_list.grid(row=1, column=0, padx=(0, 10))

        # Botones para manejar evidencias
        btn_add = tk.Button(
            evidence_frame,
            text="Agregar",
            command=add_evidence_file,
            width=10
        )
        btn_add.grid(row=1, column=1, sticky="n", pady=2)

        btn_remove = tk.Button(
            evidence_frame,
            text="Quitar",
            command=remove_evidence_file,
            width=10
        )
        btn_remove.grid(row=1, column=1, sticky="s", pady=2)

        # Función para confirmar el cierre
        def confirmar_cierre():
            comentarios = comentarios_text.get("1.0", "end").strip()

            if not comentarios and not files_to_upload:
                if not messagebox.askyesno(
                        "Confirmar",
                        "No ha agregado comentarios ni evidencias. ¿Desea continuar?"
                ):
                    return

            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Obtener información del acuerdo
                cursor.execute(
                    """SELECT acuerdo, responsables, fecha_compromiso, fecha_registro 
                       FROM acuerdos WHERE id_acuerdo = ?""",
                    (id_acuerdo,)
                )
                acuerdo_data = cursor.fetchone()

                if not acuerdo_data:
                    raise Exception("No se encontró el acuerdo")

                acuerdo_text, responsables, fecha_comp, fecha_reg = acuerdo_data

                # Crear estructura de carpetas
                fecha_cierre = datetime.now()
                year_folder = str(fecha_cierre.year)
                month_folder = f"{fecha_cierre.month:02d}"

                # Limpiar nombres de responsables para usar en ruta
                clean_responsables = "_".join(
                    "".join(c if c.isalnum() else "_" for c in name.strip())
                    for name in responsables.split(",")
                )[:50]  # Limitar longitud

                base_path = os.path.join(
                    "evidencias_acuerdos",
                    year_folder,
                    month_folder,
                    clean_responsables,
                    f"Acuerdo_{id_acuerdo}"
                )

                os.makedirs(base_path, exist_ok=True)

                # Copiar archivos de evidencia
                evidence_paths = []
                for file_path in files_to_upload:
                    dest_path = os.path.join(base_path, os.path.basename(file_path))
                    shutil.copy2(file_path, dest_path)
                    evidence_paths.append(dest_path)

                # Generar reporte PDF
                generate_pdf_report(
                    id_acuerdo, acuerdo_text, responsables,
                    fecha_reg, fecha_comp, fecha_cierre,
                    comentarios, files_to_upload, base_path
                )

                # 1. Guardar en historial
                cursor.execute(
                    """INSERT INTO historial_acuerdos 
                    (id_acuerdo, acuerdo, responsables, fecha_compromiso, 
                     fecha_modificacion, usuario_modifico, estatus, comentarios_cierre)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        id_acuerdo,
                        acuerdo_text,
                        responsables,
                        fecha_comp,
                        fecha_cierre.strftime("%Y-%m-%d %H:%M:%S"),
                        getpass.getuser(),
                        "Cerrado",
                        comentarios
                    )
                )

                # 2. Actualizar estatus a "Cerrado"
                cursor.execute(
                    """UPDATE acuerdos 
                    SET estatus = 'Cerrado',
                        fecha_estatus = ?,
                        usuario_registra = ?,
                        comentarios_cierre = ?
                    WHERE id_acuerdo = ?""",
                    (
                        fecha_cierre.strftime("%Y-%m-%d %H:%M:%S"),
                        getpass.getuser(),
                        comentarios,
                        id_acuerdo
                    )
                )

                conn.commit()
                conn.close()

                messagebox.showinfo(
                    "Éxito",
                    f"Acuerdo {id_acuerdo} cerrado correctamente\n"
                    f"Evidencias guardadas en: {base_path}"
                )

                details_window.destroy()
                cargar_acuerdos()

            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cerrar el acuerdo: {str(e)}")

        # Botones de acción
        button_frame = tk.Frame(main_frame, bg=bg_color)
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="Confirmar Cierre",
            command=confirmar_cierre,
            bg="#27ae60",
            fg="white",
            width=15
        ).pack(side="left", padx=10)

        tk.Button(
            button_frame,
            text="Cancelar",
            command=details_window.destroy,
            bg="#e74c3c",
            fg="white",
            width=15
        ).pack(side="right", padx=10)

    def center_window(window):
        """Centra una ventana en la pantalla"""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def generate_pdf_report(id_acuerdo, acuerdo, responsables, fecha_registro,
                            fecha_compromiso, fecha_cierre, comentarios,
                            evidencias, output_folder):
        """Genera un reporte PDF con los detalles del acuerdo"""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)

        # Título
        pdf.cell(0, 10, f"Reporte de Acuerdo #{id_acuerdo}", 0, 1, 'C')
        pdf.ln(10)

        # Información del acuerdo
        pdf.set_font("Arial", '', 12)

        # Duración del acuerdo
        fecha_reg = datetime.strptime(fecha_registro, "%Y-%m-%d %H:%M:%S")
        duracion = (fecha_cierre - fecha_reg).days

        # Función auxiliar para añadir secciones
        def add_section(title, content):
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, f"{title}:", 0, 1)
            pdf.set_font("Arial", '', 12)
            pdf.multi_cell(0, 8, content)
            pdf.ln(5)

        # Datos del acuerdo
        add_section("Acuerdo", acuerdo)
        add_section("Responsables", responsables)

        pdf.cell(90, 8, f"Fecha de registro: {fecha_registro}", 0, 0)
        pdf.cell(90, 8, f"Fecha compromiso: {fecha_compromiso}", 0, 1)
        pdf.cell(90, 8, f"Fecha de cierre: {fecha_cierre.strftime('%Y-%m-%d %H:%M:%S')}", 0, 0)
        pdf.cell(90, 8, f"Duración: {duracion} días", 0, 1)
        pdf.ln(10)

        # Comentarios de cierre
        add_section("Comentarios del cierre", comentarios)

        # Evidencias
        if evidencias:
            add_section("Evidencias adjuntas", "\n".join([f"- {os.path.basename(e)}" for e in evidencias]))

        # Guardar PDF
        pdf_path = os.path.join(output_folder, f"Reporte_Acuerdo_{id_acuerdo}.pdf")
        pdf.output(pdf_path)

        return pdf_path

    # Función para cargar los acuerdos
    def cargar_acuerdos():
        # Limpiar treeview
        for item in tree.get_children():
            tree.delete(item)

        # Construir consulta SQL
        query = """SELECT 
                    id_acuerdo, 
                    acuerdo, 
                    responsables, 
                    fecha_compromiso, 
                    estatus 
                   FROM acuerdos 
                   WHERE estatus != 'Cerrado'"""
        params = []

        # Aplicar filtros
        id_text = id_filter.get()
        if id_text:
            query += " AND id_acuerdo LIKE ?"
            params.append(f"%{id_text}%")

        text_text = text_filter.get()
        if text_text:
            query += " AND acuerdo LIKE ?"
            params.append(f"%{text_text}%")

        resp_text = resp_filter.get()
        if resp_text:
            query += " AND responsables LIKE ?"
            params.append(f"%{resp_text}%")

        fecha_min = fecha_desde.get_date()
        fecha_max = fecha_hasta.get_date()
        if fecha_min:
            query += " AND fecha_compromiso >= ?"
            params.append(fecha_min.strftime("%Y-%m-%d"))
        if fecha_max:
            query += " AND fecha_compromiso <= ?"
            params.append(fecha_max.strftime("%Y-%m-%d"))

        query += " ORDER BY fecha_compromiso DESC"

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)

            for row in cursor.fetchall():
                id_acuerdo = row[0]
                # Insertar fila con datos
                item = tree.insert("", "end", values=(
                    row[0],  # id
                    row[1],  # acuerdo
                    row[2],  # responsables
                    row[3],  # fecha_compromiso
                    row[4],  # estatus
                    "Cerrar"  # acción
                ))

                # Configurar botón de cerrar
                tree.set(item, "accion", "Cerrar")

            conn.close()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los acuerdos: {e}")

    # Configurar evento para botones de cerrar
    def on_tree_click(event):
        region = tree.identify("region", event.x, event.y)
        column = tree.identify_column(event.x)

        if region == "cell" and column == "#6":  # Columna de acción
            item = tree.identify_row(event.y)
            id_acuerdo = tree.item(item, "values")[0]
            cerrar_acuerdo_seleccionado(id_acuerdo)

    tree.bind("<Button-1>", on_tree_click)

    # Botón para cerrar ventana
    button_frame = tk.Frame(close_window, bg=bg_color, pady=10)
    button_frame.pack(fill="x")

    def on_close():
        close_window.destroy()
        parent_window.deiconify()

    tk.Button(
        button_frame,
        text="Regresar al Menú",
        command=on_close,
        bg="#95a5a6",
        fg=text_color,
        font=("Helvetica", 10),
        width=15
    ).pack()

    # Cargar datos iniciales
    fecha_desde.set_date(datetime.now() - timedelta(days=30))  # Últimos 30 días por defecto
    cargar_acuerdos()

    # Configurar comportamiento al cerrar
    close_window.protocol("WM_DELETE_WINDOW", on_close)
    close_window.mainloop()


# sub_menus/cerrar.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import sqlite3
from tkcalendar import DateEntry
# Importar timedelta correctamente
from datetime import timedelta
import os
import shutil
import getpass
from datetime import datetime, timedelta
import sqlite3
from tkinter import filedialog
import os
import shutil
import getpass
from datetime import datetime, timedelta
import sqlite3
from tkinter import filedialog
from fpdf import FPDF  # Para generar PDFs



def cerrar_acuerdo(parent_window, db_path):
    # Ocultar el menú principal
    parent_window.withdraw()

    # Crear ventana de cierre
    close_window = tk.Toplevel()
    close_window.title("Cerrar Acuerdos")
    close_window.geometry("1200x700")

    # Centrar la ventana
    screen_width = close_window.winfo_screenwidth()
    screen_height = close_window.winfo_screenheight()
    x = (screen_width // 2) - (1200 // 2)
    y = (screen_height // 2) - (700 // 2)
    close_window.geometry(f"1200x700+{x}+{y}")

    # Estilos
    bg_color = "#f0f0f0"
    header_color = "#2c3e50"
    button_color = "#3498db"
    button_hover = "#2980b9"
    text_color = "#ecf0f1"
    close_button_color = "#e74c3c"
    close_button_hover = "#c0392b"

    # Header
    header = tk.Frame(close_window, bg=header_color, height=40)
    header.pack(fill="x", side="top")

    tk.Label(
        header,
        text="Cerrar Acuerdos",
        bg=header_color,
        fg=text_color,
        font=("Helvetica", 12, "bold")
    ).pack(side="left", padx=20)

    # Frame para filtros
    filter_frame = tk.Frame(close_window, bg=bg_color, padx=10, pady=10)
    filter_frame.pack(fill="x")

    # Filtro por ID de acuerdo
    tk.Label(filter_frame, text="ID Acuerdo:", bg=bg_color).grid(row=0, column=0, padx=5)
    id_filter = tk.Entry(filter_frame, width=15)
    id_filter.grid(row=0, column=1, padx=5)

    # Filtro por texto en acuerdo
    tk.Label(filter_frame, text="Texto en acuerdo:", bg=bg_color).grid(row=0, column=2, padx=5)
    text_filter = tk.Entry(filter_frame, width=30)
    text_filter.grid(row=0, column=3, padx=5)

    # Filtro por responsable
    tk.Label(filter_frame, text="Responsable:", bg=bg_color).grid(row=0, column=4, padx=5)
    resp_filter = tk.Entry(filter_frame, width=20)
    resp_filter.grid(row=0, column=5, padx=5)

    # Filtro por fecha
    tk.Label(filter_frame, text="Fecha desde:", bg=bg_color).grid(row=1, column=0, padx=5)
    fecha_desde = DateEntry(
        filter_frame,
        width=12,
        background='darkblue',
        foreground='white',
        date_pattern='yyyy-mm-dd'
    )
    fecha_desde.grid(row=1, column=1, padx=5)

    tk.Label(filter_frame, text="hasta:", bg=bg_color).grid(row=1, column=2, padx=5)
    fecha_hasta = DateEntry(
        filter_frame,
        width=12,
        background='darkblue',
        foreground='white',
        date_pattern='yyyy-mm-dd'
    )
    fecha_hasta.grid(row=1, column=3, padx=5)
    fecha_hasta.set_date(datetime.now())

    # Botones de filtrado
    btn_frame = tk.Frame(filter_frame, bg=bg_color)
    btn_frame.grid(row=0, column=6, rowspan=2, padx=10)

    def aplicar_filtros():
        cargar_acuerdos()

    tk.Button(
        btn_frame,
        text="Aplicar Filtros",
        command=aplicar_filtros,
        bg=button_color,
        fg=text_color,
        width=15
    ).pack(pady=2)

    def limpiar_filtros():
        id_filter.delete(0, "end")
        text_filter.delete(0, "end")
        resp_filter.delete(0, "end")
        fecha_desde.set_date(datetime.now() - timedelta(days=30))
        fecha_hasta.set_date(datetime.now())
        cargar_acuerdos()

    tk.Button(
        btn_frame,
        text="Limpiar Filtros",
        command=limpiar_filtros,
        bg="#95a5a6",
        fg=text_color,
        width=15
    ).pack(pady=2)

    # Frame principal para la tabla
    main_frame = tk.Frame(close_window, bg=bg_color)
    main_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # Treeview para mostrar los acuerdos
    tree_frame = tk.Frame(main_frame, bg=bg_color)
    tree_frame.pack(fill="both", expand=True)

    # Scrollbars
    y_scroll = ttk.Scrollbar(tree_frame)
    y_scroll.pack(side="right", fill="y")

    x_scroll = ttk.Scrollbar(tree_frame, orient="horizontal")
    x_scroll.pack(side="bottom", fill="x")

    # Crear el Treeview
    columns = ("id", "acuerdo", "responsables", "fecha_compromiso", "estatus", "accion")
    tree = ttk.Treeview(
        tree_frame,
        columns=columns,
        yscrollcommand=y_scroll.set,
        xscrollcommand=x_scroll.set,
        selectmode="extended",
        height=15
    )

    # Configurar scrollbars
    y_scroll.config(command=tree.yview)
    x_scroll.config(command=tree.xview)

    # Configurar columnas
    tree.heading("id", text="ID Acuerdo")
    tree.heading("acuerdo", text="Acuerdo")
    tree.heading("responsables", text="Responsables")
    tree.heading("fecha_compromiso", text="Fecha Compromiso")
    tree.heading("estatus", text="Estatus")
    tree.heading("accion", text="Acción")

    tree.column("id", width=120, anchor="w")
    tree.column("acuerdo", width=300, anchor="w")
    tree.column("responsables", width=200, anchor="w")
    tree.column("fecha_compromiso", width=120, anchor="center")
    tree.column("estatus", width=100, anchor="center")
    tree.column("accion", width=120, anchor="center")

    tree.pack(fill="both", expand=True)

