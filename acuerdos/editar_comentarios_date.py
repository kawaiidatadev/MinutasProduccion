from common import *
from acuerdos.children_window import center_child_window
from acuerdos.guardar_fecha_compromiso import save_commitment_date

def edit_commitment_date(item, acuerdos_tree, historial_tree, historial_label, db_path):
    """Permite editar la fecha de compromiso con doble clic"""
    current_date_str = acuerdos_tree.item(item, "values")[5]

    # Crear ventana de calendario
    date_window = tk.Toplevel(acuerdos_tree.winfo_toplevel())
    date_window.title("Seleccionar Fecha de Compromiso")
    date_window.transient(acuerdos_tree.winfo_toplevel())
    date_window.grab_set()

    # Calendario
    try:
        if current_date_str:
            day, month, year = map(int, current_date_str.split("/"))
            cal = Calendar(
                date_window,
                selectmode="day",
                year=year,
                month=month,
                day=day,
                date_pattern="dd/mm/yyyy"
            )
        else:
            cal = Calendar(date_window, selectmode="day", date_pattern="dd/mm/yyyy")
    except:
        cal = Calendar(date_window, selectmode="day", date_pattern="dd/mm/yyyy")

    cal.pack(padx=10, pady=10)

    # Botones
    btn_frame = ttk.Frame(date_window)
    btn_frame.pack(fill="x", padx=10, pady=10)

    ttk.Button(
        btn_frame,
        text="Seleccionar",
        command=lambda: save_commitment_date(item, cal.get_date(), date_window,
                                             acuerdos_tree, historial_tree, historial_label, db_path)
    ).pack(side="right", padx=5)

    ttk.Button(
        btn_frame,
        text="Eliminar",
        command=lambda: save_commitment_date(item, "", date_window,
                                             acuerdos_tree, historial_tree, historial_label, db_path)
    ).pack(side="right", padx=5)

    ttk.Button(
        btn_frame,
        text="Cancelar",
        command=date_window.destroy
    ).pack(side="right", padx=5)

    # Centrar ventana
    center_child_window(date_window, acuerdos_tree.winfo_toplevel())

