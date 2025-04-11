import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import pandas as pd
from datetime import datetime
import os
import sys
import subprocess


def exportar_a_excel(parent, db_path):
    """Función para exportar los acuerdos a un archivo Excel"""

    # Crear ventana emergente
    export_window = tk.Toplevel(parent)
    export_window.title("Exportar Acuerdos a Excel")
    export_window.transient(parent)
    export_window.grab_set()

    # Centrar la ventana
    window_width = 500
    window_height = 300
    screen_width = export_window.winfo_screenwidth()
    screen_height = export_window.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    export_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Estilos
    bg_color = "#f5f7fa"
    header_color = "#2c3e50"
    button_color = "#3498db"
    button_hover = "#2980b9"
    text_color = "#ecf0f1"

    export_window.configure(bg=bg_color)

    # Frame principal
    main_frame = tk.Frame(export_window, bg=bg_color)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Título
    tk.Label(
        main_frame,
        text="Exportar Acuerdos a Excel",
        bg=bg_color,
        fg=header_color,
        font=("Helvetica", 14, "bold")
    ).pack(pady=(0, 20))

    # Opciones de exportación
    options_frame = tk.Frame(main_frame, bg=bg_color)
    options_frame.pack(fill="x", pady=10)

    # Variable para el tipo de exportación
    export_type = tk.StringVar(value="all")

    # Radio buttons
    tk.Radiobutton(
        options_frame,
        text="Todos los acuerdos",
        variable=export_type,
        value="all",
        bg=bg_color,
        activebackground=bg_color
    ).pack(anchor="w", pady=5)

    tk.Radiobutton(
        options_frame,
        text="Solo acuerdos activos",
        variable=export_type,
        value="active",
        bg=bg_color,
        activebackground=bg_color
    ).pack(anchor="w", pady=5)

    tk.Radiobutton(
        options_frame,
        text="Solo acuerdos cerrados",
        variable=export_type,
        value="closed",
        bg=bg_color,
        activebackground=bg_color
    ).pack(anchor="w", pady=5)

    # Frame para botones
    button_frame = tk.Frame(main_frame, bg=bg_color)
    button_frame.pack(fill="x", pady=20)

    def perform_export():
        try:
            # Conectar a la base de datos
            conn = sqlite3.connect(db_path)

            # Determinar la consulta según la selección
            if export_type.get() == "all":
                # Consulta para acuerdos con información de historial
                query = """
                               SELECT 
                    a.id_acuerdo,
                    a.acuerdo,
                    a.responsables,
                    a.fecha_compromiso,
                    a.fecha_registro,
                    a.usuario_registra,
                    a.estatus,
                    a.fecha_estatus,
                    a.comentarios_cierre,
                    GROUP_CONCAT(h.fecha_modificacion || ' - ' || h.estatus, '\n') AS historial,
                    CAST((JULIANDAY(a.fecha_estatus) - JULIANDAY(a.fecha_compromiso)) AS INTEGER) AS diferencia_dias
                FROM 
                    acuerdos a
                LEFT JOIN 
                    historial_acuerdos h ON a.id_acuerdo = h.id_acuerdo
                GROUP BY 
                    a.id_acuerdo
                ORDER BY 
                    a.id_acuerdo;
                """
                filename_suffix = "todos"
            elif export_type.get() == "active":
                query = "SELECT * FROM acuerdos WHERE estatus IN ('Activo', 'Editado')"
                filename_suffix = "activos"
            else:
                query = "SELECT * FROM acuerdos WHERE estatus = 'Cerrado'"
                filename_suffix = "cerrados"

            # Leer datos en un DataFrame
            df = pd.read_sql_query(query, conn)

            # Cerrar conexión
            conn.close()

            # Verificar si hay datos
            if df.empty:
                messagebox.showwarning("Sin datos", "No hay datos para exportar con los criterios seleccionados.")
                return

            # Si es la opción "todos", procesar el historial para mejor visualización
            if export_type.get() == "all":
                # Reorganizar las columnas para que el historial esté al final
                cols = [col for col in df.columns if col != 'historial'] + ['historial']
                df = df[cols]

                # Reemplazar None o NaN en historial con texto vacío
                df['historial'] = df['historial'].fillna('Sin historial registrado')

            # Crear nombre de archivo con fecha y hora
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"acuerdos_{filename_suffix}_{timestamp}.xlsx"

            # Ruta de destino (Escritorio del usuario)
            desktop_path = os.path.join(os.path.expanduser("~"), "Downloads")
            filepath = os.path.join(desktop_path, filename)

            # Primero exportar el archivo original
            df.to_excel(filepath, index=False, engine='openpyxl')

            # Llamar a la función de procesamiento
            from sub_menus.procesar_excel import excel_pr
            try:
                processed_path = excel_pr(filepath)

                # Mostrar mensaje con la ruta del archivo procesado
                response = messagebox.askyesno(
                    "Exportación exitosa",
                    f"Los datos han sido exportados y procesados correctamente a:\n{processed_path}\n\n¿Desea abrir la carpeta de destino?"
                )

                if response:
                    abrir_carpeta_destino(processed_path)

            except Exception as e:
                messagebox.showerror(
                    "Error en procesamiento",
                    f"Se exportó el archivo pero hubo un error al procesarlo:\n{str(e)}\n\nArchivo original: {filepath}"
                )

            # Cerrar ventana
            export_window.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error en exportación",
                f"Ocurrió un error al exportar los datos:\n{str(e)}"
            )

    def abrir_carpeta_destino(filepath):
        """Abre la carpeta contenedora del archivo en el explorador de archivos del sistema"""
        try:
            # Obtener la ruta del directorio
            folder_path = os.path.dirname(filepath)

            # Abrir la carpeta según el sistema operativo
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)
            elif os.name == 'posix':  # macOS o Linux
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', folder_path])
                else:  # Linux
                    subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir la carpeta:\n{str(e)}"
            )

    # Botón Exportar
    export_btn = tk.Button(
        button_frame,
        text="Exportar",
        command=perform_export,
        bg=button_color,
        fg=text_color,
        activebackground=button_hover,
        activeforeground=text_color,
        relief="flat",
        padx=20,
        pady=5
    )
    export_btn.pack(side="left", padx=10)

    # Botón Cancelar
    cancel_btn = tk.Button(
        button_frame,
        text="Cancelar",
        command=export_window.destroy,
        bg="#95a5a6",
        fg=text_color,
        activebackground="#7f8c8d",
        activeforeground=text_color,
        relief="flat",
        padx=20,
        pady=5
    )
    cancel_btn.pack(side="right", padx=10)

    # Efectos hover
    export_btn.bind("<Enter>", lambda e: export_btn.config(bg=button_hover))
    export_btn.bind("<Leave>", lambda e: export_btn.config(bg=button_color))
    cancel_btn.bind("<Enter>", lambda e: cancel_btn.config(bg="#7f8c8d"))
    cancel_btn.bind("<Leave>", lambda e: cancel_btn.config(bg="#95a5a6"))