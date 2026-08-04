import sqlite3

DB = 'dddream.db'   # <-- usa la MISMA ruta que ya tienes funcionando en tus otros scripts

conn = sqlite3.connect(DB)
cursor = conn.cursor()
cursor.execute('DELETE FROM noticias')
conn.commit()
borradas = cursor.rowcount
conn.close()
print(f"✓ {borradas} noticias borradas. Ahora vuelve a correr noticias_lote.py para traerlas todas de nuevo, ya con hora.")