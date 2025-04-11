from common import *
from acuerdos.cargar_historial import load_historial


def save_responsables(item, new_responsables, edit_window, acuerdos_tree, historial_tree, historial_label, db_path):
    """Guarda los responsables editados y registra nuevos usuarios con validaciones"""
    # Obtener valores actuales
    old_responsables = acuerdos_tree.item(item, "values")[2]
    old_responsables_list = [r.strip() for r in old_responsables.split(",")] if old_responsables else []

    # Procesar nuevos responsables (eliminar espacios, vacíos y duplicados)
    processed_responsables = []
    seen = set()

    for r in new_responsables:
        cleaned = r.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            processed_responsables.append(cleaned)

    # Verificar si hay cambios reales
    if set(processed_responsables) == set(old_responsables_list):
        edit_window.destroy()
        return

    new_responsables_str = ", ".join(processed_responsables)
    id_acuerdo = acuerdos_tree.item(item, "values")[0]
    usuario_actual = os.getlogin()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Registrar en historial antes de actualizar
        cursor.execute(
            """INSERT INTO historial_acuerdos 
            (id_acuerdo, acuerdo, responsables, fecha_compromiso, fecha_modificacion, usuario_modifico, estatus)
            SELECT id_acuerdo, acuerdo, responsables, fecha_compromiso, datetime('now'), ?, estatus 
            FROM acuerdos WHERE id_acuerdo = ?""",
            (usuario_actual, id_acuerdo)
        )

        # 2. Actualizar acuerdo
        cursor.execute(
            "UPDATE acuerdos SET responsables = ?, fecha_estatus = datetime('now'), estatus = 'Editado' WHERE id_acuerdo = ?",
            (new_responsables_str, id_acuerdo)
        )

        # 3. Registrar nuevos usuarios que no existan
        existing_users = set()
        cursor.execute("SELECT nombre FROM usuarios")
        for row in cursor.fetchall():
            existing_users.add(row[0].strip())

        new_users_to_add = [r for r in processed_responsables if r not in existing_users]

        for responsable in new_users_to_add:
            cursor.execute(
                """INSERT INTO usuarios 
                (nombre, fecha_registro, usuario_registra) 
                VALUES (?, datetime('now'), ?)""",
                (responsable, usuario_actual)
            )

        conn.commit()

        # Actualizar interfaz
        values = list(acuerdos_tree.item(item, "values"))
        values[2] = new_responsables_str
        acuerdos_tree.item(item, values=values)

        # Recargar historial si este acuerdo está seleccionado
        if acuerdos_tree.focus() == item:
            load_historial(None, acuerdos_tree, historial_tree, historial_label, db_path)

        messagebox.showinfo("Éxito", "Responsables actualizados correctamente.")
        edit_window.destroy()

    except sqlite3.Error as e:
        messagebox.showerror("Error", f"Error de base de datos: {e}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron actualizar los responsables: {e}")
    finally:
        if 'conn' in locals():
            conn.close()