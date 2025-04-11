from common import *
from acuerdos.cargar_historial import load_historial



def save_responsables(item, new_responsables, edit_window, acuerdos_tree, historial_tree, historial_label, db_path):
    """Guarda los responsables editados"""
    old_responsables = acuerdos_tree.item(item, "values")[2]
    new_responsables_str = ", ".join(new_responsables)

    if new_responsables_str == old_responsables:
        edit_window.destroy()
        return

    id_acuerdo = acuerdos_tree.item(item, "values")[0]
    usuario_actual = os.getlogin()  # Obtener el usuario de Windows

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Registrar en historial antes de actualizar
        cursor.execute(
            """INSERT INTO historial_acuerdos 
            (id_acuerdo, acuerdo, responsables, fecha_compromiso, fecha_modificacion, usuario_modifico, estatus)
            SELECT id_acuerdo, acuerdo, responsables, fecha_compromiso, datetime('now'), ?, estatus 
            FROM acuerdos WHERE id_acuerdo = ?""",
            (usuario_actual, id_acuerdo)
        )

        # Actualizar acuerdo
        cursor.execute(
            "UPDATE acuerdos SET responsables = ?, fecha_estatus = datetime('now'), estatus = 'Editado' WHERE id_acuerdo = ?",
            (new_responsables_str, id_acuerdo)
        )

        conn.commit()
        conn.close()


        # Actualizar interfaz
        values = list(acuerdos_tree.item(item, "values"))
        values[2] = new_responsables_str
        acuerdos_tree.item(item, values=values)

        # Recargar historial si este acuerdo está seleccionado
        if acuerdos_tree.focus() == item:
            load_historial(None, acuerdos_tree, historial_tree, historial_label, db_path)

        messagebox.showinfo("Éxito", "Responsables actualizados correctamente.")
        edit_window.destroy()

    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron actualizar los responsables: {e}")

