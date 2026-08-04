"""
First Red Day (SHORT) con 3 ENTRADAS REALISTAS (sin mirar el futuro).
La decisión de shortear se toma DURANTE el día siguiente al patrón,
o intradía cuando el precio confirma debilidad.

Entradas:
  A) 'pierde_open'  -> shortear cuando el precio pierde el open del día
  B) 'pierde_vwap'  -> shortear cuando pierde el VWAP
  C) 'dia_siguiente'-> shortear en la apertura del día siguiente al rojo

Clave anti-lookahead: el 'primer día rojo' se confirma AL CIERRE (pasado).
La operativa ocurre en el día SIGUIENTE (D+1), que es el back side.
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'
COSTE_R = 0.1
STOP_PCT = 3.0
TARGET_PCT = 6.0

# Filtro fijo (el más lógico): rojo por ambas definiciones
MIN_VERDES = 2  # 2+ días verdes antes del rojo

def conectar():
    return sqlite3.connect(DB)

def reconstruir_dias(symbol):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval='5m' ORDER BY datetime''', (symbol,))
    datos = c.fetchall(); conn.close()
    if not datos:
        return []
    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[0][:10]].append(d)
    dias = []
    for fecha in sorted(por_dia.keys()):
        regular = [v for v in por_dia[fecha] if len(v) <= 7 or v[7] == 'regular']
        if not regular:
            continue
        dias.append({
            'fecha': fecha,
            'open': regular[0][1],
            'high': max(v[2] for v in regular),
            'low': min(v[3] for v in regular),
            'close': regular[-1][4],
            'volumen': sum(v[5] or 0 for v in regular),
            'velas': regular,
        })
    return dias

def es_verde(dia):
    return dia['close'] >= dia['open']

def es_first_red_day(dias, i):
    """¿El día i es un first red day tras MIN_VERDES verdes? (rojo por ambas)"""
    if i < MIN_VERDES:
        return False
    previos = dias[i-MIN_VERDES:i]
    if not all(es_verde(d) for d in previos):
        return False
    dia, ant = dias[i], dias[i-1]
    rojo_apertura = dia['close'] < dia['open']
    rojo_cierre_ant = dia['close'] < ant['close']
    return rojo_apertura and rojo_cierre_ant

def medir_short(velas, entrada, idx_desde):
    """Mide R en corto desde una entrada, recorriendo velas[idx_desde:]."""
    stop = entrada * (1 + STOP_PCT/100)
    target = entrada * (1 - TARGET_PCT/100)
    for v in velas[idx_desde:]:
        if v[2] >= stop:   # high toca stop (subió)
            return -1.0
        elif v[3] <= target:  # low toca target (bajó)
            return TARGET_PCT/STOP_PCT
    cierre = velas[-1][4]
    return ((entrada - cierre)/entrada*100) / STOP_PCT

def trade_pierde_open(dia_op):
    """Entrada cuando el precio pierde el open del día (D+1)."""
    velas = dia_op['velas']
    op = velas[0][1]
    for k, v in enumerate(velas):
        if v[3] < op:  # low cae por debajo del open
            return medir_short(velas, op, k+1)
    return None

def trade_pierde_vwap(dia_op):
    """Entrada cuando el precio pierde el VWAP (D+1)."""
    velas = dia_op['velas']
    for k, v in enumerate(velas):
        vwap = v[6]
        if vwap is not None and v[4] < vwap:  # close bajo VWAP
            return medir_short(velas, v[4], k+1)
    return None

def trade_dia_siguiente(dia_op):
    """Entrada en la apertura del día siguiente."""
    velas = dia_op['velas']
    op = velas[0][1]
    return medir_short(velas, op, 1)

# ── Recopilar ──
conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print(f"Analizando {len(simbolos)} tickers (First Red Day, {MIN_VERDES}+ verdes, rojo ambas)...\n")

entradas = {'pierde_open': [], 'pierde_vwap': [], 'dia_siguiente': []}

for sym in simbolos:
    dias = reconstruir_dias(sym)
    for i in range(len(dias)-1):
        if es_first_red_day(dias, i):
            # La operativa es en D+1 (el día siguiente al rojo confirmado)
            dia_op = dias[i+1]
            for nombre, fn in [('pierde_open', trade_pierde_open),
                               ('pierde_vwap', trade_pierde_vwap),
                               ('dia_siguiente', trade_dia_siguiente)]:
                r = fn(dia_op)
                if r is not None:
                    entradas[nombre].append(r)

print("="*70)
print(f"FIRST RED DAY SHORT · entrada en D+1 · stop {STOP_PCT}%/target {TARGET_PCT}% · coste {COSTE_R}R")
print("="*70)
print(f"\n{'Tipo entrada':<16}{'N':>7}{'R bruto':>11}{'R neto':>11}{'Win%':>8}")
print("-"*53)

res = []
for nombre, trades in entradas.items():
    n = len(trades)
    if n < 30:
        print(f"{nombre:<16}{n:>7}   (muestra insuficiente)")
        continue
    total = sum(trades)
    wins = sum(1 for r in trades if r > 0)
    r_esp = total/n
    res.append((nombre, n, r_esp, r_esp-COSTE_R, wins/n*100))

for nombre, n, rb, rn, w in sorted(res, key=lambda x: x[3], reverse=True):
    print(f"{nombre:<16}{n:>7}{rb:>+10.3f}R{rn:>+10.3f}R{w:>7.0f}%")
