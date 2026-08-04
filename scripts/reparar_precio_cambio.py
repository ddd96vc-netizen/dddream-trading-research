"""
REPARAR PRECIO/CAMBIO% - rellena change_pct y price en scanner_results
para tickers que se quedaron sin esos datos (el mismo respaldo que se
parcheo en agregar_ticker_manual, aplicado retroactivamente a lo que ya
tienes guardado). Solo toca los campos vacios, no sobreescribe nada.
"""
import sqlite3
import yfinance as yf

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta (misma que tus otros scripts)

def conectar():
    return sqlite3.connect(DB)

conn = conectar(); c = conn.cursor()
c.execute('''
    SELECT DISTINCT symbol FROM scanner_results
    WHERE change_pct IS NULL OR price IS NULL
''')
simbolos = [r[0] for r in c.fetchall()]
conn.close()

print(f"Reparando {len(simbolos)} tickers sin price/change_pct...\n")

reparados = 0
fallidos = []

for i, symbol in enumerate(simbolos, 1):
    try:
        hist = yf.Ticker(symbol).history(period='2d')
        change_pct = None
        price = None

        if len(hist) >= 2:
            close_ayer = hist['Close'].iloc[-2]
            open_hoy = hist['Open'].iloc[-1]
            change_pct = round(((open_hoy - close_ayer) / close_ayer) * 100, 2)
            price = round(float(hist['Close'].iloc[-1]), 4)
        elif len(hist) == 1:
            open_p = hist['Open'].iloc[-1]
            close_p = hist['Close'].iloc[-1]
            change_pct = round(((close_p - open_p) / open_p) * 100, 2)
            price = round(float(close_p), 4)
        else:
            print(f"  [{i}/{len(simbolos)}] {symbol}: sin historico en yfinance")
            fallidos.append(symbol)
            continue

        conn = conectar(); c = conn.cursor()
        c.execute('''
            UPDATE scanner_results
            SET change_pct = COALESCE(change_pct, ?),
                price = COALESCE(price, ?)
            WHERE symbol = ?
        ''', (change_pct, price, symbol))
        conn.commit()
        conn.close()

        print(f"  OK [{i}/{len(simbolos)}] {symbol}: price=${price} change={change_pct}%")
        reparados += 1

    except Exception as e:
        print(f"  ERROR [{i}/{len(simbolos)}] {symbol}: {e}")
        fallidos.append(symbol)

print(f"\n{reparados} reparados, {len(fallidos)} fallidos")
if fallidos:
    print(f"Sin arreglar: {fallidos}")
