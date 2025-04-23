from common import *
from acuerdos.cargar_historial import load_historial


def save_responsables(item, new_responsables, edit_window, acuerdos_tree, historial_tree, historial_label, db_path):
    """Guarda los responsables editados con verificación mejorada de duplicados"""
    # Obtener valores actuales
    old_responsables = acuerdos_tree.item(item, "values")[2]
    old_responsables_list = [r.strip() for r in old_responsables.split(",")] if old_responsables else []

    # Procesar nuevos responsables
    processed_responsables = []
    seen = set()
    has_commas = False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Obtener todos los usuarios existentes con sus versiones formateadas
        cursor.execute("SELECT nombre FROM usuarios")
        existing_users = {}
        for row in cursor.fetchall():
            nombre_completo = row[0].strip()
            # Generar versión formateada para comparación
            partes = nombre_completo.split()
            if len(partes) >= 2:
                nombre_formateado = f"{partes[0]} {partes[1][0]}."
            else:
                nombre_formateado = partes[0]

            existing_users[nombre_formateado.lower()] = nombre_completo

        for r in new_responsables:
            cleaned = r.replace("\n", " ").replace("\r", " ").strip()

            if "," in cleaned:
                has_commas = True
                split_names = [name.strip() for name in cleaned.split(",") if name.strip()]
                for name in split_names:
                    if name and name not in seen:
                        seen.add(name)
                        # Buscar coincidencia con nombres formateados
                        nombre_actualizado = existing_users.get(name.lower(), name)
                        processed_responsables.append(nombre_actualizado)
            elif cleaned and cleaned not in seen:
                seen.add(cleaned)
                # Buscar coincidencia con nombres formateados
                nombre_actualizado = existing_users.get(cleaned.lower(), cleaned)
                processed_responsables.append(nombre_actualizado)

        # Verificar si hay cambios reales
        old_normalized = [n.lower() for n in old_responsables_list]
        new_normalized = [n.lower() for n in processed_responsables]

        if set(new_normalized) == set(old_normalized):
            edit_window.destroy()
            conn.close()
            return

        new_responsables_str = ", ".join(processed_responsables)
        id_acuerdo = acuerdos_tree.item(item, "values")[0]
        usuario_actual = os.getlogin()

        # Registrar en historial y actualizar acuerdo (igual que antes)
        estatus = "Eliminado" if has_commas else "Editado"
        cursor.execute(
            """INSERT INTO historial_acuerdos 
            (id_acuerdo, acuerdo, responsables, fecha_compromiso, fecha_modificacion, usuario_modifico, estatus)
            SELECT id_acuerdo, acuerdo, responsables, fecha_compromiso, datetime('now'), ?, estatus 
            FROM acuerdos WHERE id_acuerdo = ?""",
            (usuario_actual, id_acuerdo)
        )

        cursor.execute(
            "UPDATE acuerdos SET responsables = ?, fecha_estatus = datetime('now'), estatus = ? WHERE id_acuerdo = ?",
            (new_responsables_str, estatus, id_acuerdo)
        )

        # Registrar SOLO usuarios realmente nuevos
        new_users_to_add = [
            name for name in processed_responsables
            if name.lower() not in [n.lower() for n in existing_users.values()]
        ]

        for responsable in new_users_to_add:
            cursor.execute(
                """INSERT INTO usuarios 
                (nombre, fecha_registro, usuario_registra, estatus) 
                VALUES (?, datetime('now'), ?, 'Activo')""",
                (responsable, usuario_actual)
            )

        conn.commit()

        # Actualizar interfaz
        values = list(acuerdos_tree.item(item, "values"))
        values[2] = new_responsables_str
        acuerdos_tree.item(item, values=values)

        if acuerdos_tree.focus() == item:
            load_historial(None, acuerdos_tree, historial_tree, historial_label, db_path)

        #messagebox.showinfo("Éxito", f"Responsables actualizados. Nuevos registros: {len(new_users_to_add)}")
        edit_window.destroy()

    except Exception as e:
        messagebox.showerror("Error", f"Error al guardar: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()