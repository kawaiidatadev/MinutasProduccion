from common import *

def exportar_excel(db_path):
    """Función para exportar los acuerdos a un archivo Excel"""
    def perform_export():
        try:
            # Conectar a la base de datos
            conn = sqlite3.connect(db_path)

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

            # Leer datos en un DataFrame
            df = pd.read_sql_query(query, conn)

            # Cerrar conexión
            conn.close()

            # Verificar si hay datos
            if df.empty:
                messagebox.showwarning("Sin datos", "No hay datos para exportar con los criterios seleccionados.")
                return


            # Reorganizar las columnas para que el historial esté al final
            cols = [col for col in df.columns if col != 'historial'] + ['historial']
            df = df[cols]

            # Reemplazar None o NaN en historial con texto vacío
            df['historial'] = df['historial'].fillna('Sin historial registrado')

            # Crear nombre de archivo con fecha y hora
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"acuerdos_{timestamp}.xlsx"

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
                    if os.path.exists(filepath):
                        os.remove(filepath)

                    time.sleep(1)
                    abrir_carpeta_destino(processed_path)

            except Exception as e:
                messagebox.showerror(
                    "Error en procesamiento",
                    f"Se exportó el archivo pero hubo un error al procesarlo:\n{str(e)}\n\nArchivo original: {filepath}"
                )

            # # Cerrar ventana
            # export_window.destroy()

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

    perform_export()