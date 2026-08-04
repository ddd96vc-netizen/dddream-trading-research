"""
VALIDACIÓN DEL FILTRO DE FLOAT sobre los edges.
Prueba si añadir 'float bajo' mejora:
  - Gap & Go LONG (con RVOL alto + primera media hora)
  - First Red Day SHORT (con sobreextensión)

Requiere que scanner_results tenga float_shares poblado (rellenar con Finviz antes).

Cómo correr: coloca este archivo junto a dddream.db y ejecuta:
    python validar_float.py

Ajusta DB abajo si tu base de datos está en otra ruta.
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'   # <-- AJUSTA la ruta a tu base de datos
COSTE_R = 0.1

def conectar():
    return sqlite3.connect(DB)

# ── Float por ticker (en millones) desde scanner_results ──
def float_por_ticker():
    conn = conectar(); c = conn.cursor()
    c.execute('SELECT symbol, float_shares FROM scanner_results WHERE float_shares IS NOT NULL')
    fl = {}
    for sym, f in c.fetchall():
        fl[sym] = f / 1e6
    conn.close()
    return fl

def obtener_intradia(symbol):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval='5m' ORDER BY datetime''', (symbol,))
    r = c.fetchall(); conn.close()
    return r

def rvol_30(datos):
    vol30 = defaultdict(int)
    for d in datos:
        fecha, hm = d[0][:10], d[0][11:16]
        ses = d[7] if len(d) > 7 and d[7] else 'regular'
        if ses == 'regular' and '09:30' <= hm < '10:00':
            vol30[fecha] += (d[5] or 0)
    dias = sorted(vol30.keys()); res, acum = {}, []
    for dia in dias:
        v = vol30[dia]
        res[dia] = round(v/(sum(acum)/len(acum)), 2) if acum and sum(acum) > 0 else None
        if v > 0: acum.append(v)
    return res

# ══════════════════ GAP & GO LONG ══════════════════
def trades_gapgo(floats, stop_pct=2.0, target_pct=5.0):
    conn = conectar(); c = conn.cursor()
    c.execute('SELECT DISTINCT symbol FROM intraday_data')
    simbolos = [r[0] for r in c.fetchall()]; conn.close()

    trades = []
    for sym in simbolos:
        datos = obtener_intradia(sym)
        if not datos: continue
        rv = rvol_30(datos)
        fl = floats.get(sym)
        por_dia = defaultdict(list)
        for d in datos: por_dia[d[0][:10]].append(d)
        for fecha, velas in por_dia.items():
            pre = [v for v in velas if len(v) > 7 and v[7] == 'pre']
            reg = [v for v in velas if len(v) <= 7 or v[7] == 'regular']
            if not pre or not reg: continue
            pmh = max(v[2] for v in pre)
            ridx = None
            for i, v in enumerate(reg):
                if v[4] > pmh: ridx = i; break
            if ridx is None: continue
            hora = reg[ridx][0][11:16]
            # FILTRO base del edge: RVOL alto + primera media hora
            r_rvol = rv.get(fecha)
            if r_rvol is None or r_rvol <= 1.5: continue
            if not ('09:30' <= hora < '10:00'): continue
            entrada = reg[ridx][4]
            stop = entrada*(1-stop_pct/100); target = entrada*(1+target_pct/100)
            res = None
            for j in range(ridx+1, len(reg)):
                if reg[j][3] <= stop: res = -1.0; break
                elif reg[j][2] >= target: res = target_pct/stop_pct; break
            if res is None:
                res = ((reg[-1][4]-entrada)/entrada*100)/stop_pct
            trades.append({'r': res, 'float_M': fl})
    return trades

def evaluar(grupo, nombre):
    con_float = [t for t in grupo if t['float_M'] is not None]
    n = len(con_float)
    if n < 30:
        return f"{nombre:<32}{n:>6}   (muestra insuficiente)"
    total = sum(t['r'] for t in con_float)
    wins = sum(1 for t in con_float if t['r'] > 0)
    r_esp = total/n
    return f"{nombre:<32}{n:>6}{r_esp:>+9.3f}R{r_esp-COSTE_R:>+9.3f}R{wins/n*100:>6.0f}%"

print("Cargando float de Finviz (scanner_results)...")
floats = float_por_ticker()
print(f"  {len(floats)} tickers con float\n")

print("Analizando Gap & Go (RVOL alto + primera media hora)...")
tg = trades_gapgo(floats)

print("\n" + "="*66)
print("GAP & GO LONG · efecto del FLOAT · stop2%/target5% · coste 0.1R")
print("="*66)
print(f"\n{'Filtro float':<32}{'N':>6}{'R bruto':>10}{'R neto':>9}{'Win%':>7}")
print("-"*64)
print(evaluar(tg, "Sin filtro de float"))
print(evaluar([t for t in tg if t['float_M'] and t['float_M'] < 10], "Float < 10M"))
print(evaluar([t for t in tg if t['float_M'] and t['float_M'] < 20], "Float < 20M"))
print(evaluar([t for t in tg if t['float_M'] and t['float_M'] < 50], "Float < 50M"))
print(evaluar([t for t in tg if t['float_M'] and t['float_M'] >= 50], "Float >= 50M (alto)"))

print("\n\nLeyenda: si 'Float < 20M' tiene mejor R neto que 'Sin filtro',")
print("entonces el float bajo mejora el edge. Si es igual o peor, no aporta.")
