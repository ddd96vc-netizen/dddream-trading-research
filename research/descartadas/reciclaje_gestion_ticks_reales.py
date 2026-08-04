"""
RECICLAJE COMO GESTIÓN — PRIMERA PRUEBA DE CONCEPTO, con ticks reales.

No se prueba como señal de entrada (eso ya lo descartamos, dos veces).
Se prueba como TÉCNICA DE GESTIÓN sobre las entradas ya validadas de
First Red Day y Gap & Go: si el precio se mueve en contra, se añade una
unidad; si luego rebota con volumen anómalo, se suelta la mitad. El
stop y el target absolutos NUNCA se mueven del nivel original -- eso
limita el riesgo, no es un martingala sin fondo.

LIMITACIÓN A PROPÓSITO: solo se prueba con señales de los últimos ~20
días (es lo que alcanza el tick histórico gratis de IBKR). La muestra
va a ser chica -- es una prueba de concepto, no una validación final.
Requiere IB Gateway abierto y conectado.
"""
import sqlite3
import datetime
import statistics
from collections import defaultdict
from ib_async import IB, Stock

DB = 'database/dddream.db'   # <-- ajusta la ruta si hace falta
PUERTO = 4002
DIAS_ATRAS_LIMITE = 20   # ventana real de ticks históricos gratis
STOP_USADO = 2.5
TARGET_GAPGO = 12.0
TARGET_FRD = 10.0
MULTIPLICADOR_VOLUMEN_SPIKE = 2.0   # tick 2x el tamaño promedio reciente = "rebote con volumen"

def conectar():
    return sqlite3.connect(DB)

