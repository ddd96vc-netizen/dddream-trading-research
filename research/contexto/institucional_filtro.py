"""
INSTITUCIONAL <40% — prueba el filtro de Edu Trades sobre los 3 edges
confirmados: Gap & Go (long), First Red Day (short), Overextended Gap
Down (short). Usa los parámetros ya validados de cada uno.
El institucional es un dato por TICKER (casi no cambia día a día), así
que se segmenta el símbolo entero, no el trade individual.
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta
COSTE_R = 0.1

def conectar():
    return sqlite3.connect(DB)

def cargar_inst_own():
    """Devuelve {symbol: inst_own} con el dato más reciente disponible."""
    conn = conectar(); c = conn.cursor()
    c.execute('''
        SELECT symbol, inst_own FROM scanner_results sr
        WHERE inst_own IS NOT NULL
        AND fecha = (SELECT MAX(fecha) FROM scanner_results
                      WHERE symbol = sr.symbol AND inst_own IS NOT NULL)
    ''')
    filas = c.fetchall(); conn.close()
    return {sym: val for sym, val in filas}

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

def obtener_intradia(symbol, intervalo='5m'):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval=? ORDER BY datetime''', (symbol, intervalo))
    r = c.fetchall(); conn.close()
    return r

def reconstruir_dias(symbol):
    datos = obtener_intradia(symbol, '5m')
    if not datos:
        return []
    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[0][:10]].append(d)
    dias = []
    for fecha in sorted(por_dia.keys()):
        reg = [v for v in por_dia[fecha] if len(v) <= 7 or v[7] == 'regular']
        if not reg:
            continue
        dias.append({
            'fecha': fecha, 'open': reg[0][1], 'high': max(v[2] for v in reg),
            'low': min(v[3] for v in reg), 'close': reg[-1][4],
            'volumen': sum(v[5] or 0 for v in reg), 'velas': reg,
        })
    return dias

# ── GAP & GO (long) · RVOL alto + primera media hora · stop2/target10 ──
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
        trades.append(r)
    return trades

# ── FIRST RED DAY (short) · sobreext>=30 pierde_open · stop3/target6 ──
def trades_frd(symbol):
    dias = reconstruir_dias(symbol)
    if len(dias) < 4:
        return []
    def es_verde(d): return d['close'] >= d['open']
    trades = []
    for i in range(2, len(dias) - 1):
        prev = [dias[i - 2], dias[i - 1]]
        if not all(es_verde(d) for d in prev):
            continue
        dia, ant = dias[i], dias[i - 1]
        if not (dia['close'] < dia['open'] and dia['close'] < ant['close']):
            continue
        if not (dia['volumen'] < ant['volumen']):
            continue
        mn = min(d['low'] for d in prev); mx = max(d['high'] for d in prev)
        sob = (mx - mn) / mn * 100 if mn > 0 else 0
        if sob < 30.0:
            continue

        dia_op = dias[i + 1]
        velas = dia_op['velas']; op = velas[0][1]
        entrada_idx = None
        for k, v in enumerate(velas):
            if v[3] < op:
                entrada_idx = k; break
        if entrada_idx is None:
            continue
        r = medir_short(velas, op, entrada_idx + 1, 3.0, 6.0)
        trades.append(r)
    return trades

# ── OVEREXTENDED GAP DOWN (short) · sobreext>=50 rebote_resist · stop3/target6 ──
def trades_overext(symbol):
    dias = reconstruir_dias(symbol)
    if len(dias) < 4:
        return []
    trades = []
    for i in range(1, len(dias) - 1):
        ant, dia = dias[i - 1], dias[i]
        gap = (ant['close'] - dia['open']) / ant['close'] * 100
        if gap < 2.0:
            continue
        prev = dias[max(0, i - 2):i]
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

# ── Recopilar ──
conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print(f"Cargando institucional para {len(simbolos)} tickers...")
inst_own = cargar_inst_own()
print(f"  {len(inst_own)} tickers con dato institucional\n")

def evaluar(lista_r):
    if len(lista_r) < 20:
        return None
    n = len(lista_r)
    total = sum(lista_r)
    wins = sum(1 for r in lista_r if r > 0)
    return {'n': n, 'r_neto': total / n - COSTE_R, 'win': wins / n * 100}

def imprimir_resultado(nombre, fn_trades):
    print("=" * 66)
    print(f"{nombre}")
    print("=" * 66)
    bajo, alto, sin_dato = [], [], []
    for sym in simbolos:
        r_list = fn_trades(sym)
        if not r_list:
            continue
        io = inst_own.get(sym)
        if io is None:
            sin_dato.extend(r_list)
        elif io < 40:
            bajo.extend(r_list)
        else:
            alto.extend(r_list)

    for etiqueta, lista in [('Institucional < 40%', bajo), ('Institucional >= 40%', alto), ('Sin dato institucional', sin_dato)]:
        e = evaluar(lista)
        if e:
            print(f"  {etiqueta:<24}: {e['n']:>5} trades | R neto {e['r_neto']:+.3f}R | win {e['win']:.0f}%")
        else:
            print(f"  {etiqueta:<24}: muestra insuficiente ({len(lista)})")
    print()

imprimir_resultado("GAP & GO (long)", trades_gapgo)
imprimir_resultado("FIRST RED DAY (short)", trades_frd)
imprimir_resultado("OVEREXTENDED GAP DOWN (short)", trades_overext)

print("Si 'Institucional < 40%' da mejor R que '>= 40%' en alguno de los")
print("tres, el filtro de Edu Trades aporta valor real ahí.")
