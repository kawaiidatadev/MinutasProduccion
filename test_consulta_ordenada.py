import sqlite3
from datetime import datetime
from time import sleep
from rutas import MASTER

def registrar_ingreso(direccion_filtrada, path_master=MASTER, usuario_actual_windows="", max_intentos=3):
    """
    Registra el ingreso a una base de datos en el sistema maestro.
    Crea la estructura si no existe e identifica si el acceso es desde 'dbs' o 'solicitudes_acceso'.
    """
    conn = None
    intentos = 0
    espera_base = 1

    while intentos < max_intentos:
        try:
            print(f"\nIntento {intentos + 1}/{max_intentos}")
            print("Conectando a MASTER.db...")

            conn = sqlite3.connect(
                path_master,
                timeout=10,
                check_same_thread=False
            )
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            print("✓ Conexión exitosa")

            # Crear tabla ingresos si no existe
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingresos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                db_id INTEGER NOT NULL,
                administrador TEXT,
                esclavo TEXT,
                db_name TEXT,
                direccion TEXT NOT NULL,
                fecha_de_ultimo_acceso TEXT NOT NULL,
                tabla_origen TEXT,
                FOREIGN KEY(db_id) REFERENCES dbs(id)
            )
            """)
            print("✓ Estructura de base de datos verificada")

            # Buscar registro
            print(f"\nBuscando dirección: {direccion_filtrada}")
            query = """
            SELECT dbs.id, dbs.usuario_windows, dbs.db_name, dbs.direccion,
                   dbs.fecha_de_ultimo_acceso, solicitudes_acceso.usuario_solicitante,
                   CASE 
                       WHEN dbs.usuario_windows = ? THEN 'dbs'
                       WHEN solicitudes_acceso.usuario_solicitante = ? AND solicitudes_acceso.estatus = 'aprobado' THEN 'solicitudes_acceso'
                   END AS tabla_origen
            FROM dbs
            LEFT JOIN solicitudes_acceso ON 
                dbs.id = solicitudes_acceso.db_id AND
                solicitudes_acceso.usuario_solicitante = ? AND
                solicitudes_acceso.estatus = 'aprobado'
            WHERE dbs.direccion = ? 
                AND (dbs.usuario_windows = ? 
                     OR solicitudes_acceso.usuario_solicitante IS NOT NULL)
            LIMIT 1;
            """

            cursor.execute(query, (
                usuario_actual_windows, usuario_actual_windows,
                usuario_actual_windows, direccion_filtrada,
                usuario_actual_windows
            ))
            registro = cursor.fetchone()

            if not registro:
                print(f"× La dirección no existe o no tiene permisos")
                print("  Posibles causas:")
                print("  - La dirección no está registrada en MASTER.db")
                print("  - No tiene solicitud de acceso aprobada")
                print("  - El registro está marcado como 'Eliminado'")
                return False

            id_db, admin, db_name, direccion, ult_acceso, esclavo, tabla_origen = registro
            fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Insertar registro de ingreso
            print("\nRegistrando acceso:")
            cursor.execute("""
            INSERT INTO ingresos 
            (db_id, administrador, esclavo, db_name, direccion, fecha_de_ultimo_acceso, tabla_origen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (id_db, admin, esclavo, db_name, direccion, fecha_actual, tabla_origen))

            # Actualizar último acceso
            cursor.execute("""
            UPDATE dbs 
            SET fecha_de_ultimo_acceso = ?
            WHERE id = ?
            """, (fecha_actual, id_db))

            conn.commit()

            print(f"✓ Acceso registrado a: {db_name}")
            print(f"   - Dirección: {direccion}")
            print(f"   - Tipo de usuario: {'Administrador' if tabla_origen == 'dbs' else 'Invitado'}")
            print(f"   - Hora de acceso: {fecha_actual}")
            print(f"   - Origen: {tabla_origen}")
            return True

        except sqlite3.OperationalError as oe:
            intentos += 1
            print(f"\n× Error de operación: {str(oe)}")
            if "no such table" in str(oe):
                print("  ¡Tabla esencial no encontrada!")
                print("  Verifique la estructura de MASTER.db")
                return False
            sleep(espera_base)
            espera_base *= 2

        except sqlite3.Error as e:
            print(f"\n× Error de base de datos: {str(e)}")
            if conn: conn.rollback()
            return False

        finally:
            if conn:
                conn.close()
                print("Conexión cerrada\n" + "-" * 50)
                from reinicio import reinicio_conexion
                reinicio_conexion()

    print(f"\n× Operación fallida después de {max_intentos} intentos")
    return direccion_filtrada
