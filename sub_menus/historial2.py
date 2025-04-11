# sub_menus/historial.py
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3


def mostrar_historial(parent_window, db_path, id_acuerdo):
    # Crear ventana de historial
    hist_window = tk.Toplevel(parent_window)
    hist_window.title(f"Historial de Modificaciones - Acuerdo {id_acuerdo}")
    hist_window.geometry("900x600")

    # Marco principal
    main_frame = tk.Frame(hist_window)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Treeview para mostrar el historial
    tree = ttk.Treeview(main_frame, columns=("fecha", "usuario", "estatus"), show="headings")
    tree.heading("fecha", text="Fecha Modificación")
    tree.heading("usuario", text="Usuario")
    tree.heading("estatus", text="Estatus")
    tree.column("fecha", width=150)
    tree.column("usuario", width=100)
    tree.column("estatus", width=100)
    tree.pack(fill="both", expand=True)

    # Botón para ver detalles
    def ver_detalles():
        selected = tree.focus()
        if not selected:
            messagebox.showwarning("Advertencia", "Seleccione un registro del historial")
            return

        # Obtener datos completos del registro seleccionado
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT acuerdo, responsables, fecha_compromiso FROM historial_acuerdos WHERE rowid = ?",
                (selected,)
            )
            resultado = cursor.fetchone()
            conn.close()

            if resultado:
                # Mostrar ventana con detalles
                det_window = tk.Toplevel(hist_window)
                det_window.title("Detalles de Versión")

                # Mostrar los datos del acuerdo histórico
                tk.Label(det_window, text="Acuerdo:", font=("Helvetica", 10, "bold")).pack(anchor="w")
                tk.Label(det_window, text=resultado[0], wraplength=800, justify="left").pack(fill="x")

                tk.Label(det_window, text="\nResponsables:", font=("Helvetica", 10, "bold")).pack(anchor="w")
                tk.Label(det_window, text=resultado[1]).pack(anchor="w")

                tk.Label(det_window, text="\nFecha compromiso:", font=("Helvetica", 10, "bold")).pack(anchor="w")
                tk.Label(det_window, text=resultado[2]).pack(anchor="w")

                # Botón para cerrar
                tk.Button(det_window, text="Cerrar", command=det_window.destroy).pack(pady=10)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los detalles: {e}")

    tk.Button(main_frame, text="Ver Detalles", command=ver_detalles).pack(pady=10)

    # Cargar datos del historial
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT rowid, fecha_modificacion, usuario_modifico, estatus 
               FROM historial_acuerdos 
               WHERE id_acuerdo = ? 
               ORDER BY fecha_modificacion DESC""",
            (id_acuerdo,)
        )

        for row in cursor.fetchall():
            tree.insert("", "end", iid=row[0], values=(row[1], row[2], row[3]))

        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el historial: {e}")

    hist_window.mainloop()


