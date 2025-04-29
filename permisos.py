from common import *
from rutas import MASTER

def verificar_permisos(db_path):
    """
    Verifica si el usuario actual tiene permisos sobre la base de datos
    Retorna: (bool tiene_permisos, str usuario_db, int db_id)
    """
    try:
        usuario_actual = os.getlogin()
        conn = sqlite3.connect(MASTER)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, usuario_windows 
            FROM dbs 
            WHERE direccion LIKE ? 
        """, (db_path + '%',))

        db_info = cursor.fetchone()

        if db_info:
            db_id, usuario_db = db_info[0], db_info[1]
            return (usuario_actual.lower() == usuario_db.lower(), usuario_db, db_id)

        return (False, None, None)

    except Exception as e:
        print(f"Error verificando permisos: {str(e)}")
        return (False, None, None)
    finally:
        if 'conn' in locals():
            conn.close()


def obtener_solicitudes_pendientes(db_id):
    """
    Obtiene el número de solicitudes pendientes para una base de datos
    """
    try:
        conn = sqlite3.connect(MASTER)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) 
            FROM solicitudes_acceso 
            WHERE db_id = ? 
            AND estatus = 'pendiente'
        """, (db_id,))

        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error obteniendo solicitudes: {str(e)}")
        return 0
    finally:
        if 'conn' in locals():
            conn.close()