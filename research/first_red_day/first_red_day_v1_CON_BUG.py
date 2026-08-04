"""
⚠️ ARCHIVO ARCHIVADO A PROPÓSITO — CONTIENE UN BUG DE LOOKAHEAD BIAS.

Esta fue la PRIMERA versión del detector de First Red Day. Dio un
resultado de +0.670R que parecía espectacular -- y era FALSO.

EL BUG: la función medir_short_r() entra en el open del mismo día que
se está evaluando como "rojo", pero decidir si un día es rojo requiere
saber su cierre -- información que en la vida real todavía no existe en
el momento de la apertura. El código, sin querer, usaba el futuro para
decidir el pasado.

EL ARREGLO está en frd_realista.py (mismo repositorio): la entrada se
mueve al día SIGUIENTE (D+1) al rojo ya confirmado, usando solo
información que en ese momento ya es pasado.

Se conserva este archivo tal cual, sin corregir, como evidencia del
proceso de validación -- cazar este tipo de error es la lección más
importante de todo el proyecto.
"""

import sqlite3
from collections import defaultdict

DB = 'dddream.db'
COSTE_R = 0.1

# Parámetros de riesgo para el short
STOP_PCT = 3.0    # si sube 3% desde entrada -> stop (pierdes -1R)
TARGET_PCT = 6.0  # si baja 6% desde entrada -> target (ganas +2R)

def conectar():
    return sqlite3.connect(DB)

def reconstruir_dias(symbol):
    """Reconstruye días (open, close, high, low, volumen) desde el intradía 5m."""
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, sesion
                 FROM intraday_data WHERE symbol=? AND interval='5m' ORDER BY datetime''', (symbol,))
    datos = c.fetchall(); conn.close()
    if not datos:
        return []
    por_dia = defaultdict(list)
    for d in datos:
        por_dia[d[0][:10]].append(d)
    dias = []
    for fecha in sorted(por_dia.keys()):
        regular = [v for v in por_dia[fecha] if len(v) <= 6 or v[6] == 'regular']
        if not regular:
            continue
        dias.append({
            'fecha': fecha,
            'open': regular[0][1],
            'high': max(v[2] for v in regular),
            'low': min(v[3] for v in regular),
            'close': regular[-1][4],
            'volumen': sum(v[5] or 0 for v in regular),
            'velas': regular,  # para medir el R intradía del día rojo
        })
    return dias

def es_verde(dia):
    return dia['close'] >= dia['open']

def medir_short_r(dia_rojo):
    """
    Simula un short en el día rojo. Entrada = apertura del día rojo.
    Stop arriba (STOP_PCT), target abajo (TARGET_PCT). Lo que toque primero.
    Recorre las velas intradía del día rojo.
    """
    velas = dia_rojo['velas']
    if len(velas) < 2:
        return None
    entrada = velas[0][1]  # open del día
    stop = entrada * (1 + STOP_PCT/100)   # stop ARRIBA
    target = entrada * (1 - TARGET_PCT/100)  # target ABAJO

    for v in velas[1:]:
        high, low = v[2], v[3]
        if high >= stop:   # tocó stop (subió) -> conservador: stop primero
            return -1.0
        elif low <= target:  # tocó target (bajó) -> gana
            return TARGET_PCT/STOP_PCT
    # No tocó ninguno: resultado por cierre (short: gano si cerró por debajo)
    cierre = velas[-1][4]
    mov_favor = ((entrada - cierre)/entrada*100)  # positivo si bajó
    return mov_favor / STOP_PCT

def detectar_first_red_day(dias, min_verdes, tipo_rojo, exigir_vol):
    """
    min_verdes: 1, 2 o 3 días verdes previos
    tipo_rojo: 'apertura' | 'cierre_ant' | 'ambas'
    exigir_vol: True/False (volumen del rojo < volumen del verde previo)
    """
    trades = []
    for i in range(min_verdes, len(dias)):
        # Comprobar N días verdes consecutivos antes
        previos = dias[i-min_verdes:i]
        if not all(es_verde(d) for d in previos):
            continue

        dia = dias[i]
        ant = dias[i-1]

        # Definición de rojo
        rojo_apertura = dia['close'] < dia['open']
        rojo_cierre_ant = dia['close'] < ant['close']
        if tipo_rojo == 'apertura' and not rojo_apertura:
            continue
        elif tipo_rojo == 'cierre_ant' and not rojo_cierre_ant:
            continue
        elif tipo_rojo == 'ambas' and not (rojo_apertura and rojo_cierre_ant):
            continue

        # Filtro de volumen decreciente
        if exigir_vol and not (dia['volumen'] < ant['volumen']):
            continue

        r = medir_short_r(dia)
        if r is not None:
            trades.append(r)
    return trades

# ── Recopilar todos los tickers ──
conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]; conn.close()

print(f"Reconstruyendo días de {len(simbolos)} tickers...\n")
dias_por_ticker = {}
for sym in simbolos:
    d = reconstruir_dias(sym)
    if d:
        dias_por_ticker[sym] = d

# ── Probar las 18 combinaciones ──
print("="*78)
print(f"FIRST RED DAY (SHORT) · stop {STOP_PCT}%/target {TARGET_PCT}% · coste {COSTE_R}R")
print("="*78)

resultados = []
for min_v in [1, 2, 3]:
    for tipo in ['apertura', 'cierre_ant', 'ambas']:
        for vol in [False, True]:
            todos_trades = []
            for sym, dias in dias_por_ticker.items():
                todos_trades.extend(detectar_first_red_day(dias, min_v, tipo, vol))
            n = len(todos_trades)
            if n < 30:
                continue
            total_r = sum(todos_trades)
            wins = sum(1 for r in todos_trades if r > 0)
            r_esp = total_r/n
            resultados.append({
                'min_v': min_v, 'tipo': tipo, 'vol': vol,
                'n': n, 'r_esp': r_esp, 'r_neto': r_esp - COSTE_R,
                'win': wins/n*100
            })

resultados.sort(key=lambda x: x['r_neto'], reverse=True)

print(f"\n{'Verdes':<7}{'Tipo rojo':<12}{'VolDecr':<9}{'N':>6}{'R bruto':>10}{'R neto':>10}{'Win%':>7}")
print("-"*68)
for r in resultados:
    vol_s = 'Sí' if r['vol'] else 'No'
    print(f"{r['min_v']:<7}{r['tipo']:<12}{vol_s:<9}{r['n']:>6}{r['r_esp']:>+9.3f}R{r['r_neto']:>+9.3f}R{r['win']:>6.0f}%")

if resultados:
    mejor = resultados[0]
    print(f"\n{'='*78}")
    print(f"MEJOR: {mejor['min_v']} verdes + rojo '{mejor['tipo']}' + vol decreciente '{'Sí' if mejor['vol'] else 'No'}'")
    print(f"  → R neto {mejor['r_neto']:+.3f}R · {mejor['n']} trades · win {mejor['win']:.0f}%")
