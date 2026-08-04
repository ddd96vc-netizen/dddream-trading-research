"""
GREEN TO RED + VWAP REJECTION (SHORT) - barridos.
Ambas con entrada realista (sin lookahead) y R en corto.
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

def sobreext(dias, i, n):
    prev = dias[max(0,i-n):i]
    if not prev: return 0
    mn = min(d['low'] for d in prev); mx = max(d['high'] for d in prev)
    return (mx-mn)/mn*100 if mn > 0 else 0

conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()
print(f"Cargando {len(simbolos)} tickers...\n")
dias_tk = {}
for sym in simbolos:
    d = reconstruir_dias(sym)
    if len(d) > 4: dias_tk[sym] = d

# ═══════════════ GREEN TO RED ═══════════════
# Día abre verde (open > cierre_ant), y luego cruza a rojo (close < cierre_ant).
# Entrada: cuando el precio cruza por debajo del cierre del día anterior.
print("Ejecutando Green to Red...")
res_g2r = []
for sob_min in [0, 30, 50]:
    for dias_sob in [2, 3]:
        trades = []
        for sym, dias in dias_tk.items():
            for i in range(1, len(dias)-1):
                ant = dias[i-1]; dia = dias[i]
                # Abre verde (por encima del cierre anterior)
                if dia['open'] <= ant['close']:
                    continue
                if sob_min > 0 and sobreext(dias, i, dias_sob) < sob_min:
                    continue
                # Buscar el cruce intradía por debajo del cierre anterior
                velas = dia['velas']
                for k, v in enumerate(velas):
                    if v[4] < ant['close']:  # cruzó a rojo
                        r = medir_short(velas, v[4], k+1)
                        if r is not None:
                            trades.append(r)
                        break
        n = len(trades)
        if n < 30: continue
        total = sum(trades); wins = sum(1 for r in trades if r > 0)
        res_g2r.append((sob_min, dias_sob, n, total/n - COSTE_R, wins/n*100))

res_g2r.sort(key=lambda x: x[3], reverse=True)
print("\n" + "="*66)
print(f"RANKING GREEN TO RED SHORT · stop{STOP_PCT}/target{TARGET_PCT} · coste{COSTE_R}R")
print("="*66)
print(f"\n{'#':<4}{'Sobre':<8}{'DíasSob':<9}{'N':>7}{'R neto':>11}{'Win%':>8}")
print("-"*46)
for idx, (sob, ds, n, rn, w) in enumerate(res_g2r, 1):
    sob_s = f"≥{sob}%" if sob else '-'
    print(f"{idx:<4}{sob_s:<8}{ds:<9}{n:>7}{rn:>+10.3f}R{w:>7.0f}%")
if not res_g2r: print("Sin muestra suficiente.")

# ═══════════════ VWAP REJECTION ═══════════════
# Día bajista (close < open). El precio rebota hacia el VWAP pero es rechazado.
# Entrada: cuando el precio toca el VWAP desde abajo y vuelve a caer.
print("\n\nEjecutando VWAP Rejection...")
res_vr = []
for sob_min in [0, 30, 50]:
    for dias_sob in [2, 3]:
        trades = []
        for sym, dias in dias_tk.items():
            for i in range(1, len(dias)):
                dia = dias[i]
                if sob_min > 0 and sobreext(dias, i, dias_sob) < sob_min:
                    continue
                velas = dia['velas']
                # Buscar rechazo en VWAP: precio sube tocando VWAP y la siguiente cae
                for k in range(len(velas)-1):
                    v = velas[k]; vwap = v[6]
                    if vwap is None: continue
                    # toca el vwap por abajo (high alcanza vwap pero close por debajo)
                    if v[2] >= vwap and v[4] < vwap:
                        r = medir_short(velas, v[4], k+1)
                        if r is not None:
                            trades.append(r)
                        break
        n = len(trades)
        if n < 30: continue
        total = sum(trades); wins = sum(1 for r in trades if r > 0)
        res_vr.append((sob_min, dias_sob, n, total/n - COSTE_R, wins/n*100))

res_vr.sort(key=lambda x: x[3], reverse=True)
print("\n" + "="*66)
print(f"RANKING VWAP REJECTION SHORT · stop{STOP_PCT}/target{TARGET_PCT} · coste{COSTE_R}R")
print("="*66)
print(f"\n{'#':<4}{'Sobre':<8}{'DíasSob':<9}{'N':>7}{'R neto':>11}{'Win%':>8}")
print("-"*46)
for idx, (sob, ds, n, rn, w) in enumerate(res_vr, 1):
    sob_s = f"≥{sob}%" if sob else '-'
    print(f"{idx:<4}{sob_s:<8}{ds:<9}{n:>7}{rn:>+10.3f}R{w:>7.0f}%")
if not res_vr: print("Sin muestra suficiente.")
