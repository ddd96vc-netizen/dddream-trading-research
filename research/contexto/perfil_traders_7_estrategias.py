"""
TODAS LAS ESTRATEGIAS FILTRADAS POR PERFIL DE TRADERS - corre las 7
estrategias que hemos probado en este proyecto (las 3 confirmadas Y las
4 que habiamos descartado), cada una desglosada segun cuantas de las 4
condiciones del perfil (float<=5M, institucional<=10%, RVOL_dia>=8x,
cambio%_dia>=10%) cumplia el ticker el DIA EXACTO de cada señal.
Solo lee, no toca el scanner ni ninguna tabla.
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta (misma que tus otros scripts)
COSTE_R = 0.1

# -- Umbrales del perfil de traders (ajustables aqui) --
FLOAT_MAX = 5.0
INST_MAX = 10.0
RVOL_MIN = 8.0
CAMBIO_MIN = 10.0

def conectar():
    return sqlite3.connect(DB)

def obtener_intradia(symbol, intervalo='5m'):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval=? ORDER BY datetime''', (symbol, intervalo))
    r = c.fetchall(); conn.close()
    return r

def obtener_float_inst(symbol):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT float_shares, inst_own FROM scanner_results
                 WHERE symbol=? ORDER BY fecha DESC LIMIT 1''', (symbol,))
    row = c.fetchone(); conn.close()
    if not row:
        return None, None
    float_shares, inst_own = row
    return (float_shares / 1e6 if float_shares else None), inst_own

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
    for idx, fecha in enumerate(fechas_ordenadas):
        if fecha not in dias:
            continue
        if idx > 0 and fechas_ordenadas[idx - 1] in dias:
            cierre_ant = dias[fechas_ordenadas[idx - 1]]['close']
            dias[fecha]['change_pct'] = round((dias[fecha]['close'] - cierre_ant) / cierre_ant * 100, 2) if cierre_ant else None
        else:
            dias[fecha]['change_pct'] = None
        vols_previos = [dias[f]['volumen'] for f in fechas_ordenadas[:idx] if f in dias and dias[f]['volumen'] > 0]
        if vols_previos:
            prom = sum(vols_previos) / len(vols_previos)
            dias[fecha]['rvol_dia'] = round(dias[fecha]['volumen'] / prom, 2) if prom > 0 else None
        else:
            dias[fecha]['rvol_dia'] = None
    return dias

# ══════════════════ LAS 3 CONFIRMADAS ══════════════════

def trades_gapgo(symbol):
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
        trades.append((symbol, fecha, r))
    return trades

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
        trades.append((symbol, f_op, r))
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
        trades.append((symbol, f_dia, r))
    return trades

# ══════════════════ LAS 4 DESCARTADAS ══════════════════

def trades_vwap_bounce(symbol):
    datos = obtener_intradia(symbol, '5m')
    if not datos:
        return []
    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[0][:10]].append(d)
    trades = []
    for fecha, velas in por_dia.items():
        regular = [v for v in velas if (len(v) <= 7 or v[7] == 'regular') and v[6] is not None]
        if len(regular) < 3:
            continue
        for i, v in enumerate(regular):
            low, close, vwap = v[3], v[4], v[6]
            if vwap is None:
                continue
            if low <= vwap and close > vwap:
                r = medir_long(regular, close, i + 1, 2.0, 4.0)
                trades.append((symbol, fecha, r))
    return trades

def trades_vwap_rejection(symbol):
    """Espejo de VWAP Bounce pero en corto: rechazo del VWAP desde abajo."""
    datos = obtener_intradia(symbol, '5m')
    if not datos:
        return []
    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[0][:10]].append(d)
    trades = []
    for fecha, velas in por_dia.items():
        regular = [v for v in velas if (len(v) <= 7 or v[7] == 'regular') and v[6] is not None]
        if len(regular) < 3:
            continue
        for i, v in enumerate(regular):
            high, close, vwap = v[2], v[4], v[6]
            if vwap is None:
                continue
            if high >= vwap and close < vwap:
                r = medir_short(regular, close, i + 1, 2.0, 4.0)
                trades.append((symbol, fecha, r))
    return trades

def trades_reciclaje(symbol, umbral=1.0, ventana=2):
    """Version CORREGIDA (sin lookahead) -- entrada en la vela confirmada."""
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval='1m' ORDER BY datetime''', (symbol,))
    datos = c.fetchall(); conn.close()
    if not datos:
        return []
    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[0][:10]].append(d)
    trades = []
    for fecha, velas_full in por_dia.items():
        activas = [v for v in velas_full if (len(v) <= 7 or v[7] in ('pre', 'regular'))]
        if len(activas) < ventana:
            continue
        i = 0
        while i < len(activas) - 1:
            base = activas[i][4]
            mejor_subida = 0
            fin_idx = i
            for j in range(i + 1, min(i + ventana + 1, len(activas))):
                alto = activas[j][2]
                subida = ((alto - base) / base) * 100
                if subida > mejor_subida:
                    mejor_subida = subida
                    fin_idx = j
            if mejor_subida >= umbral:
                entrada_real = activas[fin_idx][4]
                r = medir_long(activas, entrada_real, fin_idx + 1, 1.0, 2.0)
                trades.append((symbol, fecha, r))
                i = fin_idx
            else:
                i += 1
    return trades

def trades_green_to_red(symbol, dias, destruccion_min=50.0, dias_sob=2, stop_pct=3.0, target_pct=6.0):
    fechas = sorted(dias.keys())
    trades = []
    for i in range(dias_sob, len(fechas)):
        f_dia = fechas[i]
        dia = dias[f_dia]
        prev = [dias[f] for f in fechas[i - dias_sob:i]]
        ext_high = max(d['high'] for d in prev)
        ext_low = min(d['low'] for d in prev)
        rango = ext_high - ext_low
        if rango <= 0:
            continue
        ant = dias[fechas[i - 1]]
        if dia['open'] <= ant['close']:
            continue
        velas = dia['velas']
        for k, v in enumerate(velas):
            if v[4] < ant['close']:
                precio_cruce = v[4]
                destruccion = (ext_high - precio_cruce) / rango * 100
                if destruccion >= destruccion_min:
                    r = medir_short(velas, precio_cruce, k + 1, stop_pct, target_pct)
                    trades.append((symbol, f_dia, r))
                break
    return trades

# ══════════════════ RECOPILAR ══════════════════

conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print(f"Cargando {len(simbolos)} tickers y reconstruyendo dias (5m)... esto puede tardar un rato.")
cache_dias = {sym: reconstruir_dias(sym) for sym in simbolos}
cache_float_inst = {sym: obtener_float_inst(sym) for sym in simbolos}

print("Detectando señales de las 7 estrategias...")
señales = {
    "GAP & GO (long) — CONFIRMADA": [],
    "FIRST RED DAY (short) — CONFIRMADA": [],
    "OVEREXTENDED GAP DOWN (short) — CONFIRMADA": [],
    "VWAP BOUNCE (long) — descartada": [],
    "VWAP REJECTION (short) — descartada": [],
    "RECICLAJE (long) — descartada": [],
    "GREEN TO RED (short) — descartada": [],
}

for sym in simbolos:
    señales["GAP & GO (long) — CONFIRMADA"].extend(trades_gapgo(sym))
    señales["FIRST RED DAY (short) — CONFIRMADA"].extend(trades_frd(sym, cache_dias[sym]))
    señales["OVEREXTENDED GAP DOWN (short) — CONFIRMADA"].extend(trades_overext(sym, cache_dias[sym]))
    señales["VWAP BOUNCE (long) — descartada"].extend(trades_vwap_bounce(sym))
    señales["VWAP REJECTION (short) — descartada"].extend(trades_vwap_rejection(sym))
    señales["RECICLAJE (long) — descartada"].extend(trades_reciclaje(sym))
    señales["GREEN TO RED (short) — descartada"].extend(trades_green_to_red(sym, cache_dias[sym]))

def condiciones_cumplidas(symbol, fecha):
    float_M, inst_own = cache_float_inst.get(symbol, (None, None))
    dia_info = cache_dias.get(symbol, {}).get(fecha)
    n = 0
    if float_M is not None and float_M <= FLOAT_MAX:
        n += 1
    if inst_own is not None and inst_own <= INST_MAX:
        n += 1
    if dia_info and dia_info.get('rvol_dia') is not None and dia_info['rvol_dia'] >= RVOL_MIN:
        n += 1
    if dia_info and dia_info.get('change_pct') is not None and dia_info['change_pct'] >= CAMBIO_MIN:
        n += 1
    return n

def evaluar_por_perfil(trades, nombre):
    buckets = {0: [], 1: [], 2: [], 3: [], 4: []}
    for symbol, fecha, r in trades:
        n = condiciones_cumplidas(symbol, fecha)
        buckets[n].append(r)

    print(f"\n{'=' * 66}")
    print(f"{nombre}")
    print('=' * 66)
    print(f"{'Condiciones':<16}{'N':>6}{'R neto':>12}{'Win%':>8}")
    print('-' * 42)
    for n in range(4, -1, -1):
        lista = buckets[n]
        etiqueta = f"{n}/4 cumplidas"
        if len(lista) < 5:
            print(f"{etiqueta:<16}{len(lista):>6}   muestra insuficiente")
            continue
        total = sum(lista)
        wins = sum(1 for r in lista if r > 0)
        print(f"{etiqueta:<16}{len(lista):>6}{total/len(lista) - COSTE_R:>+12.3f}R{wins/len(lista)*100:>7.0f}%")

    perfil_completo = buckets[4]
    resto = buckets[0] + buckets[1] + buckets[2] + buckets[3]
    print()
    if len(perfil_completo) >= 5:
        t = sum(perfil_completo); n_ = len(perfil_completo)
        w = sum(1 for r in perfil_completo if r > 0)
        print(f"  PERFIL COMPLETO (4/4): {n_} trades | R neto {t/n_ - COSTE_R:+.3f}R | win {w/n_*100:.0f}%")
    else:
        print(f"  PERFIL COMPLETO (4/4): muestra insuficiente ({len(perfil_completo)})")
    if len(resto) >= 5:
        t = sum(resto); n_ = len(resto)
        w = sum(1 for r in resto if r > 0)
        print(f"  RESTO (menos de 4):    {n_} trades | R neto {t/n_ - COSTE_R:+.3f}R | win {w/n_*100:.0f}%")

for nombre, trades in señales.items():
    evaluar_por_perfil(trades, nombre)

print(f"\n{'=' * 66}")
print(f"Perfil usado: float<={FLOAT_MAX}M, institucional<={INST_MAX}%, "
      f"RVOL_dia>={RVOL_MIN}x, cambio%_dia>={CAMBIO_MIN}%")
print("Revisa sobre todo las 4 'descartadas' -- si alguna revive con 4/4")
print("cumplidas, hay algo nuevo que investigar. Si siguen negativas incluso")
print("con el perfil completo, confirma que de verdad no tienen edge.")