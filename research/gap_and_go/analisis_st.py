"""
Análisis 2: probar stop/target sobre el edge afinado:
RVOL alto (>1.5x) + primera media hora (9:30-10:00).
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'
COSTE_R = 0.1

def conectar():
    return sqlite3.connect(DB)

def obtener_intradia(symbol):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval='5m' ORDER BY datetime''', (symbol,))
    r = c.fetchall(); conn.close()
    return r

def rvol_30_por_dia(datos):
    vol_30 = defaultdict(int)
    for d in datos:
        fecha, hm = d[0][:10], d[0][11:16]
        sesion = d[7] if len(d) > 7 and d[7] else 'regular'
        if sesion == 'regular' and '09:30' <= hm < '10:00':
            vol_30[fecha] += (d[5] or 0)
    dias = sorted(vol_30.keys()); res, acum = {}, []
    for dia in dias:
        v = vol_30[dia]
        res[dia] = round(v/(sum(acum)/len(acum)), 2) if acum and sum(acum) > 0 else None
        if v > 0: acum.append(v)
    return res

# Recopilar roturas UNA vez (con sus velas posteriores) para el edge afinado
conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

roturas = []
for sym in simbolos:
    datos = obtener_intradia(sym)
    if not datos: continue
    rvol30 = rvol_30_por_dia(datos)
    por_dia = defaultdict(list)
    for d in datos: por_dia[d[0][:10]].append(d)
    for fecha, velas in por_dia.items():
        pre = [v for v in velas if len(v) > 7 and v[7] == 'pre']
        regular = [v for v in velas if len(v) <= 7 or v[7] == 'regular']
        if not pre or not regular: continue
        pm_high = max(v[2] for v in pre)
        ridx = None
        for i, v in enumerate(regular):
            if v[4] > pm_high: ridx = i; break
        if ridx is None: continue
        hora = regular[ridx][0][11:16]
        # FILTRO: RVOL alto + primera media hora
        rv = rvol30.get(fecha)
        if rv is None or rv <= 1.5: continue
        if not ('09:30' <= hora < '10:00'): continue
        post = regular[ridx+1:]
        roturas.append({
            'entrada': regular[ridx][4],
            'highs': [v[2] for v in post],
            'lows': [v[3] for v in post],
            'cierre': regular[-1][4],
        })

print(f"Roturas del edge afinado (RVOL alto + 9:30-10:00): {len(roturas)}\n")

def medir(stop_pct, target_pct):
    tr = 0; n = 0; w = 0
    for r in roturas:
        entrada = r['entrada']
        stop = entrada*(1-stop_pct/100); target = entrada*(1+target_pct/100)
        res = None
        for j in range(len(r['highs'])):
            if r['lows'][j] <= stop: res = -1.0; break
            elif r['highs'][j] >= target: res = target_pct/stop_pct; break
        if res is None:
            res = ((r['cierre']-entrada)/entrada*100)/stop_pct
        tr += res; n += 1
        if res > 0: w += 1
    return (tr/n, tr/n - COSTE_R, w/n*100, n) if n else None

# Probar combinaciones (stop 2-5, target 3-10)
combos = []
for stop in [2.0, 2.5, 3.0, 3.5, 4.0]:
    for target in [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]:
        if target <= stop: continue
        e = medir(stop, target)
        if e:
            combos.append((stop, target, round(target/stop,2), e[0], e[1], e[2], e[3]))

combos.sort(key=lambda x: x[4], reverse=True)

print("TOP 10 stop/target sobre el edge afinado:")
print(f"\n{'Stop':>5}{'Target':>8}{'Ratio':>7}{'R bruto':>11}{'R neto':>11}{'Win%':>7}{'N':>6}")
print("-"*60)
for stop, target, ratio, rb, rn, w, n in combos[:10]:
    print(f"{stop:>4.1f}%{target:>7.1f}%{ratio:>6.1f}{rb:>+10.3f}R{rn:>+10.3f}R{w:>6.0f}%{n:>6}")
