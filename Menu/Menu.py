from PIL import Image, ImageTk
from collections import Counter
from tabla_principal import mostrar_tabla_acuerdos
from common import *

def show_main_menu(db_path):
    """Función que muestra el menú principal con tarjetas de métricas"""
    root = tk.Tk()
    # Configuración básica de la ventana
    width, height = 800, 825  # Aumentamos el tamaño para las tarjetas
    root.title("Sistema de Acuerdos - Menú Principal")
    root.minsize(1000, 600)

    # Centrar la ventana en la pantalla
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    # Paleta de colores mejorada
    bg_color = "#f5f7fa"
    header_color = "#2c3e50"
    button_color = "#3498db"
    button_hover = "#2980b9"
    text_color = "#ecf0f1"
    exit_button_color = "#e74c3c"
    exit_button_hover = "#c0392b"

    # Colores para las tarjetas
    card_colors = {
        "primary": "#3498db",
        "success": "#2ecc71",
        "warning": "#f39c12",
        "danger": "#e74c3c",
        "info": "#9b59b6"
    }

    # Fuentes
    title_font = font.Font(family="Helvetica", size=14, weight="bold")
    button_font = font.Font(family="Helvetica", size=10)
    clock_font = font.Font(family="Helvetica", size=10)
    card_title_font = font.Font(family="Helvetica", size=11, weight="bold")
    card_value_font = font.Font(family="Helvetica", size=24, weight="bold")
    card_footer_font = font.Font(family="Helvetica", size=9)

    # Cargar datos para las tarjetas
    def get_metrics_data():
        """Obtiene los datos para las tarjetas de métricas"""
        metrics = {
            "total_activos": 0,
            "total_editados": 0,
            "total_cerrados": 0,
            "top_responsable": {"nombre": "N/A", "count": 0},
            "acuerdo_mas_atrasado": {
                "texto": "N/A",
                "responsables": "N/A",
                "dias_atraso": 0
            },
            "promedio_dias_compromiso": 0
        }

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 1. Total de acuerdos por estatus
            cursor.execute("SELECT estatus, COUNT(*) FROM acuerdos GROUP BY estatus")
            for estatus, count in cursor.fetchall():
                if estatus == "Activo":
                    metrics["total_activos"] = count
                elif estatus == "Editado":
                    metrics["total_editados"] = count
                elif estatus == "Cerrado":
                    metrics["total_cerrados"] = count

            # 2. Responsable más frecuente (nuevo enfoque)
            cursor.execute("SELECT responsables FROM acuerdos")
            all_responsables = []

            for (responsables,) in cursor.fetchall():
                if responsables:
                    # Separar por comas y limpiar espacios
                    names = [name.strip() for name in responsables.split(",")]
                    # Tomar solo el primer nombre (antes del primer espacio)
                    first_names = [name.split(' ')[0] for name in names]
                    all_responsables.extend(first_names)

            if all_responsables:
                counter = Counter(all_responsables)
                top_responsable = counter.most_common(1)[0]
                metrics["top_responsable"]["nombre"] = top_responsable[0]
                metrics["top_responsable"]["count"] = top_responsable[1]

            # 3. Acuerdo más atrasado con texto y responsables
                cursor.execute("""
                    SELECT a.acuerdo, a.responsables, 
                           julianday('now') - julianday(a.fecha_compromiso) as dias_atraso
                    FROM acuerdos a
                    WHERE a.estatus IN ('Activo', 'Editado') 
                      AND a.fecha_compromiso IS NOT NULL
                      AND julianday(a.fecha_compromiso) < julianday('now')
                    ORDER BY dias_atraso DESC 
                    LIMIT 1
                """)
            result = cursor.fetchone()

            if result:
                acuerdo_texto = result[0]
                responsables = result[1]
                dias_atraso = int(result[2])

                # Acortar el texto del acuerdo si es muy largo
                if len(acuerdo_texto) > 30:
                    acuerdo_texto = acuerdo_texto[:27] + "..."

                # Acortar responsables (tomar solo los primeros 2)
                if responsables:
                    responsables_list = [name.strip() for name in responsables.split(",")]
                    if len(responsables_list) > 2:
                        responsables = ", ".join(responsables_list[:2]) + "..."

                metrics["acuerdo_mas_atrasado"]["texto"] = acuerdo_texto
                metrics["acuerdo_mas_atrasado"]["responsables"] = responsables
                metrics["acuerdo_mas_atrasado"]["dias_atraso"] = dias_atraso

            # 4. Promedio de días para cumplir compromisos
            cursor.execute("""
                SELECT AVG(julianday(fecha_compromiso) - julianday(fecha_estatus))
                FROM acuerdos
                WHERE estatus = 'Cerrado'
            """)
            result = cursor.fetchone()
            if result and result[0]:
                metrics["promedio_dias_compromiso"] = int(result[0])

            conn.close()
        except Exception as e:
            print(f"Error al cargar métricas: {e}")

        return metrics

    # Función para crear tarjetas de métricas
    def create_metric_card(parent, title, value, footer_text, color, height=120, width=300):
        """Crea una tarjeta de métrica visualmente atractiva"""
        card = tk.Frame(
            parent,
            bg="white",
            bd=1,
            relief="solid",
            highlightbackground="#e0e0e0",
            highlightthickness=1,
            width=width,
            height=height
        )

        # Contenido de la tarjeta
        tk.Label(
            card,
            text=title,
            bg="white",
            fg="#7f8c8d",
            font=card_title_font,
            padx=10,
            pady=5,
            anchor="w"
        ).pack(fill="x")

        # Frame para el valor principal (permite múltiples líneas)
        value_frame = tk.Frame(card, bg="white")
        value_frame.pack(fill="both", expand=True, padx=10, pady=5)

        if isinstance(value, list):
            # Para valores multilínea (como el acuerdo atrasado)
            for line in value:
                tk.Label(
                    value_frame,
                    text=line,
                    bg="white",
                    fg=color,
                    font=card_value_font if line == value[0] else card_footer_font,
                    anchor="w",
                    justify="left"
                ).pack(fill="x")
        else:
            # Para valores de una sola línea
            tk.Label(
                value_frame,
                text=value,
                bg="white",
                fg=color,
                font=card_value_font,
                anchor="w",
                justify="left"
            ).pack(fill="x")

        tk.Label(
            card,
            text=footer_text,
            bg="white",
            fg="#95a5a6",
            font=card_footer_font,
            padx=10,
            pady=5,
            anchor="w"
        ).pack(fill="x")

        return card

    # Intentar cargar el logo
    logo_img = None
    try:
        logo_path = r"\\mercury\Mtto_Prod\00_Departamento_Mantenimiento\Minutas\logo.png"
        image = Image.open(logo_path)
        image = image.resize((40, 40), Image.LANCZOS)
        logo_img = ImageTk.PhotoImage(image)
    except Exception as e:
        print(f"No se pudo cargar el logo: {e}")

    # Función para actualizar el reloj
    def update_clock():
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clock_label.config(text=now)
        root.after(1000, update_clock)

    # Función para acciones de botones
    def button_action():
        from acuerdos.interacciones import word_acuerdos
        word_acuerdos(root, db_path)

    # Función al cerrar
    def on_close():
        root.destroy()
        sys.exit()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # Header
    header = tk.Frame(root, bg=header_color, height=40)
    header.pack(fill="x", side="top")

    # Logo (esquina superior izquierda)
    if logo_img:
        logo_label = tk.Label(header, image=logo_img, bg=header_color)
        logo_label.image = logo_img
        logo_label.pack(side="left", padx=10)

    # Título
    title_label = tk.Label(
        header,
        text="Sistema de Gestión de Acuerdos",
        bg=header_color,
        fg=text_color,
        font=title_font
    )
    title_label.pack(side="left", padx=20)

    # Reloj
    clock_label = tk.Label(
        header,
        text="",
        bg=header_color,
        fg=text_color,
        font=clock_font
    )
    clock_label.pack(side="right", padx=20)

    # Marco principal
    main_frame = tk.Frame(root, bg=bg_color)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Marco para las tarjetas de métricas
    metrics_frame = tk.Frame(main_frame, bg=bg_color)
    metrics_frame.pack(fill="x", pady=(0, 20))

    # Obtener datos para las tarjetas
    metrics = get_metrics_data()

    # Crear tarjetas de métricas
    # Fila 1
    card1 = create_metric_card(
        metrics_frame,
        "Acuerdos Activos",
        metrics["total_activos"],
        "Total de acuerdos pendientes",
        card_colors["primary"]
    )
    card1.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

    card2 = create_metric_card(
        metrics_frame,
        "Acuerdos Editados",
        metrics["total_editados"],
        "Total de acuerdos modificados",
        card_colors["warning"]
    )
    card2.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")

    card3 = create_metric_card(
        metrics_frame,
        "Acuerdos Cerrados",
        metrics["total_cerrados"],
        "Total de acuerdos completados",
        card_colors["success"]
    )
    card3.grid(row=0, column=2, padx=10, pady=5, sticky="nsew")

    # Fila 2
    card4 = create_metric_card(
        metrics_frame,
        "Responsable Frecuente",
        metrics["top_responsable"]["nombre"],
        f"Aparece en {metrics['top_responsable']['count']} acuerdos",
        card_colors["info"]
    )
    card4.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

    # Tarjeta de acuerdo atrasado (multilínea)
    acuerdo_atrasado = metrics["acuerdo_mas_atrasado"]
    if acuerdo_atrasado["texto"] != "N/A":
        value_content = [
            acuerdo_atrasado["texto"],
            f"Responsables: {acuerdo_atrasado['responsables']}"
        ]
        footer_text = f"{acuerdo_atrasado['dias_atraso']} días de atraso"
    else:
        value_content = ["No hay acuerdos atrasados"]
        footer_text = ""

    card5 = create_metric_card(
        metrics_frame,
        "Mayor Atraso",
        value_content,
        footer_text,
        card_colors["danger"],
        height=140
    )
    card5.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")

    card6 = create_metric_card(
        metrics_frame,
        "Tiempo Promedio",
        f"{metrics['promedio_dias_compromiso']} días",
        "Tiempo promedio para cerrar acuerdos",
        card_colors["primary"]
    )
    card6.grid(row=1, column=2, padx=10, pady=5, sticky="nsew")

    # Configurar peso de columnas
    for i in range(3):
        metrics_frame.columnconfigure(i, weight=1)

    # Mostrar tabla de acuerdos activos
    mostrar_tabla_acuerdos(main_frame, db_path)

    # Marco para el botón principal
    button_frame = tk.Frame(main_frame, bg=bg_color)
    button_frame.pack(expand=False, pady=1)  # Cambiado a expand=False

    # Configuración del botón principal
    button_config = {
        'width': 20,
        'height': 2,
        'font': button_font,
        'bg': button_color,
        'fg': text_color,
        'activebackground': button_hover,
        'activeforeground': text_color,
        'relief': 'flat',
        'borderwidth': 0,
        'highlightthickness': 0
    }

    # Crear solo el botón de Acuerdos Interactivos
    btn = tk.Button(
        button_frame,
        text="Acuerdos Interactivos",
        command=button_action,
        **button_config
    )
    btn.pack(pady=20, ipadx=10, ipady=5)

    # Efecto hover
    btn.bind("<Enter>", lambda e: btn.config(bg=button_hover))
    btn.bind("<Leave>", lambda e: btn.config(bg=button_color))

    # Marco para el botón de salir (parte inferior derecha)
    exit_frame = tk.Frame(main_frame, bg=bg_color)
    exit_frame.pack(fill="x", side="bottom", pady=10)

    # Botón de salir
    exit_button = tk.Button(
        exit_frame,
        text="Salir",
        command=on_close,
        width=10,
        height=1,
        font=button_font,
        bg=exit_button_color,
        fg=text_color,
        activebackground=exit_button_hover,
        activeforeground=text_color,
        relief='flat',
        borderwidth=0,
        highlightthickness=0
    )
    exit_button.pack(side="right", padx=20)

    # Efecto hover para el botón de salir
    exit_button.bind("<Enter>", lambda e: exit_button.config(bg=exit_button_hover))
    exit_button.bind("<Leave>", lambda e: exit_button.config(bg=exit_button_color))

    # Iniciar reloj
    update_clock()

    # Ejecutar la aplicación
    root.mainloop()