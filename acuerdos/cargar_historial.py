from common import *
from acuerdos.formato_texto import formatear_texto



def load_historial(event, acuerdos_tree, historial_tree, historial_label, db_path):
    """Carga el historial del acuerdo seleccionado"""
    selected = acuerdos_tree.focus()
    if not selected:
        return

    # Obtener ID del acuerdo seleccionado
    id_acuerdo = acuerdos_tree.item(selected)["values"][0]

    # Actualizar label
    historial_label.config(text=f"Historial de modificaciones - Acuerdo {id_acuerdo}")

    # Limpiar treeview de historial
    for item in historial_tree.get_children():
        historial_tree.delete(item)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Obtener el usuario_registra del acuerdo
        cursor.execute(
            "SELECT usuario_registra FROM acuerdos WHERE id_acuerdo = ?",
            (id_acuerdo,)
        )
        usuario_registra = cursor.fetchone()[0]

        # Obtener versión actual
        cursor.execute(
            """SELECT 
                a.fecha_estatus, 
                COALESCE(
                    (SELECT ha.usuario_modifico 
                     FROM historial_acuerdos ha 
                     WHERE ha.id_acuerdo = a.id_acuerdo 
                     ORDER BY ha.fecha_modificacion DESC 
                     LIMIT 1),
                    a.usuario_registra
                ) as ultimo_usuario,
                a.estatus,
                a.acuerdo,
                a.responsables,
                a.fecha_compromiso,
                a.comentarios
               FROM acuerdos a
               WHERE a.id_acuerdo = ?""",
            (id_acuerdo,)
        )
        current = cursor.fetchone()
        if current:
            # Formatear fechas
            formatted_current = list(current)

            # Formatear fecha de estatus
            if formatted_current[0]:
                formatted_current[0] = datetime.strptime(formatted_current[0], "%Y-%m-%d %H:%M:%S").strftime(
                    "%d/%m/%Y %H:%M")

            # Formatear fecha compromiso
            if formatted_current[5]:
                formatted_current[5] = datetime.strptime(formatted_current[5], "%Y-%m-%d").strftime("%d/%m/%Y")

            # Formatear comentarios
            formatted_current[6] = formatear_texto(formatted_current[6] if formatted_current[6] else "")

            historial_tree.insert("", "end", values=formatted_current, tags=('current',))

        # Obtener historial
        cursor.execute(
            """SELECT 
                fecha_modificacion, 
                usuario_modifico, 
                estatus,
                acuerdo,
                responsables,
                fecha_compromiso,
                comentarios
               FROM historial_acuerdos 
               WHERE id_acuerdo = ? 
               ORDER BY fecha_modificacion DESC""",
            (id_acuerdo,)
        )

        historial_rows = cursor.fetchall()

        for idx, row in enumerate(historial_rows):
            formatted_row = list(row)

            # Formatear fecha de modificación
            if formatted_row[0]:
                formatted_row[0] = datetime.strptime(formatted_row[0], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")

            # Formatear fecha compromiso si existe
            if formatted_row[5]:
                formatted_row[5] = datetime.strptime(formatted_row[5], "%Y-%m-%d").strftime("%d/%m/%Y")

            # Formatear texto
            if formatted_row[3]:
                formatted_row[3] = formatear_texto(formatted_row[3])  # acuerdo
            if formatted_row[6]:
                formatted_row[6] = formatear_texto(formatted_row[6])  # comentarios

            # Si es la última modificación (la más antigua)
            if idx == len(historial_rows) - 1:
                formatted_row[1] = usuario_registra  # Usar el usuario_registra del acuerdo

            historial_tree.insert("", "end", values=formatted_row)

        conn.close()

        # Ajustar altura del treeview según el número de registros
        num_items = len(historial_tree.get_children())
        historial_tree.configure(height=min(max(num_items, 5), 10))  # Mínimo 5, máximo 10 filas

        # Resaltar diferencias automáticamente para la primera versión
        if historial_tree.get_children():
            highlight_changes(None, historial_tree)

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el historial: {e}")


def highlight_changes(event, historial_tree):
    """Resalta los cambios entre versiones en el historial"""
    # Limpiar tags anteriores
    for item in historial_tree.get_children():
        for col in historial_tree["columns"]:
            historial_tree.set(item, col, historial_tree.set(item, col))

    # No hay nada que comparar si solo hay un item
    if len(historial_tree.get_children()) <= 1:
        return

    # Obtener items a comparar
    items = historial_tree.get_children()
    for i in range(len(items) - 1):
        current_item = items[i]
        previous_item = items[i + 1]

        # Comparar cada campo
        for col in historial_tree["columns"]:
            current_val = historial_tree.set(current_item, col)
            previous_val = historial_tree.set(previous_item, col)

            if current_val != previous_val:
                # Determinar tipo de cambio
                if not previous_val and current_val:
                    # Nuevo valor (adición)
                    historial_tree.item(current_item, tags=('added',))
                elif previous_val and not current_val:
                    # Valor eliminado
                    historial_tree.item(current_item, tags=('removed',))
                else:
                    # Valor modificado
                    historial_tree.item(current_item, tags=('changed',))