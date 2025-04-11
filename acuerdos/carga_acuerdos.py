from common import *
from acuerdos.fromato_texto import formatear_texto
from acuerdos.cerrar_2 import cerrar_acuerdo_seleccionado

def load_acuerdos(acuerdos_tree, db_path, id_filter, text_filter, resp_filter, date_from, date_to, status_filter):
    """Carga los acuerdos principales según los filtros aplicados."""

    # Limpiar TreeView
    acuerdos_tree.delete(*acuerdos_tree.get_children())

    # Consulta base
    query = """
        SELECT 
            id_acuerdo, 
            acuerdo, 
            responsables, 
            fecha_estatus, 
            estatus,
            fecha_compromiso,
            comentarios,
            accion
        FROM acuerdos 
        WHERE 1=1
    """
    params = []

    # Filtros dinámicos
    if id_filter.get():
        query += " AND id_acuerdo LIKE ?"
        params.append(f"%{id_filter.get()}%")

    if text_filter.get():
        query += " AND acuerdo LIKE ?"
        params.append(f"%{text_filter.get()}%")

    if resp_filter.get():
        query += " AND responsables LIKE ?"
        params.append(f"%{resp_filter.get()}%")

    if date_from.get():
        query += " AND fecha_estatus >= ?"
        params.append(date_from.get())

    if date_to.get():
        query += " AND fecha_estatus <= ?"
        params.append(date_to.get())

    if status_filter.get() != "Todos":
        query += " AND estatus = ?"
        params.append(status_filter.get())

    # Orden por prioridad de estatus y fecha de compromiso
    query += """
        ORDER BY 
            CASE 
                WHEN estatus = 'Editado' THEN 1 
                WHEN estatus = 'Activo' THEN 2
                WHEN estatus = 'Cerrado' THEN 3
                ELSE 4
            END ASC,
            fecha_compromiso ASC
    """

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)

        for row in cursor.fetchall():
            # row: [0=id, 1=acuerdo, 2=responsables, 3=fecha_estatus, 4=estatus, 5=fecha_compromiso, 6=comentarios]
            formatted_row = list(row)

            # Formatear fechas
            try:
                if formatted_row[3]:  # fecha_estatus
                    formatted_row[3] = datetime.strptime(formatted_row[3], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            except:
                pass

            try:
                if formatted_row[5]:  # fecha_compromiso
                    formatted_row[5] = datetime.strptime(formatted_row[5], "%Y-%m-%d").strftime("%d/%m/%Y")
            except:
                pass
            try:
                # Determinar el texto y tag para la columna de acción
                if row[4] == "Cerrado":  # row[4] es el estatus
                    accion_text = "Cerrado"
                    tags = ('cerrado',)
                else:
                    accion_text = "Cerrar"
                    tags = ('cerrable',)

                # Insertar fila con los datos
                tree.insert("", "end", values=row + (accion_text,), tags=tags)
            except:

                pass

            # Formatear campos largos
            formatted_row[1] = formatear_texto(formatted_row[1])  # acuerdo
            formatted_row[2] = formatear_texto(formatted_row[2])  # responsables
            formatted_row[4] = formatear_texto(formatted_row[4])  # accion
            formatted_row[6] = formatear_texto(formatted_row[6] if formatted_row[6] else "")  # comentarios

            # Determinar texto de acción y tags
            if row[4] == "Cerrado":  # row[4] es el estatus
                accion_text = "Cerrado"
                tags = ('cerrado', 'no_underline')  # Agregamos tag adicional
            else:
                accion_text = "Cerrar"
                tags = ('cerrable', 'no_underline')  # Agregamos tag adicional

            # Añadir la columna de acción al final de los valores
            values_to_insert = formatted_row + [accion_text]

            # Insertar en el Treeview
            item_id = acuerdos_tree.insert("", "end", values=values_to_insert, tags=tags)
            acuerdos_tree.item(item_id, tags=tags + ('wraptext', 'no_underline'))




        conn.close()

    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron cargar los acuerdos: {e}")
