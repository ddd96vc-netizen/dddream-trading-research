"""
LIMPIEZA DEFINITIVA VIA IBKR - en vez de adivinar por el nombre del
simbolo, le pregunta a Interactive Brokers directamente: "¿reconoces
este ticker?". Los que IBKR confirme que NO existen, se borran de todas
las tablas. Esto captura tanto los de letra duplicada como cualquier
otro tipo de simbolo corrupto que el patron de texto no detectaba.
Requiere IB Gateway abierto y conectado.
"""
import sqlite3
from ib_async import IB, Stock

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta
PUERTO = 4002

conn = sqlite3.connect(DB); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM scanner_results')
simbolos = [r[0] for r in c.fetchall()]
conn.close()

print(f"Consultando {len(simbolos)} tickers en IBKR (esto tarda, pero es rápido por ticker)...\n")

ib = IB()
ib.connect('127.0.0.1', PUERTO, clientId=30)

no_reconocidos = []
for i, sym in enumerate(simbolos, 1):
    try:
        contrato = Stock(sym, 'SMART', 'USD')
        detalles = ib.reqContractDetails(contrato)
        if not detalles:
            no_reconocidos.append(sym)
            print(f"  [{i}/{len(simbolos)}] {sym}: ✗ no reconocido")
    except Exception:
        no_reconocidos.append(sym)
        print(f"  [{i}/{len(simbolos)}] {sym}: ✗ error/no reconocido")
    ib.sleep(0.3)

ib.disconnect()

print(f"\n{'=' * 60}")
print(f"{len(no_reconocidos)} tickers que IBKR NO reconoce:")
print('=' * 60)
for sym in no_reconocidos:
    print(f"  {sym}")

if not no_reconocidos:
    print("\n✓ Todos los tickers fueron reconocidos, nada que limpiar.")
    raise SystemExit

respuesta = input(f"\n¿Borrar estos {len(no_reconocidos)} tickers de TODAS las tablas? (escribe SI para confirmar): ")
if respuesta.strip().upper() != 'SI':
    print("Cancelado, no se borró nada.")
    raise SystemExit

conn = sqlite3.connect(DB); c = conn.cursor()
borrados = 0
for sym in no_reconocidos:
    c.execute('DELETE FROM scanner_results WHERE symbol = ?', (sym,))
    c.execute('DELETE FROM intraday_data WHERE symbol = ?', (sym,))
    try:
        c.execute('DELETE FROM x_tickers WHERE symbol = ?', (sym,))
        c.execute('DELETE FROM x_avistamientos WHERE symbol = ?', (sym,))
    except Exception:
        pass
    try:
        c.execute('DELETE FROM noticias WHERE symbol = ?', (sym,))
    except Exception:
        pass
    borrados += 1
conn.commit()
conn.close()

print(f"\n✓ {borrados} tickers eliminados de todas las tablas.")
print("Ahora vuelve a correr shortable_y_huecos_resumible.py — debería")
print("por fin avanzar con tickers reales en vez de repetir fantasmas.")