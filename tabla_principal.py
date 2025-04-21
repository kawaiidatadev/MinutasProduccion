from common import *


def mostrar_tabla_acuerdos(parent, db_path):
    """Muestra una tabla con los acuerdos activos ordenados por fecha compromiso"""
    try:
        # Frame para contener la tabla y su título
        frame_contenedor = tk.Frame(parent, bg="#f5f7fa")
        frame_contenedor.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Título de la sección
        lbl_titulo = tk.Label(
            frame_contenedor,
            text="Acuerdos Activos (ordenados por proximidad a fecha compromiso)",
            bg="#f5f7fa",
            fg="#2c3e50",
            font=font.Font(family="Helvetica", size=11, weight="bold")
        )
        lbl_titulo.pack(anchor="w", pady=(0, 5))

        # Línea de estado de conexión
        frame_status = tk.Frame(frame_contenedor, bg="#f5f7fa")
        frame_status.pack(anchor="w", pady=(0, 10))

        # Indicador verde de conexión
        canvas = tk.Canvas(frame_status, width=16, height=16, bg="#f5f7fa", highlightthickness=0)
        canvas.create_oval(2, 2, 14, 14, fill="#28a745", outline="")
        canvas.pack(side="left", padx=(0, 5))

        # Texto de conexión
        db_name = os.path.basename(db_path).rsplit(".db", 1)[0]  # Eliminar la extensión
        if db_name == "minutas":
            db_name = "Minutas Producción"
        else:
            db_name = "Minutas personales"

        lbl_conexion = tk.Label(
            frame_status,
            text=f"Conectado a {db_name}",
            bg="#f5f7fa",
            fg="#6c757d",
            font=font.Font(family="Helvetica", size=9, slant="italic")
        )
        lbl_conexion.pack(side="left")

        # Frame para la tabla
        frame_tabla = tk.Frame(frame_contenedor)
        frame_tabla.pack(fill="both", expand=True)

        # Estilo para la tabla
        style = ttk.Style()
        style.theme_use("default")

        # Configurar estilos
        style.configure("Treeview.Heading",
                        font=('Helvetica', 9, 'bold'),
                        background="#e1e5ea",
                        anchor="center")

        style.configure("Treeview",
                        font=('Helvetica', 8),
                        rowheight=30,
                        fieldbackground="#ffffff",
                        foreground="#000000",
                        anchor="w")

        # Estilos para filas con diferentes estados
        style.map("Treeview",
                  background=[('selected', '#347083')],
                  foreground=[('selected', 'white')])

        style.configure("Treeview.Vencido", background="#ffdddd")
        style.configure("Treeview.PorVencer", background="#fff3cd")

        # Crear Treeview
        tree = ttk.Treeview(
            frame_tabla,
            columns=("acuerdo", "dias", "responsables", "comentarios"),
            show="headings",
            height=8,
            selectmode="extended",
            style="Treeview"
        )

        # Configurar columnas
        tree.heading("acuerdo", text="Acuerdo", anchor="w")
        tree.heading("dias", text="Días Restantes", anchor="center")
        tree.heading("responsables", text="Responsables", anchor="w")
        tree.heading("comentarios", text="Comentarios", anchor="w")

        # Configurar anchos iniciales
        tree.column("#0", width=0, stretch=tk.NO)
        tree.column("acuerdo", width=350, minwidth=200, stretch=tk.YES)
        tree.column("dias", width=100, minwidth=80, stretch=tk.NO, anchor="center")
        tree.column("responsables", width=200, minwidth=150, stretch=tk.YES)
        tree.column("comentarios", width=250, minwidth=150, stretch=tk.YES)

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

        # Función mejorada para formatear responsables
        def formatear_responsables(responsables_str):
            if not responsables_str:
                return ""

            responsables = []
            for nombre_completo in responsables_str.split(","):
                nombre_completo = nombre_completo.strip()
                partes = nombre_completo.split()
                if len(partes) >= 2:
                    # Tomar nombre y primer apellido
                    responsables.append(f"{partes[0]} {partes[1]}")
                elif partes:
                    responsables.append(partes[0])

            return "\n".join(responsables)

        # Obtener datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                acuerdo,
                responsables,
                comentarios,
                julianday(fecha_compromiso) - julianday('now') as dias_restantes
            FROM acuerdos
            WHERE estatus != 'Cerrado' AND fecha_compromiso IS NOT NULL
            ORDER BY dias_restantes ASC
        """)
        acuerdos = cursor.fetchall()
        conn.close()

        # Calcular el ancho máximo necesario para responsables
        max_responsables_width = 150  # Valor mínimo inicial

        for acuerdo in acuerdos:
            if acuerdo[1]:  # Si hay responsables
                formatted = formatear_responsables(acuerdo[1])
                # Calcular ancho aproximado (8px por carácter)
                current_width = len(max(formatted.split("\n"), key=len)) * 8 + 20
                max_responsables_width = max(max_responsables_width, current_width)

        # Limitar el ancho máximo a un valor razonable
        max_responsables_width = min(max_responsables_width, 400)
        tree.column("responsables", width=max_responsables_width)

        # Insertar datos con formato y colores
        for acuerdo in acuerdos:
            texto_acuerdo = acuerdo[0] if len(acuerdo[0]) <= 100 else acuerdo[0][:97] + "..."
            dias_restantes = int(acuerdo[3]) if acuerdo[3] is not None else 0
            responsables = formatear_responsables(acuerdo[1])
            comentarios = acuerdo[2] if acuerdo[2] else "-"

            # Determinar etiqueta de estilo
            tags = []
            if dias_restantes < 0:
                tags.append("Vencido")
            elif dias_restantes <= 3:
                tags.append("PorVencer")

            tree.insert("", "end",
                        values=(texto_acuerdo, dias_restantes, responsables, comentarios),
                        tags=tags)

        # Función para ajustar columnas al redimensionar
        def ajustar_columnas(event):
            total_width = tree.winfo_width()
            # Anchos fijos para días y responsables
            fixed_width = tree.column("dias", "width") + tree.column("responsables", "width") + 20
            remaining_width = total_width - fixed_width
            # Distribuir el espacio restante (60% acuerdo, 40% comentarios)
            tree.column("acuerdo", width=int(remaining_width * 0.6))
            tree.column("comentarios", width=int(remaining_width * 0.4))

        tree.bind("<Configure>", ajustar_columnas)

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar la tabla de acuerdos: {str(e)}")