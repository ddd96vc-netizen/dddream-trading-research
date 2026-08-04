"""
DIAGNOSTICO GAP & GO + RE-VALIDACION FRD/OVEREXT

PARTE 1: lista los trades de Gap & Go con R mas alto, para cazar el
outlier sospechoso que infla el promedio (+1.479R no tiene sentido si
el resto del proyecto ronda +0.1 a +0.4R).

PARTE 2: vuelve a correr First Red Day y Overextended Gap Down SIN el
filtro de perfil, sobre TODOS tus tickers actuales, para comparar contra
los numeros originales y saber si el adelgazamiento visto es real.
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta (misma que tus otros scripts)
COSTE_R = 0.1

def conectar():
    return sqlite3.connect(DB)

def obtener_intradia(symbol, intervalo='5m'):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval=? ORDER BY datetime''', (symbol, intervalo))
    r = c.fetchall(); conn.close()
    return r

def medir_long(velas, entrada, idx, stop_pct, target_pct):
    stop = entrada * (1 - stop_pct / 100)
    target = entrada * (1 + target_pct / 100)
    for v in velas[idx:]:
        if v[3] <= stop: return -1.0
        elif v[2] >= target: return target_pct / stop_pct
    return ((velas[-1][4] - entrada) / entrada * 100) / stop_pct

def medir_short(velas, entrada, idx, stop_pct, target_pct):
    stop = entrada * (1 + stop_pct / 100)
    target = entrada * (1 - target_pct / 100)
    for v in velas[idx:]:
        if v[2] >= stop: return -1.0
        elif v[3] <= target: return target_pct / stop_pct
    return ((entrada - velas[-1][4]) / entrada * 100) / stop_pct

def reconstruir_dias(symbol):
    datos = obtener_intradia(symbol, '5m')
    if not datos:
        return {}
    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[0][:10]].append(d)
    fechas_ordenadas = sorted(por_dia.keys())
    dias = {}
    for fecha in fechas_ordenadas:
        reg = [v for v in por_dia[fecha] if len(v) <= 7 or v[7] == 'regular']
        if not reg:
            continue
        dias[fecha] = {
            'open': reg[0][1], 'high': max(v[2] for v in reg),
            'low': min(v[3] for v in reg), 'close': reg[-1][4],
            'volumen': sum(v[5] or 0 for v in reg), 'velas': reg,
        }
    return dias

conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print(f"Cargando {len(simbolos)} tickers...\n")

# ═══════════ PARTE 1: Diagnóstico Gap & Go ═══════════

def trades_gapgo_detalle(symbol):
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
        hora = reg[ridx][0][11:16]
        rv = rvol30.get(fecha)
        if rv is None or rv <= 1.5:
            continue
        if not ('09:30' <= hora < '10:00'):
            continue
        entrada = reg[ridx][4]
        r = medir_long(reg, entrada, ridx + 1, 2.0, 10.0)
        trades.append({'symbol': symbol, 'fecha': fecha, 'hora': hora, 'entrada': entrada, 'pm_high': pm_high, 'r': r})
    return trades

print("=" * 80)
print("PARTE 1 — DIAGNÓSTICO GAP & GO: buscando outliers")
print("=" * 80)

todos_gapgo = []
for sym in simbolos:
    todos_gapgo.extend(trades_gapgo_detalle(sym))

todos_gapgo.sort(key=lambda t: t['r'], reverse=True)

print(f"\nTotal señales Gap & Go: {len(todos_gapgo)}")
print(f"\nTOP 20 trades con R más alto (revisa si el precio de entrada es raro):\n")
print(f"{'Symbol':<10}{'Fecha':<12}{'Hora':<8}{'Entrada':>12}{'PM High':>12}{'R':>10}")
print("-" * 70)
for t in todos_gapgo[:20]:
    print(f"{t['symbol']:<10}{t['fecha']:<12}{t['hora']:<8}{t['entrada']:>12.4f}{t['pm_high']:>12.4f}{t['r']:>10.2f}")

todos_r = [t['r'] for t in todos_gapgo]
n = len(todos_r)
total = sum(todos_r)
print(f"\nR neto CON todos los trades: {total/n - COSTE_R:+.3f}R ({n} trades)")

for k in [1, 3, 5, 10]:
    sin_top = todos_r[k:]
    if sin_top:
        n2 = len(sin_top)
        total2 = sum(sin_top)
        print(f"R neto SIN el top {k} outlier(s): {total2/n2 - COSTE_R:+.3f}R ({n2} trades)")

print("\nSi el R neto cambia MUCHO al quitar 1-5 outliers, confirma que el")
print("promedio estaba siendo inflado por pocos trades con datos raros.")
print("Revisa esos symbols a mano en /estudio para ver si tienen sentido")
print("(precio de entrada absurdamente bajo/alto = probable dato corrupto).")

# ═══════════ PARTE 2: Re-validar FRD y Overext sin filtro de perfil ═══════════

def trades_frd(symbol, dias):
    fechas = sorted(dias.keys())
    if len(fechas) < 4:
        return []
    trades = []
    for i in range(2, len(fechas) - 1):
        f_p2, f_p1, f_dia, f_op = fechas[i - 2], fechas[i - 1], fechas[i], fechas[i + 1]
        d_p2, d_p1, d_dia, d_op = dias[f_p2], dias[f_p1], dias[f_dia], dias[f_op]
        if not (d_p2['close'] >= d_p2['open'] and d_p1['close'] >= d_p1['open']):
            continue
        if not (d_dia['close'] < d_dia['open'] and d_dia['close'] < d_p1['close']):
            continue
        if not (d_dia['volumen'] < d_p1['volumen']):
            continue
        mn = min(d_p2['low'], d_p1['low']); mx = max(d_p2['high'], d_p1['high'])
        sob = (mx - mn) / mn * 100 if mn > 0 else 0
        if sob < 30.0:
            continue
        velas = d_op['velas']; op = velas[0][1]
        entrada_idx = None
        for k, v in enumerate(velas):
            if v[3] < op:
                entrada_idx = k; break
        if entrada_idx is None:
            continue
        r = medir_short(velas, op, entrada_idx + 1, 3.0, 6.0)
        trades.append(r)
    return trades

def trades_overext(symbol, dias):
    fechas = sorted(dias.keys())
    if len(fechas) < 4:
        return []
    trades = []
    for i in range(1, len(fechas) - 1):
        f_ant, f_dia = fechas[i - 1], fechas[i]
        ant, dia = dias[f_ant], dias[f_dia]
        gap = (ant['close'] - dia['open']) / ant['close'] * 100
        if gap < 2.0:
            continue
        prev = [dias[f] for f in fechas[max(0, i - 2):i]]
        if not prev:
            continue
        mn = min(d['low'] for d in prev); mx = max(d['high'] for d in prev)
        sob = (mx - mn) / mn * 100 if mn > 0 else 0
        if sob < 50.0:
            continue
        velas = dia['velas']
        entrada_idx, entrada_precio = None, None
        for k, v in enumerate(velas):
            if v[2] >= ant['close'] * 0.98:
                entrada_precio, entrada_idx = v[4], k; break
        if entrada_idx is None:
            continue
        r = medir_short(velas, entrada_precio, entrada_idx + 1, 3.0, 6.0)
        trades.append(r)
    return trades

print("\n" + "=" * 80)
print("PARTE 2 — RE-VALIDACIÓN First Red Day y Overextended Gap Down")
print("(sin filtro de perfil, sobre TODOS tus tickers actuales)")
print("=" * 80)

todos_frd = []
todos_overext = []
for sym in simbolos:
    dias = reconstruir_dias(sym)
    todos_frd.extend(trades_frd(sym, dias))
    todos_overext.extend(trades_overext(sym, dias))

def resumen(nombre, lista, r_antes, n_antes):
    if not lista:
        print(f"\n{nombre}: sin trades")
        return
    n = len(lista)
    total = sum(lista)
    wins = sum(1 for r in lista if r > 0)
    r_neto = total / n - COSTE_R
    print(f"\n{nombre}")
    print(f"  Antes:  {r_antes:+.3f}R  ({n_antes} trades)")
    print(f"  Ahora:  {r_neto:+.3f}R  ({n} trades)  win {wins/n*100:.0f}%")
    print(f"  Diferencia: {r_neto - r_antes:+.3f}R")

resumen("FIRST RED DAY (short)", todos_frd, 0.453, 50)
resumen("OVEREXTENDED GAP DOWN (short)", todos_overext, 0.400, 54)

print("\n" + "=" * 80)
print("Si el R 'ahora' se parece a los +0.202R / +0.115R que vimos con el")
print("experimento de perfil, confirma que el adelgazamiento es real (más")
print("muestra = verdad estadística). Si sale distinto, el experimento de")
print("perfil tenía algún sesgo en cómo agrupaba los trades.")