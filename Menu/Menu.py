from collections import Counter
from tabla_principal import mostrar_tabla_acuerdos
from common import *
import sys
import ctypes
from ctypes import wintypes
from tkinter import font
import logging
from sql.db import crear_nueva_minuta

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DPI_AWARENESS:
    UNAWARE = 0
    SYSTEM_AWARE = 1
    PER_MONITOR_AWARE = 2


def show_main_menu(db_path):
    """Función principal con autoajuste para HiDPI"""  # <-- 4 espacios
    root = tk.Tk() if not tk._default_root else tk._default_root

    # Limpiar si ya existe contenido
    if hasattr(root, '_initialized'):
        for widget in root.winfo_children():
            widget.destroy()
    else:
        root._initialized = True
        from acuerdos.ventana_names import move_to_largest_monitor
        move_to_largest_monitor(root)

    root.title("Sistema de Acuerdos - Menú Principal")
    #bloquear_ventana_robusta(root)
    from acuerdos.ventana_names import move_to_largest_monitor
    move_to_largest_monitor(root)

    # Maximizar la ventana según el sistema operativo
    if sys.platform == 'win32':
        print("zomed menu.py")
        root.state('zoomed')  # Para Windows




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

            # 2. Responsable más frecuente
            from sql.querys import usuarios_frecuentes_card
            cursor.execute(usuarios_frecuentes_card)
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
        from rutas import logo_path
        logo_path = logo_path
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

    # Marco contenedor para los tres botones (centrado)
    buttons_container = tk.Frame(main_frame, bg=bg_color)
    buttons_container.pack(pady=20, fill='x')

    # Configuración común para todos los botones
    button_style = {
        'font': ('Helvetica', 11, 'bold'),
        'height': 2,
        'borderwidth': 3,
        'highlightthickness': 0,
        'cursor': 'hand2',
        'activeforeground': text_color
    }


    # Definir color para el nuevo botón (puedes ajustar estos valores)
    new_button_color = '#4CAF50'  # Verde
    new_button_hover = '#45a049'  # Verde oscuro

    # Definir color para el botón Host (puedes ajustar estos valores)
    host_button_color = '#2196F3'  # Azul
    host_button_hover = '#0b7dda'  # Azul oscuro

    # Botón de Acuerdos Interactivos (mejorado)
    btn_interactivos = tk.Button(
        buttons_container,
        text="ACUERDOS",
        command=button_action,
        bg=button_color,
        fg=text_color,
        activebackground=button_hover,
        relief='raised',
        width=20,
        **button_style
    )
    btn_interactivos.pack(side='left', expand=True, padx=(0, 10))

    # Nuevo botón para crear minuta
    btn_minuta = tk.Button(
        buttons_container,
        text="NUEVA MINUTA",
        command=crear_nueva_minuta,  # Asegúrate de definir esta función
        bg=new_button_color,
        fg=text_color,
        activebackground=new_button_hover,
        relief='raised',
        width=20,
        **button_style
    )
    btn_minuta.pack(side='left', expand=True, padx=10)

    from gestion_masters import host, get_pending_requests_count  # Nueva función

    # Primero creamos una función auxiliar para obtener el conteo
    def get_pending_count(db_path):
        try:
            return get_pending_requests_count(db_path)
        except:
            return 0


    # Luego modificamos el botón Host
    pending_count = get_pending_count(db_path)

    btn_host = tk.Button(
        buttons_container,
        text=f"HOST  {'•' if pending_count > 0 else ''}",
        command=lambda: host(db_path),
        bg=host_button_color,
        fg=text_color,
        activebackground=host_button_hover,
        relief='raised',
        width=15,
        font=('Helvetica', 11, 'bold'),
        height=2,
        borderwidth=3,
        highlightthickness=0,
        cursor='hand2',
        activeforeground=text_color,
        compound='right'
    )
    btn_host.pack(side='left', expand=True, padx=10)

    # Añadir un badge pequeño si hay solicitudes pendientes
    if pending_count > 0:
        badge = tk.Label(buttons_container,
                         text=str(pending_count),
                         bg='#FF6B6B',  # Rojo suave
                         fg='white',
                         font=('Helvetica', 8),
                         bd=0,
                         padx=4,
                         pady=1)
        badge.place(in_=btn_host,
                    relx=1.0,
                    rely=0.0,
                    anchor='ne',
                    x=-5,
                    y=5)


    # Botón de Salir (mejorado)
    exit_button = tk.Button(
        buttons_container,
        text="SALIR DEL SISTEMA",
        command=on_close,
        bg=exit_button_color,
        fg=text_color,
        activebackground=exit_button_hover,
        relief='raised',
        width=18,
        **button_style
    )
    exit_button.pack(side='right', expand=True, padx=(10, 0))

    # Efectos hover mejorados para todos los botones
    btn_interactivos.bind("<Enter>", lambda e: btn_interactivos.config(bg=button_hover, relief='sunken'))
    btn_interactivos.bind("<Leave>", lambda e: btn_interactivos.config(bg=button_color, relief='raised'))

    btn_minuta.bind("<Enter>", lambda e: btn_minuta.config(bg=new_button_hover, relief='sunken'))
    btn_minuta.bind("<Leave>", lambda e: btn_minuta.config(bg=new_button_color, relief='raised'))

    btn_host.bind("<Enter>", lambda e: btn_host.config(bg=host_button_hover, relief='sunken'))
    btn_host.bind("<Leave>", lambda e: btn_host.config(bg=host_button_color, relief='raised'))

    exit_button.bind("<Enter>", lambda e: exit_button.config(
        bg=exit_button_hover,
        relief='sunken'
    ))
    exit_button.bind("<Leave>", lambda e: exit_button.config(
        bg=exit_button_color,
        relief='raised'
    ))

    # Iniciar reloj
    update_clock()

    # Ejecutar la aplicación
    root.mainloop()