def obtener_intradia(symbol, intervalo='5m'):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval=? ORDER BY datetime''', (symbol, intervalo))
    r = c.fetchall(); conn.close()
    return r

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

def r_simple(velas, entrada, idx, stop_pct, target_pct, direccion):
    if direccion == 'long':
        stop = entrada * (1 - stop_pct / 100); target = entrada * (1 + target_pct / 100)
        for v in velas[idx:]:
            if v[3] <= stop: return -1.0
            elif v[2] >= target: return target_pct / stop_pct
        return ((velas[-1][4] - entrada) / entrada * 100) / stop_pct
    else:
        stop = entrada * (1 + stop_pct / 100); target = entrada * (1 - target_pct / 100)
        for v in velas[idx:]:
            if v[2] >= stop: return -1.0
            elif v[3] <= target: return target_pct / stop_pct
        return ((entrada - velas[-1][4]) / entrada * 100) / stop_pct

conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]
conn.close()

fecha_limite = (datetime.datetime.now() - datetime.timedelta(days=DIAS_ATRAS_LIMITE)).strftime('%Y-%m-%d')
print(f"Solo señales desde {fecha_limite} en adelante (límite del tick histórico)\n")

def señales_gapgo_recientes():
    trades = []
    for sym in simbolos:
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
            if fecha < fecha_limite: continue
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
            if rv is None or rv < 3.0: continue
            if not ('09:30' <= hora < '10:00'): continue
            entrada = reg[ridx][4]
            r_base = r_simple(reg, entrada, ridx + 1, STOP_USADO, TARGET_GAPGO, 'long')
            fecha_hora_inicio = reg[ridx + 1][0] if ridx + 1 < len(reg) else reg[ridx][0]
            trades.append({'symbol': sym, 'datetime': fecha_hora_inicio, 'entrada': entrada,
                            'direccion': 'long', 'target_pct': TARGET_GAPGO, 'r_base': r_base})
    return trades

def señales_frd_recientes():
    trades = []
    for sym in simbolos:
        dias = reconstruir_dias(sym)
        fechas = sorted(dias.keys())
        if len(fechas) < 4: continue
        for i in range(2, len(fechas) - 1):
            prev = [dias[fechas[i - 2]], dias[fechas[i - 1]]]
            if not all(d['close'] >= d['open'] for d in prev): continue
            dia = dias[fechas[i]]
            if not (dia['close'] < dia['open']): continue
            mn = min(d['low'] for d in prev); mx = max(d['high'] for d in prev)
            sob = (mx - mn) / mn * 100 if mn > 0 else 0
            if sob < 50.0: continue
            f_op = fechas[i + 1]
            if f_op < fecha_limite: continue
            d_op = dias[f_op]
            velas = d_op['velas']; op = velas[0][1]
            eidx = None
            for k, v in enumerate(velas):
                if v[3] < op: eidx = k; break
            if eidx is None: continue
            r_base = r_simple(velas, op, eidx + 1, STOP_USADO, TARGET_FRD, 'short')
            fecha_hora_inicio = velas[eidx + 1][0] if eidx + 1 < len(velas) else velas[0][0]
            trades.append({'symbol': sym, 'datetime': fecha_hora_inicio, 'entrada': op,
                            'direccion': 'short', 'target_pct': TARGET_FRD, 'r_base': r_base})
    return trades

print("Detectando señales recientes...")
gapgo = señales_gapgo_recientes()
frd = señales_frd_recientes()
print(f"  Gap & Go (últimos {DIAS_ATRAS_LIMITE} días): {len(gapgo)} señales")
print(f"  First Red Day (últimos {DIAS_ATRAS_LIMITE} días): {len(frd)} señales")

todas = [dict(t, estrategia='GAP & GO') for t in gapgo] + [dict(t, estrategia='FIRST RED DAY') for t in frd]

if not todas:
    print("\nSin señales en la ventana de ticks disponibles. Nada que probar hoy.")
    raise SystemExit

print("\nConectando a Interactive Brokers...")
ib = IB()
ib.connect('127.0.0.1', PUERTO, clientId=40)
ib.reqMarketDataType(3)
print("✓ Conectado\n")

def r_simple_directo(entrada, salida, stop_pct, direccion):
    if direccion == 'long':
        return ((salida - entrada) / entrada * 100) / stop_pct
    else:
        return ((entrada - salida) / entrada * 100) / stop_pct

def simular_reciclaje(symbol, dt_str, entrada, direccion, stop_pct, target_pct):
    try:
        dt = datetime.datetime.fromisoformat(dt_str)
        contrato = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(contrato)
        ticks = ib.reqHistoricalTicks(contrato, startDateTime=dt, endDateTime='',
                                        numberOfTicks=1000, whatToShow='TRADES', useRth=False)
        if not ticks:
            return None
    except Exception:
        return None

    if direccion == 'long':
        stop_price = entrada * (1 - stop_pct / 100)
        target_price = entrada * (1 + target_pct / 100)
        add_trigger = entrada * (1 - 0.5 * stop_pct / 100)
    else:
        stop_price = entrada * (1 + stop_pct / 100)
        target_price = entrada * (1 - target_pct / 100)
        add_trigger = entrada * (1 + 0.5 * stop_pct / 100)

    tamaños_recientes = []
    añadido = False
    precio_add = None
    unidad_a_vendida = False
    r_unidad_a = None

    def toco_stop_o_target(precio):
        if direccion == 'long':
            if precio <= stop_price: return 'stop'
            if precio >= target_price: return 'target'
        else:
            if precio >= stop_price: return 'stop'
            if precio <= target_price: return 'target'
        return None

    for t in ticks:
        precio = t.price
        tamaño = t.size or 1

        resultado = toco_stop_o_target(precio)
        if resultado in ('stop', 'target'):
            precio_final = stop_price if resultado == 'stop' else target_price
            if not añadido:
                return r_simple_directo(entrada, precio_final, stop_pct, direccion)
            r_a = r_unidad_a if unidad_a_vendida else r_simple_directo(precio_add, precio_final, stop_pct, direccion)
            r_b = r_simple_directo(entrada, precio_final, stop_pct, direccion)
            return r_a + r_b

        if not añadido:
            tocado = (direccion == 'long' and precio <= add_trigger) or (direccion == 'short' and precio >= add_trigger)
            if tocado:
                añadido = True
                precio_add = precio
        elif not unidad_a_vendida:
            vol_prom = statistics.mean(tamaños_recientes) if tamaños_recientes else tamaño
            rebote = (direccion == 'long' and precio > precio_add) or (direccion == 'short' and precio < precio_add)
            spike = tamaño >= vol_prom * MULTIPLICADOR_VOLUMEN_SPIKE
            if rebote and spike:
                unidad_a_vendida = True
                r_unidad_a = r_simple_directo(entrada, precio, stop_pct, direccion)

        tamaños_recientes.append(tamaño)
        if len(tamaños_recientes) > 20:
            tamaños_recientes.pop(0)

    ultimo = ticks[-1].price
    if not añadido:
        return r_simple_directo(entrada, ultimo, stop_pct, direccion)
    r_a = r_unidad_a if unidad_a_vendida else r_simple_directo(precio_add, ultimo, stop_pct, direccion)
    r_b = r_simple_directo(entrada, ultimo, stop_pct, direccion)
    return r_a + r_b

print("=" * 74)
print("COMPARANDO: R simple (ya validado) vs R con reciclaje (ticks reales)")
print("=" * 74)

resultados = []
for i, s in enumerate(todas, 1):
    r_recic = simular_reciclaje(s['symbol'], s['datetime'], s['entrada'], s['direccion'], STOP_USADO, s['target_pct'])
    if r_recic is not None:
        print(f"[{i}/{len(todas)}] {s['estrategia']} {s['symbol']}: R simple={s['r_base']:+.2f}  R reciclaje={r_recic:+.2f}")
        resultados.append({'estrategia': s['estrategia'], 'r_base': s['r_base'], 'r_recic': r_recic})
    else:
        print(f"[{i}/{len(todas)}] {s['estrategia']} {s['symbol']}: sin ticks disponibles")
    ib.sleep(1.0)

ib.disconnect()

print("\n" + "=" * 74)
print("RESULTADO — primera prueba de concepto (muestra chica, no concluyente)")
print("=" * 74)
for estrategia in ['GAP & GO', 'FIRST RED DAY']:
    grupo = [r for r in resultados if r['estrategia'] == estrategia]
    if not grupo:
        print(f"\n{estrategia}: sin datos suficientes")
        continue
    n = len(grupo)
    r_base_prom = sum(g['r_base'] for g in grupo) / n
    r_recic_prom = sum(g['r_recic'] for g in grupo) / n
    print(f"\n{estrategia} (N={n})")
    print(f"  R simple (ya validado):  {r_base_prom:+.3f}")
    print(f"  R con reciclaje:          {r_recic_prom:+.3f}")
    print(f"  → {'✓ el reciclaje mejora' if r_recic_prom > r_base_prom else '✗ el reciclaje empeora'}")

print("\nRecuerda: muestra chica a propósito (ventana de ticks limitada).")
print("Esto es una primera señal direccional, no una validación definitiva.")