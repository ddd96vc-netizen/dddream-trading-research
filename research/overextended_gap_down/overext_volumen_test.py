"""
VALIDACION FUERA DE MUESTRA - filtro de volumen para Overextended Gap
Down. Divide cada ticker en dos mitades por fecha (mitad mas antigua =
A, mitad mas reciente = B) y mide la version CON volumen en las dos por
separado. Si la mejora se sostiene en AMBAS, es una señal real. Si solo
aparece en una, era ruido de muestra chica -- el mismo patron que ya
vimos con First Red Day y con el optimizador.
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta
COSTE_R = 0.1
STOP_USADO = 2.5
TARGET_USADO = 10.0
GAP_MIN = 3.0
DIAS_SOB = 3
SOBREEXT_MIN = 50.0
MULTIPLICADOR_SPIKE = 1.3

def conectar():
    return sqlite3.connect(DB)

def obtener_intradia(symbol, intervalo='5m'):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval=? ORDER BY datetime''', (symbol, intervalo))
    r = c.fetchall(); conn.close()
    return r

def medir_short(velas, entrada, idx, stop_pct, target_pct):
    stop = entrada * (1 + stop_pct / 100); target = entrada * (1 - target_pct / 100)
    for v in velas[idx:]:
        if v[2] >= stop: return -1.0
        elif v[3] <= target: return target_pct / stop_pct
    return ((entrada - velas[-1][4]) / entrada * 100) / stop_pct

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

def señales_baseline(symbol, fechas_permitidas):
    dias = reconstruir_dias(symbol)
    fechas = sorted(dias.keys())
    if len(fechas) < DIAS_SOB + 2: return []
    trades = []
    for i in range(1, len(fechas) - 1):
        f_dia = fechas[i]
        if f_dia not in fechas_permitidas: continue
        ant = dias[fechas[i - 1]]; dia = dias[f_dia]
        gap = (ant['close'] - dia['open']) / ant['close'] * 100
        if gap < GAP_MIN: continue
        prev = [dias[f] for f in fechas[max(0, i - DIAS_SOB):i]]
        if not prev: continue
        mn = min(d['low'] for d in prev); mx = max(d['high'] for d in prev)
        sob = (mx - mn) / mn * 100 if mn > 0 else 0
        if sob < SOBREEXT_MIN: continue
        velas = dia['velas']
        eidx, ep = None, None
        for k, v in enumerate(velas):
            if v[2] >= ant['close'] * 0.98:
                ep, eidx = v[4], k; break
        if eidx is None: continue
        r = medir_short(velas, ep, eidx + 1, STOP_USADO, TARGET_USADO)
        trades.append(r)
    return trades

def señales_con_volumen(symbol, fechas_permitidas):
    dias = reconstruir_dias(symbol)
    fechas = sorted(dias.keys())
    if len(fechas) < DIAS_SOB + 2: return []
    trades = []
    for i in range(1, len(fechas) - 1):
        f_dia = fechas[i]
        if f_dia not in fechas_permitidas: continue
        ant = dias[fechas[i - 1]]; dia = dias[f_dia]
        gap = (ant['close'] - dia['open']) / ant['close'] * 100
        if gap < GAP_MIN: continue
        prev = [dias[f] for f in fechas[max(0, i - DIAS_SOB):i]]
        if not prev: continue
        mn = min(d['low'] for d in prev); mx = max(d['high'] for d in prev)
        sob = (mx - mn) / mn * 100 if mn > 0 else 0
        if sob < SOBREEXT_MIN: continue

        velas = dia['velas']
        resistencia = ant['close'] * 0.98
        idx_toque = None
        for k, v in enumerate(velas):
            if v[2] >= resistencia:
                idx_toque = k; break
        if idx_toque is None or idx_toque < 2:
            continue

        volumenes_rebote = [v[5] or 0 for v in velas[:idx_toque]]
        mitad = len(volumenes_rebote) // 2
        vol_primera = sum(volumenes_rebote[:mitad]) / max(mitad, 1)
        vol_segunda = sum(volumenes_rebote[mitad:]) / max(len(volumenes_rebote) - mitad, 1)
        if not (vol_segunda < vol_primera):
            continue

        vol_prom_rebote = sum(volumenes_rebote) / len(volumenes_rebote)
        vela_toque = velas[idx_toque]
        if vol_prom_rebote <= 0 or (vela_toque[5] or 0) < vol_prom_rebote * MULTIPLICADOR_SPIKE:
            continue

        ep = vela_toque[4]
        r = medir_short(velas, ep, idx_toque + 1, STOP_USADO, TARGET_USADO)
        trades.append(r)
    return trades

conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]
conn.close()

print(f"Cargando {len(simbolos)} tickers y dividiendo cada uno en dos mitades por fecha...\n")

fechas_mitad_a = {}
fechas_mitad_b = {}
for sym in simbolos:
    conn = conectar(); c = conn.cursor()
    c.execute("SELECT DISTINCT substr(datetime,1,10) FROM intraday_data WHERE symbol=? AND interval='5m'", (sym,))
    fechas = sorted(r[0] for r in c.fetchall())
    conn.close()
    corte = len(fechas) // 2
    fechas_mitad_a[sym] = set(fechas[:corte])
    fechas_mitad_b[sym] = set(fechas[corte:])

def evaluar(fn, fechas_dict, nombre):
    todos = []
    for sym in simbolos:
        todos.extend(fn(sym, fechas_dict[sym]))
    if len(todos) < 10:
        print(f"  {nombre}: muestra insuficiente ({len(todos)})")
        return
    n = len(todos)
    total = sum(todos)
    wins = sum(1 for r in todos if r > 0)
    print(f"  {nombre}: N={n}  R neto={total/n - COSTE_R:+.3f}R  win={wins/n*100:.0f}%")

print("=" * 70)
print("MITAD A (fechas más antiguas)")
print("=" * 70)
evaluar(señales_baseline, fechas_mitad_a, "Actual (solo toca resistencia)  ")
evaluar(señales_con_volumen, fechas_mitad_a, "Nueva (rebote débil + volumen)  ")

print("\n" + "=" * 70)
print("MITAD B (fechas más recientes)")
print("=" * 70)
evaluar(señales_baseline, fechas_mitad_b, "Actual (solo toca resistencia)  ")
evaluar(señales_con_volumen, fechas_mitad_b, "Nueva (rebote débil + volumen)  ")

print("\n" + "=" * 70)
print("Si 'Nueva' supera a 'Actual' en LAS DOS mitades, la mejora es real.")
print("Si solo gana en una, era ruido de muestra chica -- descarta el filtro.")
print("=" * 70)