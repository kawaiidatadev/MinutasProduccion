# mostrar_dashboard.py
import tkinter as tk
from tkinter import ttk, font, messagebox
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import calendar
from PIL import Image, ImageTk


def mostrar_dashboard(parent, db_path):
    """Ventana principal del Dashboard con gráficos interactivos y filtros"""

    dashboard = tk.Toplevel(parent)
    dashboard.title("Dashboard de Acuerdos - Análisis Avanzado")
    dashboard.geometry("1300x750")
    dashboard.state('zoomed')

    # --- Estilos y Fuentes ---
    bg_color = "#f5f7fa"
    card_bg = "#ffffff"
    style = ttk.Style()
    style.configure("TFrame", background=bg_color)
    style.configure("TLabel", background=bg_color, font=("Helvetica", 10))
    style.configure("TButton", font=("Helvetica", 10))
    style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))

    # --- Funciones de Datos ---
    def cargar_datos(filtro_estatus=None, filtro_mes=None, filtro_responsable=None):
        """Carga datos desde SQLite con filtros aplicables"""
        conn = sqlite3.connect(db_path)

        # Consulta base con todas las columnas necesarias
        query = """SELECT id_acuerdo, acuerdo, estatus, responsables, 
                  fecha_compromiso, fecha_registro FROM acuerdos"""
        conditions = []

        # Manejo de filtros
        if filtro_estatus and filtro_estatus != "Todos":
            conditions.append(f"estatus = '{filtro_estatus}'")

        if filtro_mes and filtro_mes != "Todos":
            try:
                month_num = list(calendar.month_name).index(filtro_mes)
                conditions.append(f"strftime('%m', fecha_compromiso) = '{month_num:02d}'")
            except ValueError:
                print(f"Mes no válido: {filtro_mes}")

        if filtro_responsable and filtro_responsable.strip():
            conditions.append(f"responsables LIKE '%{filtro_responsable}%'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Debug: imprimir la consulta SQL
        print("Ejecutando consulta:", query)

        try:
            df = pd.read_sql_query(query, conn)

            # Debug: verificar datos obtenidos
            print(f"Datos obtenidos: {len(df)} registros")
            if not df.empty:
                print("Primer registro:", df.iloc[0].to_dict())

            # Procesamiento adicional
            if not df.empty:
                now = pd.Timestamp.now()
                df['fecha_compromiso'] = pd.to_datetime(df['fecha_compromiso'], errors='coerce')
                df['dias_atraso'] = (now - df['fecha_compromiso']).dt.days
                df['dias_atraso'] = df['dias_atraso'].apply(lambda x: x if x > 0 and pd.notna(x) else 0)

            return df

        except Exception as e:
            print(f"Error al cargar datos: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    # --- Componentes del Dashboard ---
    def crear_tarjeta_metrica(contenedor, titulo, valor, color):
        """Crea una tarjeta de métrica visual"""
        frame = ttk.Frame(contenedor, style="Card.TFrame", padding=10, width=200, height=100)

        lbl_titulo = ttk.Label(frame, text=titulo, style="CardTitle.TLabel")
        lbl_titulo.pack(anchor="w")

        lbl_valor = ttk.Label(frame, text=valor, style="CardValue.TLabel", foreground=color)
        lbl_valor.pack(anchor="w", pady=5)

        return frame

    def actualizar_graficos():
        """Actualiza todos los componentes del dashboard"""
        try:
            df = cargar_datos(
                filtro_estatus=combo_estatus.get(),
                filtro_mes=combo_mes.get(),
                filtro_responsable=entry_responsable.get()
            )

            # Debug: Mostrar consulta y cantidad de datos
            print(f"Datos cargados: {len(df)} registros")

            # Actualizar componentes visuales
            actualizar_tarjetas(df)
            actualizar_grafico_barras(df)
            actualizar_grafico_torta(df)
            actualizar_grafico_evolucion(df)
            actualizar_tabla(df)

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error, no hay registros...")
            print(f"Error completo: {e}")

    def actualizar_tarjetas(df):
        """Actualiza las tarjetas de métricas"""
        for widget in frame_tarjetas.winfo_children():
            widget.destroy()

        total_acuerdos = len(df)
        atrasados = len(df[df['dias_atraso'] > 0])
        cerrados = len(df[df['estatus'] == 'Cerrado'])
        cumplimiento = f"{(cerrados / total_acuerdos * 100):.1f}%" if total_acuerdos > 0 else "0%"

        crear_tarjeta_metrica(frame_tarjetas, "📋 Total Acuerdos", total_acuerdos, "#3498db")
        crear_tarjeta_metrica(frame_tarjetas, "⏰ Atrasados", atrasados, "#e74c3c")
        crear_tarjeta_metrica(frame_tarjetas, "✅ Cerrados", cerrados, "#2ecc71")
        crear_tarjeta_metrica(frame_tarjetas, "📈 % Cumplimiento", cumplimiento, "#9b59b6")

    def actualizar_grafico_barras(df):
        """Gráfico de barras por estatus"""
        fig, ax = plt.subplots(figsize=(6, 3))
        counts = df['estatus'].value_counts()

        if not counts.empty:
            counts.plot(kind='bar', ax=ax, color=['#3498db', '#2ecc71', '#e74c3c'])
            ax.set_title("Acuerdos por Estatus")
        else:
            ax.text(0.5, 0.5, 'No hay datos', ha='center', va='center')
            ax.set_title("Acuerdos por Estatus (sin datos)")

        for widget in frame_grafico_barras.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=frame_grafico_barras)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    def actualizar_grafico_torta(df):
        """Gráfico de torta de responsables"""
        fig, ax = plt.subplots(figsize=(6, 3))
        responsables = df['responsables'].str.split(',').explode().str.strip()
        counts = responsables.value_counts().head(5)

        if not counts.empty:
            counts.plot(kind='pie', ax=ax, autopct='%1.1f%%')
            ax.set_title("Top 5 Responsables")
        else:
            ax.text(0.5, 0.5, 'No hay datos', ha='center', va='center')
            ax.set_title("Responsables (sin datos)")

        for widget in frame_grafico_torta.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=frame_grafico_torta)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    def actualizar_grafico_evolucion(df):
        """Gráfico de evolución temporal"""
        fig, ax = plt.subplots(figsize=(8, 3))
        df['fecha_registro'] = pd.to_datetime(df['fecha_registro'])
        df_resumen = df.groupby(df['fecha_registro'].dt.to_period('M')).size()

        if not df_resumen.empty:
            df_resumen.plot(ax=ax, marker='o', color='#9b59b6')
            ax.set_title("Evolución Mensual de Acuerdos")
        else:
            ax.text(0.5, 0.5, 'No hay datos', ha='center', va='center')
            ax.set_title("Evolución (sin datos)")

        for widget in frame_grafico_evolucion.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=frame_grafico_evolucion)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    def actualizar_tabla(df):
        """Actualiza la tabla con los acuerdos"""
        for row in tabla.get_children():
            tabla.delete(row)

        if df.empty:
            # Mostrar mensaje cuando no hay datos
            tabla.insert("", "end", values=("No hay datos con los filtros actuales", "", "", "", "", ""))
            return

        try:
            # Ordenar por días de atraso (mayor primero)
            df_sorted = df.sort_values('dias_atraso', ascending=False)

            # Insertar datos en la tabla
            for _, row in df_sorted.head(20).iterrows():  # Mostrar solo los primeros 20
                estado = "⚠️ Atrasado" if row['dias_atraso'] > 0 else "✅ Al día"
                acuerdo = str(row['acuerdo'])[:50] + "..." if len(str(row['acuerdo'])) > 50 else row['acuerdo']

                # Manejar posibles valores nulos en fecha_compromiso
                fecha_comp = row['fecha_compromiso']
                if pd.isna(fecha_comp):
                    fecha_str = ""
                elif isinstance(fecha_comp, str):
                    fecha_str = fecha_comp
                else:
                    fecha_str = fecha_comp.strftime('%Y-%m-%d')

                tabla.insert("", "end", values=(
                    row.get('id_acuerdo', ''),
                    acuerdo,
                    row.get('responsables', ''),
                    fecha_str,
                    estado,
                    f"{row['dias_atraso']} días" if row['dias_atraso'] > 0 else "-"
                ))
        except Exception as e:
            print(f"Error al actualizar tabla: {e}")
            tabla.insert("", "end", values=("Error al cargar datos", "", "", "", "", ""))

    frame_filtros = ttk.Frame(dashboard, padding=10)
    frame_filtros.pack(fill="x", pady=5)

    ttk.Label(frame_filtros, text="Filtros:").grid(row=0, column=0, padx=5)

    # Filtro por Estatus
    ttk.Label(frame_filtros, text="Estatus:").grid(row=0, column=1, padx=5)
    combo_estatus = ttk.Combobox(frame_filtros, values=["Todos", "Activo", "Editado", "Cerrado"], state="readonly")
    combo_estatus.grid(row=0, column=2, padx=5)
    combo_estatus.set("Todos")

    # Filtro por Mes
    ttk.Label(frame_filtros, text="Mes:").grid(row=0, column=3, padx=5)
    combo_mes = ttk.Combobox(frame_filtros, values=["Todos"] + list(calendar.month_name[1:]), state="readonly")
    combo_mes.grid(row=0, column=4, padx=5)
    combo_mes.set("Todos")

    # Filtro por Responsable
    ttk.Label(frame_filtros, text="Responsable:").grid(row=0, column=5, padx=5)
    entry_responsable = ttk.Entry(frame_filtros)
    entry_responsable.grid(row=0, column=6, padx=5)

    # Botón Aplicar Filtros
    btn_aplicar = ttk.Button(frame_filtros, text="Aplicar Filtros", command=actualizar_graficos)
    btn_aplicar.grid(row=0, column=7, padx=10)

    # Frame de Tarjetas
    frame_tarjetas = ttk.Frame(dashboard)
    frame_tarjetas.pack(fill="x", pady=10)
    for i in range(4):  # 4 tarjetas
        frame_tarjetas.columnconfigure(i, weight=1)

    # Frames de Gráficos
    frame_graficos = ttk.Frame(dashboard)
    frame_graficos.pack(fill="both", expand=True)

    frame_grafico_barras = ttk.Frame(frame_graficos)
    frame_grafico_barras.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

    frame_grafico_torta = ttk.Frame(frame_graficos)
    frame_grafico_torta.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

    frame_grafico_evolucion = ttk.Frame(frame_graficos)
    frame_grafico_evolucion.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

    # Configuración de Grid para gráficos
    frame_graficos.grid_columnconfigure(0, weight=1)
    frame_graficos.grid_columnconfigure(1, weight=1)
    frame_graficos.grid_rowconfigure(0, weight=1)
    frame_graficos.grid_rowconfigure(1, weight=1)

    # Frame para la tabla
    frame_tabla = ttk.Frame(dashboard)
    frame_tabla.pack(fill="both", expand=True, pady=10)

    # Crear tabla
    columns = ("ID", "Acuerdo", "Responsables", "Fecha Compromiso", "Estado", "Días Atraso")
    tabla = ttk.Treeview(frame_tabla, columns=columns, show="headings", height=8)

    # Configurar columnas
    for col in columns:
        tabla.heading(col, text=col)
        tabla.column(col, width=100, anchor="w")

    # Ajustar anchos específicos
    tabla.column("Acuerdo", width=250)
    tabla.column("Responsables", width=150)

    # Scrollbar
    scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tabla.pack(side="left", fill="both", expand=True)

    # Estilos personalizados
    style.configure("Card.TFrame", background=card_bg, borderwidth=1, relief="solid")
    style.configure("CardTitle.TLabel", font=("Helvetica", 9), foreground="#7f8c8d")
    style.configure("CardValue.TLabel", font=("Helvetica", 18, "bold"))
    style.configure("Treeview", font=('Helvetica', 9), rowheight=25)
    style.map("Treeview", background=[('selected', '#347083')])

    # Carga inicial
    actualizar_graficos()

