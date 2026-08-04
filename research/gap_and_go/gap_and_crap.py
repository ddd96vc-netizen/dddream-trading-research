"""
GAP AND CRAP vs GAP & GO — etiqueta tus Gap&Go ya detectados según si el
volumen se mantiene (Gap&Go real) o se destruye tras la rotura (Gap and
Crap), y prueba si una salida anticipada por caída de volumen mejora el R
frente al stop/target fijo (la idea del trailing stop pendiente).
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'
COSTE_R = 0.1
STOP_PCT = 2.0
TARGET_PCT = 5.0
VELAS_CHEQUEO = 3         # cuántas velas tras la entrada miramos el volumen
CAIDA_VOL_UMBRAL = 50.0   # % de caída de volumen que define "Gap and Crap"

def conectar():
    return sqlite3.connect(DB)

def medir_long_fijo(velas, entrada, idx, stop_pct, target_pct):
    stop = entrada * (1 - stop_pct / 100)
    target = entrada * (1 + target_pct / 100)
    for v in velas[idx:]:
        if v[3] <= stop: return -1.0
        elif v[2] >= target: return target_pct / stop_pct
    return ((velas[-1][4] - entrada) / entrada * 100) / stop_pct

def medir_long_salida_volumen(velas, entrada, idx, stop_pct, target_pct, vol_entrada):
    """
    Igual que el fijo, pero si en las primeras VELAS_CHEQUEO tras la
    entrada el volumen medio cae por debajo de CAIDA_VOL_UMBRAL% del
    volumen de la vela de entrada, sale ahí (salida anticipada).
    """
    stop = entrada * (1 - stop_pct / 100)
    target = entrada * (1 + target_pct / 100)
    chequeo = velas[idx:idx + VELAS_CHEQUEO]
    if chequeo and vol_entrada > 0:
        vol_prom = sum(v[5] or 0 for v in chequeo) / len(chequeo)
        if vol_prom < vol_entrada * (CAIDA_VOL_UMBRAL / 100):
            precio_salida = chequeo[-1][4]
            return ((precio_salida - entrada) / entrada * 100) / stop_pct
    for v in velas[idx:]:
        if v[3] <= stop: return -1.0
        elif v[2] >= target: return target_pct / stop_pct
    return ((velas[-1][4] - entrada) / entrada * 100) / stop_pct

def detectar_gapgo(symbol):
    """Reconstruye señales de Gap & Go (rotura de PM High), con volumen de entrada."""
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval='5m' ORDER BY datetime''', (symbol,))
    datos = c.fetchall(); conn.close()
    if not datos:
        return []

    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[0][:10]].append(d)

    señales = []
    for fecha, velas in por_dia.items():
        pre = [v for v in velas if len(v) > 7 and v[7] == 'pre']
        regular = [v for v in velas if len(v) <= 7 or v[7] == 'regular']
        if not pre or not regular:
            continue
        pm_high = max(v[2] for v in pre)
        ridx = None
        for i, v in enumerate(regular):
            if v[4] > pm_high:
                ridx = i
                break
        if ridx is None:
            continue
        entrada = regular[ridx][4]
        vol_entrada = regular[ridx][5] or 0
        señales.append({'velas': regular, 'idx': ridx, 'entrada': entrada, 'vol_entrada': vol_entrada})
    return señales

# ── Recopilar ──
conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print(f"Cargando {len(simbolos)} tickers...")
todas_señales = []
for sym in simbolos:
    todas_señales.extend(detectar_gapgo(sym))

print(f"Total señales de Gap & Go: {len(todas_señales)}\n")

# ── Etiquetar Gap&Go real vs Gap and Crap (diagnóstico post-hoc) ──
gap_go_real = []
gap_and_crap = []
for s in todas_señales:
    velas, idx, entrada, vol_entrada = s['velas'], s['idx'], s['entrada'], s['vol_entrada']
    chequeo = velas[idx + 1:idx + 1 + VELAS_CHEQUEO]
    if chequeo and vol_entrada > 0:
        vol_prom = sum(v[5] or 0 for v in chequeo) / len(chequeo)
        if vol_prom < vol_entrada * (CAIDA_VOL_UMBRAL / 100):
            gap_and_crap.append(s)
        else:
            gap_go_real.append(s)
    else:
        gap_go_real.append(s)

def evaluar_fijo(lista):
    if len(lista) < 20:
        return None
    total = 0
    wins = 0
    for s in lista:
        r = medir_long_fijo(s['velas'], s['entrada'], s['idx'] + 1, STOP_PCT, TARGET_PCT)
        total += r
        if r > 0:
            wins += 1
    n = len(lista)
    return {'n': n, 'r_neto': total / n - COSTE_R, 'win': wins / n * 100}

print("=" * 66)
print("DIAGNÓSTICO: Gap&Go real vs Gap and Crap (mismo stop/target fijo)")
print("=" * 66)
r_real = evaluar_fijo(gap_go_real)
r_crap = evaluar_fijo(gap_and_crap)
if r_real:
    print(f"Gap & Go real     : {r_real['n']:>5} señales | R neto {r_real['r_neto']:+.3f}R | win {r_real['win']:.0f}%")
if r_crap:
    print(f"Gap and Crap      : {r_crap['n']:>5} señales | R neto {r_crap['r_neto']:+.3f}R | win {r_crap['win']:.0f}%")

# ── Prueba real: ¿mejora salir antes por caída de volumen? ──
def evaluar_con_salida_vol(lista):
    if len(lista) < 20:
        return None
    total = 0
    wins = 0
    for s in lista:
        r = medir_long_salida_volumen(s['velas'], s['entrada'], s['idx'] + 1, STOP_PCT, TARGET_PCT, s['vol_entrada'])
        total += r
        if r > 0:
            wins += 1
    n = len(lista)
    return {'n': n, 'r_neto': total / n - COSTE_R, 'win': wins / n * 100}

print("\n" + "=" * 66)
print("PRUEBA: ¿mejora salir antes si el volumen se destruye pronto?")
print("(sobre TODAS las señales, no solo las etiquetadas 'crap')")
print("=" * 66)
r_fijo_todas = evaluar_fijo(todas_señales)
r_vol_todas = evaluar_con_salida_vol(todas_señales)
if r_fijo_todas:
    print(f"Stop/target FIJO        : {r_fijo_todas['n']:>5} señales | R neto {r_fijo_todas['r_neto']:+.3f}R | win {r_fijo_todas['win']:.0f}%")
if r_vol_todas:
    print(f"Salida por caída volumen: {r_vol_todas['n']:>5} señales | R neto {r_vol_todas['r_neto']:+.3f}R | win {r_vol_todas['win']:.0f}%")

print("\nSi 'Salida por caída volumen' da mejor R que 'FIJO', la idea del")
print("trailing/exit por volumen tiene fundamento y vale la pena integrarla.")
