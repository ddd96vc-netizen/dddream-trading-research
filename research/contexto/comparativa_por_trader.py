"""
COMPARATIVA POR TRADER — con seguimiento de muestra. Usa el DÍA EXACTO
de cada avistamiento (reconstruido del intradía, no "el dato más
reciente" del scanner, que puede ser de otra fecha muy distinta), y
además marca con claridad qué traders ya tienen muestra suficiente para
confiar en sus números, y cuáles necesitan que sigas metiendo tickers.
Corre esto cada vez que metas tickers nuevos -- no hace falta esperar a
tener "suficientes", el propio script te avisa.
"""
import sqlite3
import statistics
from collections import defaultdict

DB = 'dddream.db'   # <-- ajusta la ruta si hace falta (misma que tus otros scripts)
UMBRAL_MUESTRA = 15   # a partir de aqui, "muestra suficiente" (ajustable)

def conectar():
    return sqlite3.connect(DB)

def reconstruir_dias(symbol):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT datetime, open, high, low, close, volume, vwap, sesion
                 FROM intraday_data WHERE symbol=? AND interval='5m' ORDER BY datetime''', (symbol,))
    datos = c.fetchall(); conn.close()
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
        dias[fecha] = {'close': reg[-1][4], 'volumen': sum(v[5] or 0 for v in reg)}

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
            dias[fecha]['rvol'] = round(dias[fecha]['volumen'] / prom, 2) if prom > 0 else None
        else:
            dias[fecha]['rvol'] = None

    return dias

def obtener_float_inst(symbol):
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT float_shares, inst_own FROM scanner_results
                 WHERE symbol=? ORDER BY fecha DESC LIMIT 1''', (symbol,))
    row = c.fetchone(); conn.close()
    if not row:
        return None, None
    float_shares, inst_own = row
    return (float_shares / 1e6 if float_shares else None), inst_own

conn = conectar(); c = conn.cursor()
c.execute('SELECT symbol, fecha, trader FROM x_avistamientos')
avistamientos = c.fetchall()
conn.close()

campos = ['price', 'change_pct', 'volume', 'rvol', 'float_M', 'inst_own']
datos_por_trader = defaultdict(lambda: {campo: [] for campo in campos})
total_avistamientos = defaultdict(int)
sin_cobertura = defaultdict(int)
cache_dias = {}

for symbol, fecha, trader in avistamientos:
    trader = trader.strip()
    total_avistamientos[trader] += 1
    if symbol not in cache_dias:
        cache_dias[symbol] = reconstruir_dias(symbol)
    dias = cache_dias[symbol]

    if fecha not in dias:
        sin_cobertura[trader] += 1
        continue

    dia = dias[fecha]
    float_M, inst_own = obtener_float_inst(symbol)
    valores = {
        'price': dia['close'], 'change_pct': dia.get('change_pct'),
        'volume': dia['volumen'], 'rvol': dia.get('rvol'),
        'float_M': float_M, 'inst_own': inst_own,
    }
    for campo, val in valores.items():
        if val is not None:
            datos_por_trader[trader][campo].append(val)

def resumen(lista):
    if not lista:
        return None
    return {'n': len(lista), 'media': statistics.mean(lista), 'mediana': statistics.median(lista)}

# -- Panel de seguimiento: quien tiene muestra suficiente, quien no --
print("=" * 72)
print(f"PANEL DE SEGUIMIENTO — umbral de muestra suficiente: {UMBRAL_MUESTRA} avistamientos")
print("=" * 72)

todos_traders = sorted(total_avistamientos.keys(), key=lambda t: -total_avistamientos[t])
suficientes = []
pocos = []

for trader in todos_traders:
    total = total_avistamientos[trader]
    sin_cob = sin_cobertura[trader]
    con_datos = total - sin_cob
    estado = "✓ MUESTRA SUFICIENTE" if con_datos >= UMBRAL_MUESTRA else "⚠ pocas muestras — sigue metiendo"
    print(f"  {trader:<24} {total:>4} avistamientos ({con_datos} con datos, {sin_cob} sin cobertura)  {estado}")
    if con_datos >= UMBRAL_MUESTRA:
        suficientes.append(trader)
    else:
        pocos.append(trader)

print(f"\n✓ Con muestra suficiente ({len(suficientes)}): {', '.join(suficientes) if suficientes else '— ninguno todavía —'}")
print(f"⚠ Necesitan más tickers ({len(pocos)}): {', '.join(pocos) if pocos else '— ninguno —'}")

# -- Tabla de metricas, TODOS los traders sin importar tamano --
print("\n" + "=" * 72)
for campo in campos:
    print(f"\n--- {campo} (del DIA EXACTO en que se operó) ---")
    print(f"{'Trader':<24}{'N':>5}{'Media':>15}{'Mediana':>15}  Estado")
    print("-" * 72)
    for trader in todos_traders:
        r = resumen(datos_por_trader[trader][campo])
        marca = "✓" if trader in suficientes else "⚠"
        if r:
            print(f"{trader:<24}{r['n']:>5}{r['media']:>15,.2f}{r['mediana']:>15,.2f}  {marca}")
        else:
            print(f"{trader:<24}{'sin datos':>35}  {marca}")

print("\n" + "=" * 72)
print(f"⚠ = fíate poco todavía (menos de {UMBRAL_MUESTRA} avistamientos con datos).")
print("✓ = ya puedes empezar a sacar conclusiones con más confianza.")
print("Vuelve a correr este script cada vez que metas tickers nuevos --")
print("verás cómo los ⚠ se van convirtiendo en ✓ con el tiempo.")