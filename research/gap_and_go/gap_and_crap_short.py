"""
GAP AND CRAP — pata en corto. Después de un Gap & Go válido (RVOL alto +
primera media hora, tu edge ya confirmado), si MÁS TARDE ese mismo día
el precio pierde el VWAP con una vela de volumen por encima de lo normal
visto hasta ese momento, se abre una segunda pata en CORTO desde ahí
hasta el cierre del día (o hasta tocar stop/target).
Primera prueba exploratoria -- si sobrevive, se optimiza y valida fuera
de muestra como las demás.
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta (misma que tus otros scripts)
COSTE_R = 0.1
VOL_MULT = 1.3   # la vela de pérdida de VWAP debe tener >= 1.3x el volumen promedio visto hasta ese punto

def conectar():
    return sqlite3.connect(DB)

def obtener_intradia(symbol, intervalo='5m'):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval=? ORDER BY datetime''', (symbol, intervalo))
    r = c.fetchall(); conn.close()
    return r

def medir_short(velas, entrada, idx, stop_pct, target_pct):
    stop = entrada * (1 + stop_pct / 100)
    target = entrada * (1 - target_pct / 100)
    for v in velas[idx:]:
        if v[2] >= stop: return -1.0
        elif v[3] <= target: return target_pct / stop_pct
    return ((entrada - velas[-1][4]) / entrada * 100) / stop_pct

def señales_gapgo_short_leg(symbol, stop_pct, target_pct):
    datos = obtener_intradia(symbol, '5m')
    if not datos:
        return []
    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[0][:10]].append(d)

    vol30 = defaultdict(int)
    for d in datos:
        fecha, hm = d[0][:10], d[0][11:16]
        ses = d[7] if len(d) > 7 and d[7] else 'regular'
        if ses == 'regular' and '09:30' <= hm < '10:00':
            vol30[fecha] += (d[5] or 0)
    dias_ord = sorted(vol30.keys()); rvol30 = {}; acum = []
    for dia in dias_ord:
        v = vol30[dia]
        rvol30[dia] = round(v / (sum(acum) / len(acum)), 2) if acum and sum(acum) > 0 else None
        if v > 0:
            acum.append(v)

    trades = []
    for fecha, velas in por_dia.items():
        pre = [v for v in velas if len(v) > 7 and v[7] == 'pre']
        reg = [v for v in velas if len(v) <= 7 or v[7] == 'regular']
        if not pre or not reg:
            continue
        pm_high = max(v[2] for v in pre)
        ridx = None
        for i, v in enumerate(reg):
            if v[4] > pm_high:
                ridx = i; break
        if ridx is None:
            continue

        # Filtro del Gap & Go ya validado: RVOL alto + primera media hora
        hora = reg[ridx][0][11:16]
        rv = rvol30.get(fecha)
        if rv is None or rv <= 1.5:
            continue
        if not ('09:30' <= hora < '10:00'):
            continue

        # Buscar, DESPUÉS de la entrada larga, la pérdida de VWAP con volumen alto
        vols_vistos = [(reg[k][5] or 0) for k in range(ridx + 1)]
        eidx, ep = None, None
        for k in range(ridx + 1, len(reg)):
            v = reg[k]
            vwap = v[6]
            if vwap is None:
                vols_vistos.append(v[5] or 0)
                continue
            vol_prom = sum(vols_vistos) / len(vols_vistos) if vols_vistos else 0
            if v[4] < vwap and vol_prom > 0 and (v[5] or 0) >= vol_prom * VOL_MULT:
                ep, eidx = v[4], k
                break
            vols_vistos.append(v[5] or 0)
        if eidx is None:
            continue

        r = medir_short(reg, ep, eidx + 1, stop_pct, target_pct)
        trades.append({'symbol': symbol, 'fecha': fecha, 'hora_entrada': reg[eidx][0][11:16], 'entrada': ep, 'r': r})
    return trades

conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print(f"Cargando {len(simbolos)} tickers...\n")
print("=" * 70)
print("GAP AND CRAP — pata en corto tras perder VWAP con volumen")
print("=" * 70)

# Probar varias combinaciones de stop/target, es la primera vez que se mide esto
combinaciones = [(2.0, 4.0), (2.0, 6.0), (3.0, 6.0), (3.0, 8.0)]

for stop_pct, target_pct in combinaciones:
    todos = []
    for sym in simbolos:
        todos.extend(señales_gapgo_short_leg(sym, stop_pct, target_pct))

    if len(todos) < 15:
        print(f"\nstop={stop_pct}% target={target_pct}%: muestra insuficiente ({len(todos)})")
        continue

    n = len(todos)
    total = sum(t['r'] for t in todos)
    wins = sum(1 for t in todos if t['r'] > 0)
    print(f"\nstop={stop_pct}% target={target_pct}%")
    print(f"  N={n} trades | R neto={total/n - COSTE_R:+.3f}R | win={wins/n*100:.0f}%")

print("\n" + "=" * 70)
print("Si alguna combinación da R neto positivo con muestra decente (30+),")
print("vale la pena optimizarla y pasarla por validación fuera de muestra")
print("antes de confiar en ella -- igual que las otras 3.")