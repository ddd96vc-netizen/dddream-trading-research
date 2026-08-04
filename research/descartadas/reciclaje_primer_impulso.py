"""
RECICLAJE — versión CORREGIDA (sin mirar el futuro).
La entrada es al cierre de la vela donde se CONFIRMA el impulso, no en la
vela base. Antes se entraba "antes" de una subida que ya se sabía que
iba a pasar (esa es la señal con la que se detecta el impulso) -- eso es
mirar el futuro. Aquí se mide solo con velas genuinamente posteriores.
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta
COSTE_R = 0.1
UMBRAL = 1.0
VENTANA = 2

def conectar():
    return sqlite3.connect(DB)

def medir_long(velas, entrada, idx, stop_pct, target_pct):
    stop = entrada * (1 - stop_pct / 100)
    target = entrada * (1 + target_pct / 100)
    for v in velas[idx:]:
        if v[3] <= stop: return -1.0
        elif v[2] >= target: return target_pct / stop_pct
    return ((velas[-1][4] - entrada) / entrada * 100) / stop_pct

def detectar_impulsos_dia(velas_dia):
    """Devuelve lista de (fin_idx, precio_entrada_real) por impulso confirmado."""
    impulsos = []
    i = 0
    while i < len(velas_dia) - 1:
        base = velas_dia[i][4]
        mejor_subida = 0
        fin_idx = i
        for j in range(i + 1, min(i + VENTANA + 1, len(velas_dia))):
            alto = velas_dia[j][2]
            subida = ((alto - base) / base) * 100
            if subida > mejor_subida:
                mejor_subida = subida
                fin_idx = j
        if mejor_subida >= UMBRAL:
            entrada_real = velas_dia[fin_idx][4]   # cierre de la vela CONFIRMADA
            impulsos.append((fin_idx, entrada_real))
            i = fin_idx
        else:
            i += 1
    return impulsos

conn = conectar(); c = conn.cursor()
c.execute("SELECT DISTINCT symbol FROM intraday_data WHERE interval='1m'")
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print(f"Cargando {len(simbolos)} tickers (1 minuto)...")

trades_todos = []
trades_primero = []

for sym in simbolos:
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval='1m' ORDER BY datetime''', (sym,))
    datos = c.fetchall(); conn.close()
    if not datos:
        continue
    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[0][:10]].append(d)
    for fecha, velas_full in por_dia.items():
        activas = [v for v in velas_full if (len(v) <= 7 or v[7] in ('pre', 'regular'))]
        if len(activas) < VENTANA:
            continue
        impulsos = detectar_impulsos_dia(activas)
        for pos, (fin_idx, entrada) in enumerate(impulsos):
            trades_todos.append((activas, fin_idx, entrada))
            if pos == 0:
                trades_primero.append((activas, fin_idx, entrada))

print(f"Impulsos totales: {len(trades_todos)} | Solo primeros del día: {len(trades_primero)}\n")

def evaluar(lista_trades, stop_pct, target_pct):
    if len(lista_trades) < 30:
        return None
    total_r = 0
    wins = 0
    for velas, fin_idx, entrada in lista_trades:
        r = medir_long(velas, entrada, fin_idx + 1, stop_pct, target_pct)
        total_r += r
        if r > 0:
            wins += 1
    n = len(lista_trades)
    return {'n': n, 'r_neto': total_r / n - COSTE_R, 'win': wins / n * 100}

print("=" * 70)
print(f"RECICLAJE CORREGIDO (sin lookahead) · coste{COSTE_R}R")
print("=" * 70)
print(f"\n{'Stop':>6}{'Target':>8}{'Grupo':>16}{'N':>7}{'R neto':>11}{'Win%':>7}")
print("-" * 58)
for stop_pct, target_pct in [(1.0, 2.0), (1.0, 3.0), (0.5, 1.5), (1.5, 3.0)]:
    r_todos = evaluar(trades_todos, stop_pct, target_pct)
    r_prim = evaluar(trades_primero, stop_pct, target_pct)
    if r_todos:
        print(f"{stop_pct:>5.1f}%{target_pct:>7.1f}%{'TODOS':>16}{r_todos['n']:>7}{r_todos['r_neto']:>+10.3f}R{r_todos['win']:>6.0f}%")
    if r_prim:
        print(f"{stop_pct:>5.1f}%{target_pct:>7.1f}%{'SOLO 1º DÍA':>16}{r_prim['n']:>7}{r_prim['r_neto']:>+10.3f}R{r_prim['win']:>6.0f}%")
    print()

print("Estos números YA NO deberían tener el R inflado de antes. Compara")
print("con la corrida anterior — si aquí sale ~0 o negativo, confirma que")
print("el bug era el causante de los +0.7R a +1.7R que vimos.")