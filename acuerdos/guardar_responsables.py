from common import *
from acuerdos.cargar_historial import load_historial


def save_responsables(item, new_responsables, edit_window, acuerdos_tree, historial_tree, historial_label, db_path):
    """Guarda los responsables editados y registra nuevos usuarios con validaciones"""
    # Obtener valores actuales
    old_responsables = acuerdos_tree.item(item, "values")[2]
    old_responsables_list = [r.strip() for r in old_responsables.split(",")] if old_responsables else []

    # Procesar nuevos responsables (eliminar espacios, vacíos, duplicados y saltos de línea)
    processed_responsables = []
    seen = set()
    has_commas = False  # Bandera para detectar nombres con comas

    for r in new_responsables:
        # Eliminar saltos de línea y espacios extra
        cleaned = r.replace("\n", " ").replace("\r", " ").strip()

        # Verificar si el nombre contiene comas después de limpiar
        if "," in cleaned:
            has_commas = True
            # Dividir por comas y procesar cada parte
            split_names = [name.strip() for name in cleaned.split(",") if name.strip()]
            for name in split_names:
                if name and name not in seen:
                    seen.add(name)
                    processed_responsables.append(name)
        elif cleaned and cleaned not in seen:
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

        # Determinar el estatus basado en si hubo comas en los nombres
        estatus = "Eliminado" if has_commas else "Editado"

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
            "UPDATE acuerdos SET responsables = ?, fecha_estatus = datetime('now'), estatus = ? WHERE id_acuerdo = ?",
            (new_responsables_str, estatus, id_acuerdo)
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

        messagebox.showinfo("Éxito", f"Responsables actualizados correctamente. Estatus: {estatus}")
        edit_window.destroy()

    except sqlite3.Error as e:
        messagebox.showerror("Error", f"Error de base de datos: {e}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron actualizar los responsables: {e}")
    finally:
        if 'conn' in locals():
            conn.close()