"""
CATALIZADOR - version AFINADA. Solo cuenta como catalizador valido si la
noticia se publico ANTES de la hora de entrada de ESE trade en concreto.
Requiere haber corrido noticias_lote.py YA CON el parche de hora.
"""
import sqlite3
from collections import defaultdict

DB = 'dddream.db'
COSTE_R = 0.1

def conectar():
    return sqlite3.connect(DB)

def cargar_noticias_con_hora():
    conn = conectar(); c = conn.cursor()
    c.execute("SELECT symbol, fecha, hora FROM noticias WHERE hora IS NOT NULL")
    filas = c.fetchall(); conn.close()
    mapa = defaultdict(list)
    for sym, fecha, hora in filas:
        mapa[(sym, fecha)].append(hora)
    return mapa

def medir_long(velas, entrada, idx, stop_pct, target_pct):
    stop = entrada * (1 - stop_pct / 100)
    target = entrada * (1 + target_pct / 100)
    for v in velas[idx:]:
        if v[3] <= stop: return -1.0
        elif v[2] >= target: return target_pct / stop_pct
    return ((velas[-1][4] - entrada) / entrada * 100) / stop_pct

def trades_gapgo_con_hora(symbol):
    conn = conectar(); c = conn.cursor()
    c.execute("""SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval='5m' ORDER BY datetime""", (symbol,))
    datos = c.fetchall(); conn.close()
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
        hora_entrada = reg[ridx][0][11:16]
        rv = rvol30.get(fecha)
        if rv is None or rv <= 1.5:
            continue
        if not ('09:30' <= hora_entrada < '10:00'):
            continue
        entrada = reg[ridx][4]
        r = medir_long(reg, entrada, ridx + 1, 2.0, 10.0)
        trades.append((fecha, hora_entrada, r))
    return trades

conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print("Cargando noticias con hora...")
noticias = cargar_noticias_con_hora()
total_con_hora = sum(len(v) for v in noticias.values())
print(f"  {total_con_hora} noticias con hora registrada, en {len(noticias)} pares (ticker, fecha)\n")

if total_con_hora == 0:
    print("Aviso: no hay noticias con hora guardada todavia.")
    print("Aplica el parche a noticias_lote.py y vuelve a correrlo antes de esto.")
    raise SystemExit

con_catalizador_previo = []
con_noticia_pero_tarde = []
sin_noticia = []

for sym in simbolos:
    for fecha, hora_entrada, r in trades_gapgo_con_hora(sym):
        horas_noticia = noticias.get((sym, fecha))
        if not horas_noticia:
            sin_noticia.append(r)
        elif any(h < hora_entrada for h in horas_noticia):
            con_catalizador_previo.append(r)
        else:
            con_noticia_pero_tarde.append(r)

def evaluar(lista, nombre):
    n = len(lista)
    if n < 20:
        print(f"  {nombre:<34}: muestra insuficiente ({n})")
        return
    total = sum(lista)
    wins = sum(1 for r in lista if r > 0)
    print(f"  {nombre:<34}: {n:>5} trades | R neto {total / n - COSTE_R:+.3f}R | win {wins / n * 100:.0f}%")

print("=" * 72)
print("GAP & GO - catalizador AFINADO (noticia publicada ANTES de la entrada)")
print("=" * 72)
evaluar(con_catalizador_previo, "Noticia ANTES de entrar (real)")
evaluar(con_noticia_pero_tarde, "Noticia el mismo dia, pero DESPUES")
evaluar(sin_noticia, "Sin noticia ese dia")

print("\nSolo 'Noticia ANTES de entrar' es un filtro que de verdad podrias")
print("usar en vivo. Si 'DESPUES' tambien sale bien, confirma que la mejora")
print("anterior era causa-al-reves (el ticker se movio y LUEGO salieron")
print("noticias sobre el movimiento).")