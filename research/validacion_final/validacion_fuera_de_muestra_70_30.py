"""
VALIDACIÓN FUERA DE MUESTRA (walk-forward) — la prueba definitiva.

Divide los datos de cada ticker en dos partes: el primer 70% de sus días
(ENTRENAMIENTO) y el último 30% (PRUEBA, nunca visto). Busca los mejores
parámetros SOLO en entrenamiento, y luego prueba esos MISMOS parámetros
exactos SOLO en la parte de prueba. Si el R se mantiene parecido, el
edge es real. Si se desploma o se vuelve negativo, era ruido de tanto
combinar parámetros (overfitting).

Exige stop >= 2.5% en la búsqueda (evita el sesgo de stops irrealmente
pequeños que ya detectamos).
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta (misma que tus otros scripts)
COSTE_R = 0.1
N_MINIMO_TRAIN = 20
TRAIN_FRAC = 0.70   # 70% de los días de cada ticker para buscar, 30% para probar

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

# -- Split train/test por ticker (70% días más antiguos = train, 30% más recientes = test) --
fechas_train = {}
fechas_test = {}
for sym in simbolos:
    datos = obtener_intradia(sym, '5m')
    fechas = sorted(set(d[0][:10] for d in datos))
    corte = int(len(fechas) * TRAIN_FRAC)
    fechas_train[sym] = set(fechas[:corte])
    fechas_test[sym] = set(fechas[corte:])

print(f"Split hecho: {TRAIN_FRAC*100:.0f}% train / {(1-TRAIN_FRAC)*100:.0f}% test, por ticker\n")

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
            if n >= N_MINIMO_TRAIN:
                resultados.append({'stop': stop_pct, 'target': target_pct, 'ratio': round(target_pct / stop_pct, 2),
                                    'n': n, 'r_neto': round(total / n - COSTE_R, 4), 'win': round(wins / n * 100, 1)})
    return resultados

def medir_directo(señales, stop_pct, target_pct, direccion):
    """Mide R para UN combo concreto de stop/target (usado en la fase de prueba)."""
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
    if n == 0:
        return None
    return {'n': n, 'r_neto': round(total / n - COSTE_R, 4), 'win': round(wins / n * 100, 1)}

# ══════════════════════════════════════════════════════════════
#  1. GAP & GO
# ══════════════════════════════════════════════════════════════

def señales_gapgo(rvol_min, hora_fin, fechas_permitidas):
    todas = []
    for sym in simbolos:
        permitidas = fechas_permitidas[sym]
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
            if fecha not in permitidas: continue
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

cache_dias = {sym: reconstruir_dias(sym) for sym in simbolos}

def señales_frd(min_verdes, tipo_rojo, vol_decreciente, sobreext_min, fechas_permitidas):
    todas = []
    for sym in simbolos:
        permitidas = fechas_permitidas[sym]
        dias = cache_dias[sym]
        fechas = sorted(dias.keys())
        if len(fechas) < min_verdes + 2: continue
        for i in range(min_verdes, len(fechas) - 1):
            f_op = fechas[i + 1]
            if f_op not in permitidas: continue
            prev = [dias[f] for f in fechas[i - min_verdes:i]]
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
            d_op = dias[f_op]
            velas = d_op['velas']; op = velas[0][1]
            eidx = None
            for k, v in enumerate(velas):
                if v[3] < op: eidx = k; break
            if eidx is None: continue
            post = velas[eidx + 1:]
            todas.append({'entrada': op, 'highs': [x[2] for x in post], 'lows': [x[3] for x in post], 'cierre': velas[-1][4]})
    return todas

def señales_overext(gap_min, dias_sob, sobreext_min, entrada_tipo, fechas_permitidas):
    todas = []
    for sym in simbolos:
        permitidas = fechas_permitidas[sym]
        dias = cache_dias[sym]
        fechas = sorted(dias.keys())
        if len(fechas) < dias_sob + 2: continue
        for i in range(1, len(fechas) - 1):
            f_dia = fechas[i]
            if f_dia not in permitidas: continue
            ant = dias[fechas[i - 1]]; dia = dias[f_dia]
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

# ══════════════════════════════════════════════════════════════
#  FASE 1: BUSCAR el mejor combo SOLO en TRAIN (stop >= 2.5%)
# ══════════════════════════════════════════════════════════════

def buscar_mejor_gapgo(fechas_permitidas):
    stop_v = [2.5, 3.0, 4.0]; target_v = [4.0, 6.0, 8.0, 10.0, 12.0]
    mejores = []
    for rvol_min in [1.5, 2.0, 3.0]:
        for hora_fin in ['10:00', '10:15', '10:30']:
            señales = señales_gapgo(rvol_min, hora_fin, fechas_permitidas)
            for r in barrer_stop_target(señales, stop_v, target_v, 'long'):
                r['rvol_min'] = rvol_min; r['hora_fin'] = hora_fin
                mejores.append(r)
    mejores.sort(key=lambda x: -x['r_neto'])
    return mejores[:3]

def buscar_mejor_frd(fechas_permitidas):
    stop_v = [2.5, 3.0, 4.0]; target_v = [4.0, 6.0, 8.0, 10.0]
    mejores = []
    for mv in [2, 3]:
        for tr in ['apertura', 'ambas']:
            for vd in [True, False]:
                for sob in [30, 50]:
                    señales = señales_frd(mv, tr, vd, sob, fechas_permitidas)
                    for r in barrer_stop_target(señales, stop_v, target_v, 'short'):
                        r['min_verdes'] = mv; r['tipo_rojo'] = tr; r['vol_decr'] = vd; r['sobreext_min'] = sob
                        mejores.append(r)
    mejores.sort(key=lambda x: -x['r_neto'])
    return mejores[:3]

def buscar_mejor_overext(fechas_permitidas):
    stop_v = [2.5, 3.0, 4.0]; target_v = [4.0, 6.0, 8.0, 10.0]
    mejores = []
    for gm in [1.0, 2.0, 3.0]:
        for ds in [2, 3]:
            for sb in [50, 70]:
                for et in ['rebote_resist', 'pierde_open']:
                    señales = señales_overext(gm, ds, sb, et, fechas_permitidas)
                    for r in barrer_stop_target(señales, stop_v, target_v, 'short'):
                        r['gap_min'] = gm; r['dias_sob'] = ds; r['sobreext_min'] = sb; r['entrada'] = et
                        mejores.append(r)
    mejores.sort(key=lambda x: -x['r_neto'])
    return mejores[:3]

print("=" * 78)
print("FASE 1 — Buscando los 3 mejores combos de cada estrategia en TRAIN...")
print("(esto tarda -- son varias decenas de combinaciones por estrategia)")
print("=" * 78)

print("\n  Buscando en Gap & Go...")
top_gapgo = buscar_mejor_gapgo(fechas_train)
print("  Buscando en First Red Day...")
top_frd = buscar_mejor_frd(fechas_train)
print("  Buscando en Overextended Gap Down...")
top_overext = buscar_mejor_overext(fechas_train)

# ══════════════════════════════════════════════════════════════
#  FASE 2: PROBAR esos mismos combos SOLO en TEST
# ══════════════════════════════════════════════════════════════

print("\n" + "=" * 78)
print("FASE 2 — Probando esos MISMOS parámetros SOLO en TEST (datos nunca vistos)")
print("=" * 78)

def reportar(nombre, top_train, fn_señales, direccion, claves_extra):
    print(f"\n--- {nombre} ---")
    for i, combo in enumerate(top_train, 1):
        kwargs = {k: combo[k] for k in claves_extra}
        señales_test = fn_señales(*kwargs.values(), fechas_test)
        resultado_test = medir_directo(señales_test, combo['stop'], combo['target'], direccion)
        print(f"\n  Candidato #{i}: {kwargs}  stop={combo['stop']}% target={combo['target']}%")
        print(f"    TRAIN: N={combo['n']:<5} R_neto={combo['r_neto']:+.3f}  win={combo['win']}%")
        if resultado_test:
            print(f"    TEST:  N={resultado_test['n']:<5} R_neto={resultado_test['r_neto']:+.3f}  win={resultado_test['win']}%")
            if resultado_test['r_neto'] > 0 and resultado_test['r_neto'] > combo['r_neto'] * 0.4:
                print(f"    → ✓ SE MANTIENE razonablemente. Podría ser real.")
            elif resultado_test['r_neto'] > 0:
                print(f"    → ⚠ Se adelgaza mucho pero sigue positivo. Dudoso.")
            else:
                print(f"    → ✗ SE DESPLOMA o se vuelve negativo. Probable overfitting.")
        else:
            print(f"    TEST:  sin señales en el período de prueba")

reportar("GAP & GO (long)", top_gapgo, señales_gapgo, 'long', ['rvol_min', 'hora_fin'])
reportar("FIRST RED DAY (short)", top_frd, señales_frd, 'short', ['min_verdes', 'tipo_rojo', 'vol_decr', 'sobreext_min'])
reportar("OVEREXTENDED GAP DOWN (short)", top_overext, señales_overext, 'short', ['gap_min', 'dias_sob', 'sobreext_min', 'entrada'])

print(f"\n{'=' * 78}")
print("LECTURA: si el R de TEST se parece al de TRAIN (o al menos se queda")
print("positivo y no muy lejos), el edge probablemente es real. Si el R de")
print("TEST se desploma o se vuelve negativo, era ajuste a ruido -- no lo uses.")
