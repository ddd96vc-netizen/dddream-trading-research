"""
OVEREXTENDED GAP DOWN (SHORT) - barrido completo.
Lógica: acción sobreextendida que abre por debajo del cierre anterior (gap down).
Los compradores atrapados venden en break even -> presión bajista.
Entrada: shortear el rebote de la mañana hacia resistencia del día previo.

Anti-lookahead: el gap down se conoce en la apertura (pasado inmediato).
La entrada se ejecuta intradía sobre el rebote.
"""
import sqlite3
from collections import defaultdict
import sys
sys.stdout.reconfigure(encoding='utf-8')


DB = 'dddream.db'
COSTE_R = 0.1
STOP_PCT = 3.0
TARGET_PCT = 6.0

def conectar(): return sqlite3.connect(DB)

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

def medir_short(velas, entrada, idx):
    stop = entrada*(1+STOP_PCT/100); target = entrada*(1-TARGET_PCT/100)
    for v in velas[idx:]:
        if v[2] >= stop: return -1.0
        elif v[3] <= target: return TARGET_PCT/STOP_PCT
    return ((entrada - velas[-1][4])/entrada*100)/STOP_PCT

# Precargar
conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()
print(f"Cargando {len(simbolos)} tickers...")
dias_tk = {}
for sym in simbolos:
    d = reconstruir_dias(sym)
    if len(d) > 4: dias_tk[sym] = d

def sobreext_previa(dias, i, dias_atras):
    """Subida acumulada en los N días previos al gap down."""
    prev = dias[max(0,i-dias_atras):i]
    if not prev: return 0
    mn = min(d['low'] for d in prev); mx = max(d['high'] for d in prev)
    return (mx-mn)/mn*100 if mn > 0 else 0

# Entrada: rebote hacia resistencia previa
# El día del gap down, esperamos que el precio REBOTE (suba) hacia el cierre
# del día anterior, y shorteamos ahí (venta en resistencia).
def entrada_rebote_resistencia(dia_gap, cierre_ant):
    """Shortear cuando el precio rebota hacia el cierre del día anterior."""
    velas = dia_gap['velas']
    for k, v in enumerate(velas):
        if v[2] >= cierre_ant * 0.98:  # rebote llega cerca (98%) del cierre previo
            return medir_short(velas, v[4], k+1)
    return None

def entrada_pierde_open(dia_gap):
    """Alternativa: shortear cuando pierde el open del día del gap."""
    velas = dia_gap['velas']; op = velas[0][1]
    for k, v in enumerate(velas):
        if v[3] < op:
            return medir_short(velas, op, k+1)
    return None

# ── Barrido ──
print("Ejecutando barrido Overextended Gap Down...\n")
resultados = []

for gap_min in [1, 2, 3]:  # % mínimo de gap down
    for dias_sob in [2, 3]:  # días previos para medir sobreextensión
        for sob_min in [0, 30, 50]:
            for ent_nombre in ['rebote_resist', 'pierde_open']:
                trades = []
                for sym, dias in dias_tk.items():
                    for i in range(1, len(dias)-1):
                        ant = dias[i-1]; dia = dias[i]
                        # Gap down: open del día < cierre anterior en gap_min%
                        gap = (ant['close'] - dia['open']) / ant['close'] * 100
                        if gap < gap_min:
                            continue
                        if sob_min > 0 and sobreext_previa(dias, i, dias_sob) < sob_min:
                            continue
                        if ent_nombre == 'rebote_resist':
                            r = entrada_rebote_resistencia(dia, ant['close'])
                        else:
                            r = entrada_pierde_open(dia)
                        if r is not None:
                            trades.append(r)
                n = len(trades)
                if n < 30: continue
                total = sum(trades); wins = sum(1 for r in trades if r > 0)
                resultados.append({
                    'gap': gap_min, 'dsob': dias_sob, 'sob': sob_min,
                    'ent': ent_nombre, 'n': n,
                    'r_neto': total/n - COSTE_R, 'win': wins/n*100,
                })

resultados.sort(key=lambda x: x['r_neto'], reverse=True)

print("="*82)
print(f"RANKING Overextended Gap Down SHORT · stop{STOP_PCT}/target{TARGET_PCT} · coste{COSTE_R}R")
print("="*82)
print(f"\n{'#':<4}{'GapMin':<8}{'DíasSob':<9}{'Sobre':<8}{'Entrada':<16}{'N':>6}{'R neto':>10}{'Win%':>7}")
print("-"*80)
for idx, r in enumerate(resultados, 1):
    sob_s = f"≥{r['sob']}%" if r['sob'] else '-'
    print(f"{idx:<4}{r['gap']:<8}{r['dsob']:<9}{sob_s:<8}{r['ent']:<16}{r['n']:>6}{r['r_neto']:>+9.3f}R{r['win']:>6.0f}%")

if not resultados:
    print("Sin combinaciones con muestra suficiente (>=30 trades).")
print(f"\nTotal combinaciones válidas: {len(resultados)}")
