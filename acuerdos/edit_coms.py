from common import *
from acuerdos.children_window import center_child_window
def edit_comments(item, acuerdos_tree, historial_tree, historial_label, db_path):
    """Permite editar los comentarios del acuerdo con doble clic"""
    current_comments = acuerdos_tree.item(item, "values")[6]  # Índice 6 para comentarios

    # Crear ventana de edición
    edit_window = tk.Toplevel(acuerdos_tree.winfo_toplevel())
    edit_window.title("Editar Comentarios")
    edit_window.transient(acuerdos_tree.winfo_toplevel())
    edit_window.grab_set()

    # Área de texto con scroll
    text_frame = ttk.Frame(edit_window)
    text_frame.pack(fill="both", expand=True, padx=10, pady=10)

    text_scroll = ttk.Scrollbar(text_frame)
    text_scroll.pack(side="right", fill="y")

    text_edit = tk.Text(
        text_frame,
        wrap="word",
        height=10,
        width=60,
        yscrollcommand=text_scroll.set
    )
    text_edit.pack(fill="both", expand=True)
    text_edit.insert("1.0", current_comments if current_comments else "")

    # Configurar el foco y posición del cursor
    text_edit.focus_set()  # Esto hace que el foco vaya al widget Text
    text_edit.mark_set("insert", "end")  # Coloca el cursor al final del texto
    text_edit.see("end")  # Asegura que el final del texto sea visible

    text_scroll.config(command=text_edit.yview)



    # Función para guardar con Enter
    from acuerdos.guardar_comentarios import save_comments
    def on_enter(event):
        save_comments(item, text_edit.get("1.0", "end-1c"), edit_window,
                      acuerdos_tree, historial_tree, historial_label, db_path)

    text_edit.bind("<Return>", on_enter)

    # Botones
    btn_frame = ttk.Frame(edit_window)
    btn_frame.pack(fill="x", padx=10, pady=10)

    ttk.Button(
        btn_frame,
        text="Guardar",
        command=lambda: save_comments(item, text_edit.get("1.0", "end-1c"), edit_window,
                                      acuerdos_tree, historial_tree, historial_label, db_path)
    ).pack(side="right", padx=5)

    ttk.Button(
        btn_frame,
        text="Cancelar",
        command=edit_window.destroy
    ).pack(side="right", padx=5)

    # Centrar ventana
    center_child_window(edit_window, acuerdos_tree.winfo_toplevel())
