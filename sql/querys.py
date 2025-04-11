import sqlite3

# Conectar a la base de datos
conn = sqlite3.connect(r'\\mercury\Mtto_Prod\00_Departamento_Mantenimiento\Minutas\minutas.db')
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
    print(f"Primeros dos registros de tabla '{table_name}': {records}")

# Obtener los queries de relaciones (foreign keys)
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql LIKE '%FOREIGN KEY%'")
foreign_keys_queries = cursor.fetchall()

# Obtener los queries de triggers
cursor.execute("SELECT sql FROM sqlite_master WHERE type='trigger'")
triggers_queries = cursor.fetchall()

# Cerrar la conexión
conn.close()
