"""
VWAP BOUNCE — validación con datos reales (nunca se había corrido).
Detecta rebotes en VWAP (vela cuyo low toca/cruza el VWAP pero cierra por
encima) y mide R real con varias combinaciones de stop/target.
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta
COSTE_R = 0.1

def conectar():
    return sqlite3.connect(DB)

def medir_long(velas, entrada, idx, stop_pct, target_pct):
    stop = entrada * (1 - stop_pct / 100)
    target = entrada * (1 + target_pct / 100)
    for v in velas[idx:]:
        if v[3] <= stop: return -1.0
        elif v[2] >= target: return target_pct / stop_pct
    return ((velas[-1][4] - entrada) / entrada * 100) / stop_pct

def detectar_rebotes(symbol):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval='5m' ORDER BY datetime''', (symbol,))
    datos = c.fetchall(); conn.close()
    if not datos:
        return []
    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[0][:10]].append(d)
    señales = []
    for fecha, velas in por_dia.items():
        regular = [v for v in velas if (len(v) <= 7 or v[7] == 'regular') and v[6] is not None]
        if len(regular) < 3:
            continue
        for i, v in enumerate(regular):
            low, close, vwap = v[3], v[4], v[6]
            if vwap is None:
                continue
            if low <= vwap and close > vwap:
                señales.append((regular, i, close))
    return señales

conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print(f"Cargando {len(simbolos)} tickers...")
todas = []
for sym in simbolos:
    todas.extend(detectar_rebotes(sym))

print(f"Total rebotes de VWAP: {len(todas)}\n")

def evaluar(lista, stop_pct, target_pct):
    if len(lista) < 30:
        return None
    total = 0
    wins = 0
    for velas, idx, entrada in lista:
        r = medir_long(velas, entrada, idx + 1, stop_pct, target_pct)
        total += r
        if r > 0:
            wins += 1
    n = len(lista)
    return {'n': n, 'r_neto': total / n - COSTE_R, 'win': wins / n * 100}

print("=" * 66)
print(f"VWAP BOUNCE · validación con datos reales · coste{COSTE_R}R")
print("=" * 66)
print(f"\n{'Stop':>6}{'Target':>8}{'N':>8}{'R neto':>11}{'Win%':>7}")
print("-" * 42)
for stop_pct, target_pct in [(1.0, 2.0), (1.5, 3.0), (2.0, 4.0), (2.0, 5.0), (2.5, 5.0), (3.0, 6.0)]:
    r = evaluar(todas, stop_pct, target_pct)
    if r:
        print(f"{stop_pct:>5.1f}%{target_pct:>7.1f}%{r['n']:>8}{r['r_neto']:>+10.3f}R{r['win']:>6.0f}%")

print("\nSi todas las filas son negativas, VWAP Bounce (tal como está)")
print("no tiene edge, igual que Green to Red / VWAP Rejection / Reciclaje.")
