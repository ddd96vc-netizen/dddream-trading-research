"""
GREEN TO RED — prueba la condición real de "destrucción" (no sobreextensión).
Mide: en el momento del cruce verde->rojo, ¿cuánto % de la extensión previa
(high-low de los días previos) ya se retrocedió? Si es >= destruccion_min%,
cuenta la señal. Esto es DISTINTO de exigir que la subida previa fuera grande.
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'
COSTE_R = 0.1
STOP_PCT = 3.0
TARGET_PCT = 6.0

def conectar():
    return sqlite3.connect(DB)

def reconstruir_dias(symbol):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval='5m' ORDER BY datetime''', (symbol,))
    datos = c.fetchall(); conn.close()
    if not datos: return []
    por_dia = defaultdict(list)
    for d in datos: por_dia[d[0][:10]].append(d)
    dias = []
    for fecha in sorted(por_dia.keys()):
        reg = [v for v in por_dia[fecha] if len(v) <= 7 or v[7] == 'regular']
        if not reg: continue
        dias.append({
            'fecha': fecha, 'open': reg[0][1], 'high': max(v[2] for v in reg),
            'low': min(v[3] for v in reg), 'close': reg[-1][4], 'velas': reg,
        })
    return dias

def medir_short(velas, entrada, idx):
    stop = entrada*(1+STOP_PCT/100); target = entrada*(1-TARGET_PCT/100)
    for v in velas[idx:]:
        if v[2] >= stop: return -1.0
        elif v[3] <= target: return TARGET_PCT/STOP_PCT
    return ((entrada - velas[-1][4])/entrada*100)/STOP_PCT

def detectar(dias, dias_sob, destruccion_min):
    """Devuelve lista de R para cruces verde->rojo con destrucción >= umbral."""
    resultados = []
    for i in range(dias_sob, len(dias)):
        dia = dias[i]
        prev = dias[i-dias_sob:i]
        ext_high = max(d['high'] for d in prev)
        ext_low = min(d['low'] for d in prev)
        rango = ext_high - ext_low
        if rango <= 0: continue

        ant = dias[i-1]
        if dia['open'] <= ant['close']:
            continue  # tiene que abrir verde

        velas = dia['velas']
        for k, v in enumerate(velas):
            if v[4] < ant['close']:  # cruce a rojo
                precio_cruce = v[4]
                destruccion = (ext_high - precio_cruce) / rango * 100
                if destruccion >= destruccion_min:
                    r = medir_short(velas, precio_cruce, k+1)
                    resultados.append(r)
                break  # solo el primer cruce del día
    return resultados

# ── Recopilar días de todos los tickers ──
conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print(f"Cargando {len(simbolos)} tickers...")
dias_por_ticker = {}
for sym in simbolos:
    d = reconstruir_dias(sym)
    if len(d) > 4:
        dias_por_ticker[sym] = d

# ── Probar combinaciones: dias_sob x destruccion_min ──
print("Probando combinaciones de destrucción...\n")
resultados_finales = []

for dias_sob in [2, 3]:
    for destruccion_min in [0, 30, 50, 70]:
        todos_r = []
        for sym, dias in dias_por_ticker.items():
            todos_r.extend(detectar(dias, dias_sob, destruccion_min))
        n = len(todos_r)
        if n < 30:
            continue
        total = sum(todos_r)
        wins = sum(1 for r in todos_r if r > 0)
        resultados_finales.append({
            'dias_sob': dias_sob, 'destruccion_min': destruccion_min,
            'n': n, 'r_neto': total/n - COSTE_R, 'win': wins/n*100,
        })

resultados_finales.sort(key=lambda x: x['r_neto'], reverse=True)

print("="*72)
print(f"GREEN TO RED · condición de DESTRUCCIÓN real · stop{STOP_PCT}/target{TARGET_PCT} · coste{COSTE_R}R")
print("="*72)
print(f"\n{'DíasSob':<10}{'Destrucción≥':<14}{'N':>7}{'R neto':>11}{'Win%':>8}")
print("-"*50)
for r in resultados_finales:
    print(f"{r['dias_sob']:<10}{r['destruccion_min']:<14}{r['n']:>7}{r['r_neto']:>+10.3f}R{r['win']:>7.0f}%")

print(f"\nTotal combinaciones con muestra suficiente: {len(resultados_finales)}")
print("\nCompara la fila 'destrucción≥0' (equivale a sin filtro) contra las")
print("demás — si destrucción alta mejora claramente el R, el matiz de Edu")
print("Trades era real y distinto de lo que ya habíamos probado (sobreext).")
