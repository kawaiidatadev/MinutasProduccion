from common import *
from acuerdos.cargar_historial import load_historial
def save_commitment_date(item, new_date_str, edit_window, acuerdos_tree, historial_tree, historial_label, db_path):
    """Guarda la fecha de compromiso editada"""
    current_date_str = acuerdos_tree.item(item, "values")[5]

    if new_date_str == current_date_str:
        messagebox.showinfo("Información", "No se realizaron cambios.")
        edit_window.destroy()
        return

    id_acuerdo = acuerdos_tree.item(item, "values")[0]

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Formatear fecha para la base de datos
        db_date = None
        if new_date_str:
            try:
                day, month, year = map(int, new_date_str.split("/"))
                db_date = f"{year}-{month:02d}-{day:02d}"
            except:
                messagebox.showerror("Error", "Formato de fecha inválido")
                return

        # Obtener el usuario actual de Windows
        usuario_actual = os.getlogin()

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
            "UPDATE acuerdos SET fecha_compromiso = ?, fecha_estatus = datetime('now'), estatus = 'Editado' WHERE id_acuerdo = ?",
            (db_date, id_acuerdo)
        )

        conn.commit()
        conn.close()

        # Actualizar interfaz
        values = list(acuerdos_tree.item(item, "values"))
        values[5] = new_date_str if new_date_str else ""
        acuerdos_tree.item(item, values=values)

        # Recargar historial si este acuerdo está seleccionado
        if acuerdos_tree.focus() == item:
            load_historial(None, acuerdos_tree, historial_tree, historial_label, db_path)

        #messagebox.showinfo("Éxito", "Fecha de compromiso actualizada correctamente.")
        edit_window.destroy()

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo actualizar la fecha de compromiso: {e}")


