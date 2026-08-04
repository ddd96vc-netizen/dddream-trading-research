"""
BARRIDO COMPLETO 'todos contra todos' del First Red Day SHORT.
Cruza TODAS las dimensiones y rankea por R neto.
Entrada realista (sin lookahead). R medido en corto.
"""
import sqlite3
from collections import defaultdict
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB = 'dddream.db'
COSTE_R = 0.1
STOP_PCT = 3.0
TARGET_PCT = 6.0

def conectar():
    return sqlite3.connect(DB)

def reconstruir_dias(symbol):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval='5m' ORDER BY datetime''', (symbol,))
    datos = c.fetchall(); conn.close()
    if not datos: return []
    por_dia = defaultdict(list)
    for d in datos: por_dia[d[0][:10]].append(d)
    dias = []
    for fecha in sorted(por_dia.keys()):
        reg = [v for v in por_dia[fecha] if len(v) <= 7 or v[7] == 'regular']
        if not reg: continue
        dias.append({
            'open': reg[0][1], 'high': max(v[2] for v in reg),
            'low': min(v[3] for v in reg), 'close': reg[-1][4],
            'volumen': sum(v[5] or 0 for v in reg), 'velas': reg,
        })
    return dias

def es_verde(d): return d['close'] >= d['open']

def medir_short(velas, entrada, idx):
    stop = entrada*(1+STOP_PCT/100); target = entrada*(1-TARGET_PCT/100)
    for v in velas[idx:]:
        if v[2] >= stop: return -1.0
        elif v[3] <= target: return TARGET_PCT/STOP_PCT
    return ((entrada - velas[-1][4])/entrada*100)/STOP_PCT

def entrada_pierde_open(dia):
    velas = dia['velas']; op = velas[0][1]
    for k, v in enumerate(velas):
        if v[3] < op: return medir_short(velas, op, k+1)
    return None

def entrada_pierde_vwap(dia):
    velas = dia['velas']
    for k, v in enumerate(velas):
        if v[6] is not None and v[4] < v[6]:
            return medir_short(velas, v[4], k+1)
    return None

def entrada_dia_sig(dia):
    velas = dia['velas']
    return medir_short(velas, velas[0][1], 1)

ENTRADAS = {'pierde_open': entrada_pierde_open,
            'pierde_vwap': entrada_pierde_vwap,
            'dia_sig': entrada_dia_sig}

# Precargar días de todos los tickers
conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print(f"Cargando días de {len(simbolos)} tickers...")
dias_tk = {}
for sym in simbolos:
    d = reconstruir_dias(sym)
    if len(d) > 4: dias_tk[sym] = d

def es_frd(dias, i, min_v, tipo):
    if i < min_v: return False
    if not all(es_verde(d) for d in dias[i-min_v:i]): return False
    dia, ant = dias[i], dias[i-1]
    ra = dia['close'] < dia['open']
    rc = dia['close'] < ant['close']
    if tipo == 'apertura': return ra
    if tipo == 'cierre_ant': return rc
    return ra and rc

def sobreext(dias, i, min_v):
    prev = dias[i-min_v:i]
    mn = min(d['low'] for d in prev)
    mx = max(d['high'] for d in prev)
    return (mx-mn)/mn*100 if mn > 0 else 0

# ── BARRIDO COMPLETO ──
print("Ejecutando barrido de 108 combinaciones...\n")
resultados = []

for min_v in [1, 2, 3]:
    for tipo in ['apertura', 'cierre_ant', 'ambas']:
        for vol_decr in [False, True]:
            for sob_min in [0, 30]:
                for ent_nombre, ent_fn in ENTRADAS.items():
                    trades = []
                    for sym, dias in dias_tk.items():
                        for i in range(len(dias)-1):
                            if not es_frd(dias, i, min_v, tipo):
                                continue
                            if vol_decr and not (dias[i]['volumen'] < dias[i-1]['volumen']):
                                continue
                            if sob_min > 0 and sobreext(dias, i, min_v) < sob_min:
                                continue
                            r = ent_fn(dias[i+1])
                            if r is not None:
                                trades.append(r)
                    n = len(trades)
                    if n < 30:
                        continue
                    total = sum(trades)
                    wins = sum(1 for r in trades if r > 0)
                    resultados.append({
                        'v': min_v, 'tipo': tipo, 'vol': vol_decr, 'sob': sob_min,
                        'ent': ent_nombre, 'n': n,
                        'r_neto': total/n - COSTE_R, 'win': wins/n*100,
                    })

resultados.sort(key=lambda x: x['r_neto'], reverse=True)

print("="*90)
print(f"RANKING First Red Day SHORT · stop{STOP_PCT}/target{TARGET_PCT} · coste{COSTE_R}R · min 30 trades")
print("="*90)
print(f"\n{'#':<4}{'Verdes':<7}{'TipoRojo':<12}{'VolDcr':<8}{'Sobre':<7}{'Entrada':<13}{'N':>6}{'R neto':>10}{'Win%':>7}")
print("-"*88)
for idx, r in enumerate(resultados, 1):
    vol_s = 'Sí' if r['vol'] else 'No'
    sob_s = f"≥{r['sob']}%" if r['sob'] else '-'
    print(f"{idx:<4}{r['v']:<7}{r['tipo']:<12}{vol_s:<8}{sob_s:<7}{r['ent']:<13}{r['n']:>6}{r['r_neto']:>+9.3f}R{r['win']:>6.0f}%")

print(f"\nTotal combinaciones con muestra suficiente: {len(resultados)}")
