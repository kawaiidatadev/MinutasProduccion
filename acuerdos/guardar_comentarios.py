from common import *
from acuerdos.cargar_historial import load_historial
def save_comments(item, new_comments, edit_window, acuerdos_tree, historial_tree, historial_label, db_path):
    """Guarda los comentarios editados del acuerdo"""
    old_comments = acuerdos_tree.item(item, "values")[6]

    if new_comments.strip() == (old_comments.strip() if old_comments else ""):
        edit_window.destroy()
        return

    id_acuerdo = acuerdos_tree.item(item, "values")[0]

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Obtener el usuario actual de Windows
        usuario_actual = os.getlogin()

        # Registrar en historial antes de actualizar
        cursor.execute(
            """INSERT INTO historial_acuerdos 
            (id_acuerdo, acuerdo, responsables, fecha_compromiso, comentarios, fecha_modificacion, usuario_modifico, estatus)
            SELECT id_acuerdo, acuerdo, responsables, fecha_compromiso, comentarios, datetime('now'), ?, estatus 
            FROM acuerdos WHERE id_acuerdo = ?""",
            (usuario_actual, id_acuerdo)
        )

        # Actualizar acuerdo (nota: asumiendo que tu tabla tiene una columna 'comentarios')
        cursor.execute(
            "UPDATE acuerdos SET comentarios = ?, fecha_estatus = datetime('now'), estatus = 'Editado' WHERE id_acuerdo = ?",
            (new_comments if new_comments.strip() else None, id_acuerdo)  # Guardar NULL si está vacío
        )

        conn.commit()
        conn.close()

        # Actualizar interfaz
        values = list(acuerdos_tree.item(item, "values"))
        values[6] = new_comments if new_comments.strip() else ""
        acuerdos_tree.item(item, values=values)

        # Recargar historial si este acuerdo está seleccionado
        if acuerdos_tree.focus() == item:
            load_historial(None, acuerdos_tree, historial_tree, historial_label, db_path)

        edit_window.destroy()

    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron actualizar los comentarios: {e}")