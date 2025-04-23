import sqlite3
# Conectar a la base de datos
from rutas import DB_PATH
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Obtener los queries de creación de tablas
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
tables_creation_queries = cursor.fetchall()

# Obtener los nombres de las tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

# Obtener los primeros tres registros de cada tabla
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
    records = cursor.fetchall()
    # print(f"Primeros dos registros de tabla '{table_name}': {records}")

# Obtener los queries de relaciones (foreign keys)
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql LIKE '%FOREIGN KEY%'")
foreign_keys_queries = cursor.fetchall()

# Obtener los queries de triggers
cursor.execute("SELECT sql FROM sqlite_master WHERE type='trigger'")
triggers_queries = cursor.fetchall()

# Cerrar la conexión
conn.close()

tabla_acuerdos = '''
                CREATE TABLE IF NOT EXISTS acuerdos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_acuerdo TEXT NOT NULL,
                    acuerdo TEXT NOT NULL,
                    responsables TEXT NOT NULL,
                    fecha_compromiso TEXT NOT NULL,
                    fecha_registro TEXT NOT NULL,
                    usuario_registra TEXT NOT NULL,
                    estatus TEXT NOT NULL DEFAULT 'Activo',
                    fecha_estatus TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    comentarios_cierre TEXT DEFAULT '',
                    comentarios TEXT DEFAULT '',
                    accion TEXT DEFAULT 'Cerrar'
                )
            '''
historial_acuerdos = '''
                CREATE TABLE IF NOT EXISTS historial_acuerdos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_acuerdo TEXT NOT NULL,
                    acuerdo TEXT NOT NULL,
                    responsables TEXT NOT NULL,
                    fecha_compromiso TEXT NOT NULL,
                    fecha_modificacion TEXT NOT NULL,
                    usuario_modifico TEXT NOT NULL,
                    estatus TEXT NOT NULL,
                    comentarios_cierre TEXT DEFAULT '',
                    comentarios TEXT DEFAULT '',
                    ruta_pdf TEXT,
                    FOREIGN KEY (id_acuerdo) REFERENCES acuerdos(id_acuerdo)
                )
            '''

usuarios = '''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    fecha_registro TEXT NOT NULL, -- Formato ISO 8601: 'YYYY-MM-DD HH:MM:SS'
                    usuario_registra TEXT NOT NULL,
                    estatus TEXT
)
'''

usuarios_prioridad_sin_eliminados = """ WITH RECURSIVE split_responsables AS (
    SELECT 
        substr(responsables || ',', 0, instr(responsables || ',', ',')) AS nombre,
        substr(responsables, instr(responsables || ',', ',') + 1) AS remaining
    FROM acuerdos
    WHERE responsables != '' AND responsables IS NOT NULL

    UNION ALL

    SELECT
        substr(remaining, 0, instr(remaining || ',', ',')),
        substr(remaining, instr(remaining || ',', ',') + 1)
    FROM split_responsables
    WHERE remaining != ''
)
SELECT DISTINCT trim(nombre) AS nombre
FROM split_responsables
WHERE nombre != ''
AND nombre IN (
    SELECT nombre 
    FROM usuarios
    WHERE estatus != 'Eliminado'
)
UNION
SELECT DISTINCT nombre 
FROM usuarios
WHERE estatus = 'Activo'
ORDER BY nombre COLLATE NOCASE ASC;
"""