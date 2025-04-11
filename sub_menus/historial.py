# sub_menus/historial.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import sqlite3
from difflib import SequenceMatcher


class HistorialAcuerdos:
    def __init__(self, parent_window, db_path):
        self.parent = parent_window
        self.db_path = db_path

        # Definir colores para resaltar cambios PRIMERO
        self.color_added = '#e6ffe6'  # Verde claro para adiciones
        self.color_removed = '#ffe6e6'  # Rojo claro para eliminaciones
        self.color_changed = '#ffffe6'  # Amarillo claro para cambios

        self.current_version = None
        self.previous_versions = []
        self.create_ui()
        self.load_acuerdos()
        self.center_window()

        self.setup_bindings()


    def setup_bindings(self):
        """Configura los eventos del Treeview"""
        self.acuerdos_tree.bind("<Double-1>", self.on_double_click)



    def center_window(self):
        """Centra la ventana en la pantalla"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def create_ui(self):
        # Crear ventana principal con estilo consistente
        self.window = tk.Toplevel(self.parent)
        self.window.title("Historial Completo de Acuerdos")
        self.window.geometry("1200x800")
        self.window.configure(bg='#f0f0f0')

        # Estilo para los frames
        style = ttk.Style()
        style.configure('Custom.TFrame', background='#f0f0f0')

        # Frame para filtros
        filter_frame = ttk.Frame(self.window, padding=(10, 10, 10, 10), style='Custom.TFrame')
        filter_frame.pack(fill="x")

        # Filtro por ID de acuerdo
        ttk.Label(filter_frame, text="ID Acuerdo:", background='#f0f0f0').grid(row=0, column=0, sticky="w")
        self.id_filter = ttk.Entry(filter_frame, width=15)
        self.id_filter.grid(row=0, column=1, sticky="w", padx=5)

        # Filtro por texto en acuerdo
        ttk.Label(filter_frame, text="Texto en acuerdo:", background='#f0f0f0').grid(row=0, column=2, sticky="w")
        self.text_filter = ttk.Entry(filter_frame, width=30)
        self.text_filter.grid(row=0, column=3, sticky="w", padx=5)

        # Filtro por responsable
        ttk.Label(filter_frame, text="Responsable:", background='#f0f0f0').grid(row=0, column=4, sticky="w")
        self.resp_filter = ttk.Entry(filter_frame, width=20)
        self.resp_filter.grid(row=0, column=5, sticky="w", padx=5)

        # Filtro por fecha
        ttk.Label(filter_frame, text="Fecha entre:", background='#f0f0f0').grid(row=1, column=0, sticky="w")
        self.date_from = ttk.Entry(filter_frame, width=12)
        self.date_from.grid(row=1, column=1, sticky="w", padx=5)
        ttk.Label(filter_frame, text="y", background='#f0f0f0').grid(row=1, column=2)
        self.date_to = ttk.Entry(filter_frame, width=12)
        self.date_to.grid(row=1, column=3, sticky="w", padx=5)

        # Filtro por estatus
        ttk.Label(filter_frame, text="Estatus:", background='#f0f0f0').grid(row=1, column=4, sticky="w")
        self.status_filter = ttk.Combobox(filter_frame, values=["Todos", "Activo", "Editado", "Cerrado"],
                                          state="readonly")
        self.status_filter.set("Todos")
        self.status_filter.grid(row=1, column=5, sticky="w", padx=5)

        # Botones de filtrado con estilo consistente
        btn_frame = ttk.Frame(filter_frame, style='Custom.TFrame')
        btn_frame.grid(row=0, column=6, rowspan=2, padx=10)

        ttk.Button(btn_frame, text="Filtrar", command=self.apply_filters, width=10).pack(pady=2)
        ttk.Button(btn_frame, text="Limpiar", command=self.clear_filters, width=10).pack(pady=2)

        # Treeview para acuerdos principales
        tree_frame = ttk.Frame(self.window, style='Custom.TFrame')
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.acuerdos_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "acuerdo", "responsables", "fecha", "estatus", "fecha_compromiso"),
            show="headings",
            height=8
        )

        # Configurar columnas
        self.acuerdos_tree.heading("id", text="ID Acuerdo", command=lambda: self.sort_tree("id"))
        self.acuerdos_tree.heading("acuerdo", text="Acuerdo", command=lambda: self.sort_tree("acuerdo"))
        self.acuerdos_tree.heading("responsables", text="Responsables", command=lambda: self.sort_tree("responsables"))
        self.acuerdos_tree.heading("fecha", text="Última Modificación", command=lambda: self.sort_tree("fecha"))
        self.acuerdos_tree.heading("estatus", text="Estatus", command=lambda: self.sort_tree("estatus"))
        self.acuerdos_tree.heading("fecha_compromiso", text="Fecha Compromiso",
                                   command=lambda: self.sort_tree("fecha_compromiso"))


        self.acuerdos_tree.column("id", width=80, anchor="center")
        self.acuerdos_tree.column("acuerdo", width=250)
        self.acuerdos_tree.column("responsables", width=150)
        self.acuerdos_tree.column("fecha", width=150, anchor="center")
        self.acuerdos_tree.column("estatus", width=80, anchor="center")
        self.acuerdos_tree.column("fecha_compromiso", width=120, anchor="center")

        self.acuerdos_tree.pack(fill="x", pady=(0, 10))

        # Separador
        ttk.Separator(tree_frame, orient="horizontal").pack(fill="x", pady=5)

        # Label para historial
        self.historial_label = ttk.Label(
            tree_frame,
            text="Historial de modificaciones:",
            font=("Helvetica", 10, "bold"),
            background='#f0f0f0'
        )
        self.historial_label.pack(anchor="w")

        # Treeview para historial con tags para resaltar
        self.historial_tree = ttk.Treeview(
            tree_frame,
            columns=("fecha", "usuario", "estatus", "acuerdo", "responsables", "fecha_compromiso"),
            show="headings"
        )

        #  Configurar tags para resaltado - AHORA LOS COLORES ESTÁN DEFINIDOS
        self.historial_tree.tag_configure('added', background=self.color_added)
        self.historial_tree.tag_configure('removed', background=self.color_removed)
        self.historial_tree.tag_configure('changed', background=self.color_changed)

        # Configurar columnas
        self.historial_tree.heading("fecha", text="Fecha Modificación")
        self.historial_tree.heading("usuario", text="Usuario")
        self.historial_tree.heading("estatus", text="Estatus")
        self.historial_tree.heading("acuerdo", text="Acuerdo")
        self.historial_tree.heading("responsables", text="Responsables")
        self.historial_tree.heading("fecha_compromiso", text="Fecha Compromiso")

        self.historial_tree.column("fecha", width=150, anchor="center")
        self.historial_tree.column("usuario", width=100, anchor="center")
        self.historial_tree.column("estatus", width=80, anchor="center")
        self.historial_tree.column("acuerdo", width=250)
        self.historial_tree.column("responsables", width=150)
        self.historial_tree.column("fecha_compromiso", width=120, anchor="center")

        self.historial_tree.pack(fill="both", expand=True)

        # Configurar eventos
        self.acuerdos_tree.bind("<<TreeviewSelect>>", self.load_historial)
        self.historial_tree.bind("<Button-1>", self.on_historial_click)

    def on_historial_click(self, event):
        """Manejador de clic en el historial para mostrar diferencias"""
        item = self.historial_tree.identify_row(event.y)
        if not item:
            return

        # Obtener índice del item seleccionado
        items = self.historial_tree.get_children()
        try:
            index = items.index(item)
            self.highlight_changes(index)
        except ValueError:
            pass

    def highlight_changes(self, selected_index):
        """Resalta los cambios entre la versión seleccionada y la anterior"""
        # Limpiar tags anteriores
        for item in self.historial_tree.get_children():
            for col in self.historial_tree["columns"]:
                self.historial_tree.set(item, col, self.historial_tree.set(item, col))

        # No hay nada que comparar si solo hay un item
        if len(self.historial_tree.get_children()) <= 1:
            return

        # Obtener items a comparar
        items = self.historial_tree.get_children()
        current_item = items[selected_index]
        previous_item = items[selected_index + 1] if selected_index + 1 < len(items) else None

        if not previous_item:
            return

        # Comparar cada campo
        for col in self.historial_tree["columns"]:
            current_val = self.historial_tree.set(current_item, col)
            previous_val = self.historial_tree.set(previous_item, col)

            if current_val != previous_val:
                # Determinar tipo de cambio
                if not previous_val and current_val:
                    # Nuevo valor (adición)
                    self.historial_tree.set(current_item, col, current_val)
                    self.historial_tree.item(current_item, tags=('added',))
                elif previous_val and not current_val:
                    # Valor eliminado
                    self.historial_tree.set(current_item, col, current_val)
                    self.historial_tree.item(current_item, tags=('removed',))
                else:
                    # Valor modificado
                    self.historial_tree.set(current_item, col, current_val)
                    self.historial_tree.item(current_item, tags=('changed',))

                    # Opcional: Mostrar diferencias de texto para acuerdo y responsables
                    if col in ("acuerdo", "responsables"):
                        diff_text = self.get_text_diff(previous_val, current_val)
                        self.historial_tree.set(current_item, col, diff_text)

    def get_text_diff(self, old_text, new_text):
        """Genera una representación de las diferencias entre dos textos"""
        matcher = SequenceMatcher(None, old_text, new_text)
        diff_text = ""

        for opcode in matcher.get_opcodes():
            op, i1, i2, j1, j2 = opcode
            if op == 'equal':
                diff_text += new_text[j1:j2]
            elif op == 'insert':
                diff_text += f'[+{new_text[j1:j2]}]'
            elif op == 'delete':
                diff_text += f'[-{old_text[i1:i2]}]'
            elif op == 'replace':
                diff_text += f'[-{old_text[i1:i2]}][+{new_text[j1:j2]}]'

        return diff_text

    def load_acuerdos(self):
        """Carga los acuerdos principales según los filtros"""
        # Limpiar treeview
        for item in self.acuerdos_tree.get_children():
            self.acuerdos_tree.delete(item)

        # Construir consulta SQL con filtros
        query = """SELECT 
                    id_acuerdo, 
                    acuerdo, 
                    responsables, 
                    fecha_estatus, 
                    estatus,
                    fecha_compromiso
                   FROM acuerdos 
                   WHERE 1=1"""
        params = []

        # Aplicar filtros
        id_filter = self.id_filter.get()
        if id_filter:
            query += " AND id_acuerdo LIKE ?"
            params.append(f"%{id_filter}%")

        text_filter = self.text_filter.get()
        if text_filter:
            query += " AND acuerdo LIKE ?"
            params.append(f"%{text_filter}%")

        resp_filter = self.resp_filter.get()
        if resp_filter:
            query += " AND responsables LIKE ?"
            params.append(f"%{resp_filter}%")

        date_from = self.date_from.get()
        date_to = self.date_to.get()
        if date_from:
            query += " AND fecha_estatus >= ?"
            params.append(date_from)
        if date_to:
            query += " AND fecha_estatus <= ?"
            params.append(date_to)

        status = self.status_filter.get()
        if status != "Todos":
            query += " AND estatus = ?"
            params.append(status)

        query += " ORDER BY fecha_estatus DESC"

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)

            for row in cursor.fetchall():
                # Formatear fecha compromiso para mejor visualización
                formatted_row = list(row)
                if formatted_row[5]:  # Si hay fecha_compromiso
                    formatted_row[5] = datetime.strptime(formatted_row[5], "%Y-%m-%d").strftime("%d/%m/%Y")
                self.acuerdos_tree.insert("", "end", values=formatted_row)

            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los acuerdos: {e}")

    def load_historial(self, event):
        """Carga el historial del acuerdo seleccionado"""
        selected = self.acuerdos_tree.focus()
        if not selected:
            return

        # Obtener ID del acuerdo seleccionado
        id_acuerdo = self.acuerdos_tree.item(selected)["values"][0]

        # Actualizar label
        self.historial_label.config(text=f"Historial de modificaciones - Acuerdo {id_acuerdo}")

        # Limpiar treeview de historial
        for item in self.historial_tree.get_children():
            self.historial_tree.delete(item)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Obtener versión actual
            cursor.execute(
                """SELECT 
                    fecha_estatus, 
                    usuario_registra, 
                    estatus,
                    acuerdo,
                    responsables,
                    fecha_compromiso
                   FROM acuerdos 
                   WHERE id_acuerdo = ?""",
                (id_acuerdo,)
            )
            current = cursor.fetchone()
            if current:
                # Formatear fecha compromiso
                formatted_current = list(current)
                if formatted_current[5]:
                    formatted_current[5] = datetime.strptime(formatted_current[5], "%Y-%m-%d").strftime("%d/%m/%Y")
                self.historial_tree.insert("", "end", values=formatted_current, tags=('current',))

            # Obtener historial
            cursor.execute(
                """SELECT 
                    fecha_modificacion, 
                    usuario_modifico, 
                    estatus,
                    acuerdo,
                    responsables,
                    fecha_compromiso
                   FROM historial_acuerdos 
                   WHERE id_acuerdo = ? 
                   ORDER BY fecha_modificacion DESC""",
                (id_acuerdo,)
            )

            for row in cursor.fetchall():
                # Formatear fechas para mejor visualización
                formatted_row = list(row)
                # Formatear fecha de modificación
                formatted_row[0] = datetime.strptime(formatted_row[0], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                # Formatear fecha compromiso si existe
                if formatted_row[5]:
                    formatted_row[5] = datetime.strptime(formatted_row[5], "%Y-%m-%d").strftime("%d/%m/%Y")
                self.historial_tree.insert("", "end", values=formatted_row)

            conn.close()

            # Resaltar diferencias automáticamente para la primera versión
            if self.historial_tree.get_children():
                self.highlight_changes(0)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el historial: {e}")

    def apply_filters(self):
        """Aplica los filtros y recarga los acuerdos"""
        self.load_acuerdos()

    def clear_filters(self):
        """Limpia todos los filtros"""
        self.id_filter.delete(0, "end")
        self.text_filter.delete(0, "end")
        self.resp_filter.delete(0, "end")
        self.date_from.delete(0, "end")
        self.date_to.delete(0, "end")
        self.status_filter.set("Todos")
        self.load_acuerdos()

    def sort_tree(self, column):
        """Ordena el treeview por la columna seleccionada"""
        items = [(self.acuerdos_tree.set(child, column), child)
                 for child in self.acuerdos_tree.get_children("")]

        try:
            # Intentar ordenar como fecha si la columna es fecha
            if column in ("fecha", "fecha_compromiso"):
                items.sort(key=lambda x: datetime.strptime(x[0], "%d/%m/%Y") if x[0] else "", reverse=True)
            elif column == "id":
                items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0)
            else:
                items.sort()
        except:
            items.sort()

        for index, (val, child) in enumerate(items):
            self.acuerdos_tree.move(child, "", index)




def mostrar_historial(parent_window, db_path):
    HistorialAcuerdos(parent_window, db_path)
    # Después de crear la instancia:
    historial = HistorialAcuerdos(parent_window, db_path)
    historial.acuerdos_tree.bind("<Double-1>",
                                 lambda e: on_double_click(e,
                                                           historial.acuerdos_tree,
                                                           historial.historial_tree,
                                                           historial.historial_label,
                                                           db_path
                                                           )
                                 )