from common import *
from acuerdos.center_window import center_window
import sqlite3
import os
import shutil
import getpass
from datetime import datetime
from tkinter import filedialog, messagebox
import tkinter as tk


# Función para cerrar un acuerdo (versión modificada)
def cerrar_acuerdo_seleccionado(id_acuerdo, tree=None, db_path=None):

    print("cerrar 2.py")
    """Cierra un acuerdo con comentarios y evidencias, y actualiza el Treeview"""
    # Ruta base para guardar las evidencias
    from rutas import BASE_EVIDENCIAS
    BASE_EVIDENCIAS = BASE_EVIDENCIAS

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
    comentarios_text.focus_set()  # Esto pondrá el cursor en el widget Text

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
                "".join(word[0] for word in name.strip().split()) for name in responsables.split(",")
            )[:50]  # Limitar longitud

            base_path = os.path.join(
                BASE_EVIDENCIAS,  # Usamos la nueva ruta base
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



            # Generar reporte PDF (esto ya existe en tu código)
            pdf_path = generate_pdf_report(
                id_acuerdo, acuerdo_text, responsables,
                fecha_reg, fecha_comp, fecha_cierre,
                comentarios, files_to_upload, base_path
            )

            # 1. Guardar en historial
            cursor.execute(
                """INSERT INTO historial_acuerdos 
                (id_acuerdo, acuerdo, responsables, fecha_compromiso, 
                 fecha_modificacion, usuario_modifico, estatus, comentarios_cierre,ruta_pdf)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    id_acuerdo,
                    acuerdo_text,
                    responsables,
                    fecha_comp,
                    fecha_cierre.strftime("%Y-%m-%d %H:%M:%S"),
                    getpass.getuser(),
                    "Cerrado",
                    comentarios,
                    pdf_path
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

            # Actualizar el Treeview si se proporcionó
            if tree:
                for item in tree.get_children():
                    if tree.item(item, "values")[0] == str(id_acuerdo):
                        values = list(tree.item(item, "values"))
                        values[4] = "Cerrado"  # Actualizar estatus
                        tree.item(item, values=values)
                        # Actualizar tags para cambiar el estilo si es necesario
                        tree.item(item, tags=('cerrado',))
                        break


            details_window.destroy()

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


def generate_pdf_report(id_acuerdo, acuerdo, responsables, fecha_registro,
                        fecha_compromiso, fecha_cierre, comentarios,
                        evidencias, output_folder):
    """Genera un reporte PDF con los detalles del acuerdo"""
    from fpdf import FPDF
    from datetime import datetime
    import os
    import platform
    import subprocess

    class PDF(FPDF):
        def __init__(self):
            super().__init__()
            self.set_auto_page_break(auto=True, margin=25)
            self.set_margins(20, 30, 20)  # Márgenes izquierdo, superior, derecho
            self.set_title(f"Reporte de Acuerdo #{id_acuerdo}")

        def header(self):
            # Logo en el lado izquierdo
            from rutas import ruta_image
            ruta_image = ruta_image
            self.image(ruta_image, 10, 8, 25)


            # Título del documento en el lado derecho (ajustado para mejor posición)
            self.set_font('Arial', 'B', 10)
            self.set_xy(self.w - 60, 10)  # Posición ajustada
            self.cell(50, 5, "Minuta general", 0, 1, 'R')
            self.set_xy(self.w - 60, 15)  # Posición ajustada debajo del anterior
            self.cell(50, 5, "R-BEA-7.4-02", 0, 1, 'R')

            # Línea decorativa
            self.set_draw_color(0, 80, 180)
            self.line(20, 25, self.w - 20, 25)

            # Espacio después del encabezado
            self.set_y(30)

        def footer(self):
            self.set_y(-25)
            self.set_draw_color(200, 200, 200)
            self.line(20, self.get_y(), self.w - 20, self.get_y())
            self.ln(5)

            self.set_font('Arial', 'I', 8)
            page_width = self.w - 40
            left_text = "Sistema de Gestión"
            center_text = "Versión 3, 26/06/2020"
            right_text = f"Página {self.page_no()} de {{nb}}"

            self.cell(page_width / 3, 5, left_text, 0, 0, 'L')
            self.cell(page_width / 3, 5, center_text, 0, 0, 'C')
            self.cell(page_width / 3, 5, right_text, 0, 0, 'R')
            self.ln(5)

            self.set_font('Arial', 'I', 7)
            self.cell(0, 5,
                      "Este documento es propiedad del Grupo BEA, queda prohibida su reproducción parcial o total sin su previa autorización.",
                      0, 0, 'C')

    # Crear PDF
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Configuración de fuente y colores
    pdf.set_font("Arial", size=12)

    # Título principal con diseño mejorado
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 80, 180)
    pdf.cell(0, 10, f"Reporte de Acuerdo #{id_acuerdo}", 0, 1, 'C')

    # Línea decorativa bajo el título
    pdf.set_draw_color(0, 80, 180)
    pdf.line(pdf.l_margin + 20, pdf.get_y(), pdf.w - pdf.r_margin - 20, pdf.get_y())
    pdf.ln(15)  # Más espacio después del título

    # Información del acuerdo
    def add_section(title, content, bg_color=(0, 80, 180)):
        # Fondo del título
        pdf.set_fill_color(*bg_color)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f" {title}: ", 0, 1, 'L', fill=True)

        # Contenido
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 7, content)
        pdf.ln(8)  # Espacio después de la sección

    # Secciones con diseño mejorado
    add_section("Acuerdo", acuerdo)
    add_section("Responsables", responsables, (50, 50, 50))

    # Fechas en formato tabla mejorada
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(90, 8, "Fecha de registro:", 0, 0, 'L')
    pdf.set_font("Arial", '', 11)
    pdf.cell(90, 8, fecha_registro, 0, 1, 'L')

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(90, 8, "Fecha compromiso:", 0, 0, 'L')
    pdf.set_font("Arial", '', 11)
    pdf.cell(90, 8, fecha_compromiso, 0, 1, 'L')

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(90, 8, "Fecha de cierre:", 0, 0, 'L')
    pdf.set_font("Arial", '', 11)
    pdf.cell(90, 8, fecha_cierre.strftime('%Y-%m-%d %H:%M:%S'), 0, 1, 'L')

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(90, 8, "Duración:", 0, 0, 'L')
    pdf.set_font("Arial", '', 11)
    fecha_reg = datetime.strptime(fecha_registro, "%Y-%m-%d %H:%M:%S")
    duracion = (fecha_cierre - fecha_reg).days
    pdf.cell(90, 8, f"{duracion} días", 0, 1, 'L')
    pdf.ln(10)

    # Comentarios
    add_section("Comentarios del cierre", comentarios, (70, 70, 70))

    # Evidencias con diseño mejorado
    if evidencias:
        pdf.set_fill_color(0, 80, 180)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, " Evidencias adjuntas: ", 0, 1, 'L', fill=True)

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 11)
        for evidencia in evidencias:
            pdf.cell(10, 7, "", 0, 0)
            pdf.cell(5, 7, "*", 0, 0)
            pdf.cell(0, 7, f" {os.path.basename(evidencia)}", 0, 1)
        pdf.ln(5)

    # Guardar PDF
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    pdf_path = os.path.join(output_folder, f"Reporte_Acuerdo_{id_acuerdo}.pdf")
    pdf.output(pdf_path)

    # Abrir carpeta de destino
    try:
        if platform.system() == "Windows":
            os.startfile(output_folder)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", output_folder])
        else:
            subprocess.Popen(["xdg-open", output_folder])
    except Exception as e:
        print(f"No se pudo abrir la carpeta: {e}")

    return pdf_path