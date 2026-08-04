"""
OPTIMIZADOR DE ESTRATEGIAS (estilo StrategyQuant / MetaTrader Optimizer)
-- version con rango de stop/target mas amplio y exportacion COMPLETA
a CSV (todas las combinaciones, no solo el top 10) para analizar aparte.

AVISO: con el rango ampliado esto tarda MAS que la version anterior.
Verás el progreso en pantalla. Déjalo correr tranquilo.
"""
import sqlite3
import csv
from collections import defaultdict

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta (misma que tus otros scripts)
COSTE_R = 0.1
N_MINIMO = 15   # descarta combinaciones con menos trades que esto (evita ruido)

def conectar():
    return sqlite3.connect(DB)

def obtener_intradia(symbol, intervalo='5m'):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval=? ORDER BY datetime''', (symbol, intervalo))
    r = c.fetchall(); conn.close()
    return r

conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()
print(f"Universo: {len(simbolos)} tickers\n")

def barrer_stop_target(señales, valores_stop, valores_target, direccion):
    resultados = []
    for stop_pct in valores_stop:
        for target_pct in valores_target:
            total = 0; n = 0; wins = 0
            for s in señales:
                entrada = s['entrada']
                if direccion == 'long':
                    stop = entrada * (1 - stop_pct / 100); target = entrada * (1 + target_pct / 100)
                else:
                    stop = entrada * (1 + stop_pct / 100); target = entrada * (1 - target_pct / 100)
                r = None
                for j in range(len(s['highs'])):
                    if direccion == 'long':
                        if s['lows'][j] <= stop: r = -1.0; break
                        elif s['highs'][j] >= target: r = target_pct / stop_pct; break
                    else:
                        if s['highs'][j] >= stop: r = -1.0; break
                        elif s['lows'][j] <= target: r = target_pct / stop_pct; break
                if r is None:
                    r = (((s['cierre'] - entrada) if direccion == 'long' else (entrada - s['cierre'])) / entrada * 100) / stop_pct
                total += r; n += 1
                if r > 0: wins += 1
            if n >= N_MINIMO:
                resultados.append({'stop': stop_pct, 'target': target_pct, 'ratio': round(target_pct / stop_pct, 2),
                                    'n': n, 'r_neto': round(total / n - COSTE_R, 4), 'win': round(wins / n * 100, 1)})
    return resultados

def imprimir_top(resultados, nombre):
    resultados_ord = sorted(resultados, key=lambda x: x['r_neto'], reverse=True)
    print(f"\n{'=' * 78}")
    print(f"TOP 10 (de {len(resultados_ord)} combinaciones totales) — {nombre}")
    print('=' * 78)
    if not resultados_ord:
        print("  Sin combinaciones con muestra suficiente.")
        return
    for i, r in enumerate(resultados_ord[:10], 1):
        otros = {k: v for k, v in r.items() if k not in ('stop', 'target', 'ratio', 'n', 'r_neto', 'win')}
        extra = "  " + " ".join(f"{k}={v}" for k, v in otros.items()) if otros else ""
        print(f"  #{i:<3} stop={r['stop']}% target={r['target']}% ratio={r['ratio']}:1  "
              f"N={r['n']:<5} R_neto={r['r_neto']:+.3f}  win={r['win']}%{extra}")

def exportar_csv(resultados, nombre_archivo):
    if not resultados:
        print(f"  (sin resultados que exportar para {nombre_archivo})")
        return
    columnas = list(resultados[0].keys())
    with open(nombre_archivo, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        for r in sorted(resultados, key=lambda x: x['r_neto'], reverse=True):
            writer.writerow(r)
    print(f"  ✓ {len(resultados)} combinaciones exportadas a {nombre_archivo}")

# ══════════════════════════════════════════════════════════════
#  1. GAP & GO (long)
# ══════════════════════════════════════════════════════════════

def señales_gapgo(rvol_min, hora_fin):
    todas = []
    for sym in simbolos:
        datos = obtener_intradia(sym, '5m')
        if not datos: continue
        por_dia = defaultdict(list)
        for d in datos: por_dia[d[0][:10]].append(d)
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
            if v > 0: acum.append(v)
        for fecha, velas in por_dia.items():
            pre = [v for v in velas if len(v) > 7 and v[7] == 'pre']
            reg = [v for v in velas if len(v) <= 7 or v[7] == 'regular']
            if not pre or not reg: continue
            pm_high = max(v[2] for v in pre)
            ridx = None
            for i, v in enumerate(reg):
                if v[4] > pm_high: ridx = i; break
            if ridx is None: continue
            hora = reg[ridx][0][11:16]
            rv = rvol30.get(fecha)
            if rv is None or rv < rvol_min: continue
            if not ('09:30' <= hora < hora_fin): continue
            entrada = reg[ridx][4]
            post = reg[ridx + 1:]
            todas.append({'entrada': entrada, 'highs': [x[2] for x in post], 'lows': [x[3] for x in post], 'cierre': reg[-1][4]})
    return todas

print("=" * 78)
print("OPTIMIZANDO GAP & GO (long)...")
print("=" * 78)
rvol_valores = [1.0, 1.5, 2.0, 3.0]
hora_valores = ['09:45', '10:00', '10:15', '10:30']
stop_gapgo = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
target_gapgo = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0]

resultados_gapgo = []
total_combos = len(rvol_valores) * len(hora_valores)
i = 0
for rvol_min in rvol_valores:
    for hora_fin in hora_valores:
        i += 1
        print(f"  [{i}/{total_combos}] rvol_min={rvol_min} hora_fin={hora_fin} ...")
        señales = señales_gapgo(rvol_min, hora_fin)
        parciales = barrer_stop_target(señales, stop_gapgo, target_gapgo, 'long')
        for p in parciales:
            p['rvol_min'] = rvol_min
            p['hora_fin'] = hora_fin
        resultados_gapgo.extend(parciales)

imprimir_top(resultados_gapgo, "GAP & GO (long)")
exportar_csv(resultados_gapgo, 'optimizador_gapgo.csv')

# ══════════════════════════════════════════════════════════════
#  2. FIRST RED DAY (short)
# ══════════════════════════════════════════════════════════════

def reconstruir_dias(symbol):
    datos = obtener_intradia(symbol, '5m')
    if not datos: return {}
    por_dia = defaultdict(list)
    for d in datos: por_dia[d[0][:10]].append(d)
    fechas_ord = sorted(por_dia.keys())
    dias = {}
    for fecha in fechas_ord:
        reg = [v for v in por_dia[fecha] if len(v) <= 7 or v[7] == 'regular']
        if not reg: continue
        dias[fecha] = {'open': reg[0][1], 'high': max(v[2] for v in reg), 'low': min(v[3] for v in reg),
                        'close': reg[-1][4], 'volumen': sum(v[5] or 0 for v in reg), 'velas': reg}
    return dias

cache_dias_todos = {sym: reconstruir_dias(sym) for sym in simbolos}
print("\n(dias reconstruidos y cacheados para FRD y Overext)\n")

def señales_frd(min_verdes, tipo_rojo, vol_decreciente, sobreext_min):
    todas = []
    for sym in simbolos:
        dias = cache_dias_todos[sym]
        fechas = sorted(dias.keys())
        if len(fechas) < min_verdes + 2: continue
        for i in range(min_verdes, len(fechas) - 1):
            prev_f = fechas[i - min_verdes:i]
            prev = [dias[f] for f in prev_f]
            if not all(d['close'] >= d['open'] for d in prev): continue
            dia = dias[fechas[i]]; ant = dias[fechas[i - 1]]
            rojo_ap = dia['close'] < dia['open']; rojo_ca = dia['close'] < ant['close']
            if tipo_rojo == 'apertura' and not rojo_ap: continue
            if tipo_rojo == 'cierre_ant' and not rojo_ca: continue
            if tipo_rojo == 'ambas' and not (rojo_ap and rojo_ca): continue
            if vol_decreciente and not (dia['volumen'] < ant['volumen']): continue
            mn = min(d['low'] for d in prev); mx = max(d['high'] for d in prev)
            sob = (mx - mn) / mn * 100 if mn > 0 else 0
            if sob < sobreext_min: continue
            d_op = dias[fechas[i + 1]]
            velas = d_op['velas']; op = velas[0][1]
            eidx = None
            for k, v in enumerate(velas):
                if v[3] < op: eidx = k; break
            if eidx is None: continue
            post = velas[eidx + 1:]
            todas.append({'entrada': op, 'highs': [x[2] for x in post], 'lows': [x[3] for x in post], 'cierre': velas[-1][4]})
    return todas

print("=" * 78)
print("OPTIMIZANDO FIRST RED DAY (short)...")
print("=" * 78)
mv_valores = [1, 2, 3]
tr_valores = ['apertura', 'cierre_ant', 'ambas']
vd_valores = [True, False]
sob_valores = [20, 30, 40, 50]
stop_frd = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
target_frd = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]

resultados_frd = []
total_combos = len(mv_valores) * len(tr_valores) * len(vd_valores) * len(sob_valores)
i = 0
for mv in mv_valores:
    for tr in tr_valores:
        for vd in vd_valores:
            for sob in sob_valores:
                i += 1
                print(f"  [{i}/{total_combos}] verdes={mv} rojo={tr} vol_decr={vd} sobreext>={sob} ...")
                señales = señales_frd(mv, tr, vd, sob)
                parciales = barrer_stop_target(señales, stop_frd, target_frd, 'short')
                for p in parciales:
                    p['min_verdes'] = mv; p['tipo_rojo'] = tr; p['vol_decr'] = vd; p['sobreext_min'] = sob
                resultados_frd.extend(parciales)

imprimir_top(resultados_frd, "FIRST RED DAY (short)")
exportar_csv(resultados_frd, 'optimizador_frd.csv')

# ══════════════════════════════════════════════════════════════
#  3. OVEREXTENDED GAP DOWN (short)
# ══════════════════════════════════════════════════════════════

def señales_overext(gap_min, dias_sob, sobreext_min, entrada_tipo):
    todas = []
    for sym in simbolos:
        dias = cache_dias_todos[sym]
        fechas = sorted(dias.keys())
        if len(fechas) < dias_sob + 2: continue
        for i in range(1, len(fechas) - 1):
            ant = dias[fechas[i - 1]]; dia = dias[fechas[i]]
            gap = (ant['close'] - dia['open']) / ant['close'] * 100
            if gap < gap_min: continue
            prev = [dias[f] for f in fechas[max(0, i - dias_sob):i]]
            if not prev: continue
            mn = min(d['low'] for d in prev); mx = max(d['high'] for d in prev)
            sob = (mx - mn) / mn * 100 if mn > 0 else 0
            if sob < sobreext_min: continue
            velas = dia['velas']
            eidx, ep = None, None
            if entrada_tipo == 'rebote_resist':
                for k, v in enumerate(velas):
                    if v[2] >= ant['close'] * 0.98: ep, eidx = v[4], k; break
            else:
                op = velas[0][1]
                for k, v in enumerate(velas):
                    if v[3] < op: ep, eidx = op, k; break
            if eidx is None: continue
            post = velas[eidx + 1:]
            todas.append({'entrada': ep, 'highs': [x[2] for x in post], 'lows': [x[3] for x in post], 'cierre': velas[-1][4]})
    return todas

print("=" * 78)
print("OPTIMIZANDO OVEREXTENDED GAP DOWN (short)...")
print("=" * 78)
gap_valores = [1.0, 2.0, 3.0]
sob_valores2 = [30, 50, 70]
ds_valores = [2, 3]
ent_valores = ['rebote_resist', 'pierde_open']
stop_ov = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
target_ov = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]

resultados_overext = []
total_combos = len(gap_valores) * len(ds_valores) * len(sob_valores2) * len(ent_valores)
i = 0
for gm in gap_valores:
    for ds in ds_valores:
        for sb in sob_valores2:
            for et in ent_valores:
                i += 1
                print(f"  [{i}/{total_combos}] gap>={gm} dias_sob={ds} sobreext>={sb} entrada={et} ...")
                señales = señales_overext(gm, ds, sb, et)
                parciales = barrer_stop_target(señales, stop_ov, target_ov, 'short')
                for p in parciales:
                    p['gap_min'] = gm; p['dias_sob'] = ds; p['sobreext_min'] = sb; p['entrada'] = et
                resultados_overext.extend(parciales)

imprimir_top(resultados_overext, "OVEREXTENDED GAP DOWN (short)")
exportar_csv(resultados_overext, 'optimizador_overext.csv')

print(f"\n{'=' * 78}")
print("RESUMEN DE ARCHIVOS EXPORTADOS")
print("=" * 78)
print(f"  optimizador_gapgo.csv     — {len(resultados_gapgo)} combinaciones")
print(f"  optimizador_frd.csv       — {len(resultados_frd)} combinaciones")
print(f"  optimizador_overext.csv   — {len(resultados_overext)} combinaciones")
print("\nAbre cualquiera en Excel/Google Sheets, ordena por r_neto, y filtra")
print(f"por 'n' (muestra) para ver qué combinaciones son robustas de verdad")
print(f"y no solo suerte de poca muestra (todas ya tienen n >= {N_MINIMO}).")