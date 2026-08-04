"""
RUTINA DIARIA — corre scanner, actualiza intradía, repara datos faltantes,
consulta SEC EDGAR, y ahora también shortable + huecos de intradía vía
Interactive Brokers. Se corre desde la RAÍZ del proyecto (junto a
smallC.py). Los pasos 5 y 6 necesitan IB Gateway abierto — si no lo está,
fallan solos con un aviso claro y el resto de la rutina sigue igual.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from database import Database

# ══════════════════════════════════════════════════════════════
#  CRITERIOS DEL SCANNER — los de siempre + el perfil de traders de X
#  (Charlie de la Vega, CF Iglesias, Xavier Comas, Cesc XN)
# ══════════════════════════════════════════════════════════════
PRECIO_MIN = 0
PRECIO_MAX = 20
CAMBIO_MIN = 5
VOLUMEN_MIN = 500_000

FLOAT_MAX_M = 5.0      # millones -- del perfil de traders de X
INST_MAX_PCT = 10.0    # % institucional -- del mismo perfil

DIAS_SEC_ATRAS = 14
PUERTO_IB = 4002

db = Database()
db.crear_tabla()

print("=" * 70)
print("PASO 1/6 — Lanzando scanner de Finviz")
print("=" * 70)
try:
    tickers_nuevos = db.obtener_small_caps_finviz(
        cambio_min=CAMBIO_MIN, volumen_min=VOLUMEN_MIN,
        precio_min=PRECIO_MIN, precio_max=PRECIO_MAX,
        float_max_millones=FLOAT_MAX_M, inst_max_pct=INST_MAX_PCT
    )
    print(f"✓ Scanner OK: {len(tickers_nuevos)} tickers encontrados\n")
except Exception as e:
    print(f"✗ Scanner FALLÓ: {e}\n")
    tickers_nuevos = []

print("=" * 70)
print("PASO 2/6 — Actualizando intradía de todos los tickers en seguimiento")
print("=" * 70)
tickers_seg = db.obtener_tickers_seguimiento()
fallos_intradia = []
for t in tickers_seg:
    symbol = t[0]
    try:
        db.descargar_intradia_con_vwap(symbol)
    except Exception:
        fallos_intradia.append(symbol)
print(f"✓ Intradía actualizado: {len(tickers_seg) - len(fallos_intradia)}/{len(tickers_seg)} tickers")
if fallos_intradia:
    print(f"✗ Fallaron: {fallos_intradia}")
print()

print("=" * 70)
print("PASO 3/6 — Reparando float/RVOL/institucional faltantes")
print("=" * 70)
try:
    reparados, sin_encontrar = db.reparar_datos_finviz_faltantes()
    print(f"✓ {reparados} reparados · {len(sin_encontrar)} sin encontrar\n")
except Exception as e:
    print(f"✗ Reparación FALLÓ: {e}\n")

print("=" * 70)
print("PASO 4/6 — Consultando SEC EDGAR (filings recientes: 8-K, S-1, 424B5...)")
print("=" * 70)
try:
    simbolos_todos = [t[0] for t in db.obtener_tickers_seguimiento()]
    alertas = db.consultar_alertas_sec(simbolos_todos, dias_atras=DIAS_SEC_ATRAS)

    FORMS_DILUCION = {'S-1', 'S-1/A', 'S-3', 'S-3/A', '424B4', '424B5'}
    dilucion = {}
    genericas = {}
    for symbol, lista in alertas.items():
        for a in lista:
            if a['form'] in FORMS_DILUCION:
                dilucion.setdefault(symbol, []).append(a)
            else:
                genericas.setdefault(symbol, []).append(a)

    if dilucion:
        print(f"🔴 DILUCIÓN / OFERTA DE ACCIONES — {len(dilucion)} tickers (alta prioridad):")
        for symbol, lista in dilucion.items():
            for a in lista:
                print(f"    {symbol}: {a['form']} el {a['fecha']}")
    else:
        print("✓ Sin filings de dilución en la ventana consultada")

    if genericas:
        print(f"\n⚪ 8-K genéricos — {len(genericas)} tickers (informativo):")
        for symbol, lista in genericas.items():
            fechas = ', '.join(a['fecha'] for a in lista)
            print(f"    {symbol}: {len(lista)}x 8-K ({fechas})")
    else:
        print("✓ Sin 8-K genéricos en la ventana")
except Exception as e:
    print(f"✗ Consulta SEC FALLÓ: {e}")
print()

print("=" * 70)
print("PASO 5/6 — Disponibilidad para corto (shortable) vía Interactive Brokers")
print("=" * 70)
try:
    from ib_async import IB, Stock
    ib = IB()
    ib.connect('127.0.0.1', PUERTO_IB, clientId=20)
    ib.reqMarketDataType(3)

    conn = db.conectar(); cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE scanner_results ADD COLUMN shortable_shares REAL')
    except Exception:
        pass
    conn.commit()
    cursor.execute('SELECT DISTINCT symbol FROM scanner_results')
    simbolos_short = [r[0] for r in cursor.fetchall()]
    conn.close()

    guardados = 0
    for sym in simbolos_short:
        try:
            contrato = Stock(sym, 'SMART', 'USD')
            ib.qualifyContracts(contrato)
            ticker_data = ib.reqMktData(contrato, genericTickList='236')
            ib.sleep(1.2)
            shares = ticker_data.shortableShares
            if shares is not None:
                conn = db.conectar(); cursor = conn.cursor()
                cursor.execute('UPDATE scanner_results SET shortable_shares=? WHERE symbol=?', (shares, sym))
                conn.commit(); conn.close()
                guardados += 1
            ib.cancelMktData(contrato)
        except Exception:
            continue
    ib.disconnect()
    print(f"✓ Shortable actualizado: {guardados}/{len(simbolos_short)} tickers\n")
except Exception as e:
    print(f"✗ PASO 5 FALLÓ (¿está IB Gateway abierto?): {e}\n")

print("=" * 70)
print("PASO 6/6 — Rellenando huecos de intradía vía Interactive Brokers")
print("=" * 70)
try:
    from ib_async import IB, Stock
    ib = IB()
    ib.connect('127.0.0.1', PUERTO_IB, clientId=21)
    ib.reqMarketDataType(3)

    conn = db.conectar(); cursor = conn.cursor()
    cursor.execute('''SELECT DISTINCT symbol FROM scanner_results
                       WHERE symbol NOT IN (SELECT DISTINCT symbol FROM intraday_data)''')
    simbolos_sin_datos = [r[0] for r in cursor.fetchall()]
    conn.close()

    LIMITE = 20
    print(f"  {len(simbolos_sin_datos)} tickers sin intradía, procesando hasta {LIMITE}...")
    for sym in simbolos_sin_datos[:LIMITE]:
        try:
            contrato = Stock(sym, 'SMART', 'USD')
            ib.qualifyContracts(contrato)
            fecha_fin = ''
            conn = db.conectar(); cursor = conn.cursor()
            total_guardadas = 0
            for _ in range(15):
                barras = ib.reqHistoricalData(contrato, endDateTime=fecha_fin, durationStr='2 D',
                                                barSizeSetting='5 mins', whatToShow='TRADES', useRTH=False)
                if not barras:
                    break
                for b in barras:
                    dt_str = b.date.strftime('%Y-%m-%d %H:%M:%S%z')
                    dt_str = dt_str[:-2] + ':' + dt_str[-2:]
                    cursor.execute('''INSERT OR IGNORE INTO intraday_data
                        (symbol, datetime, interval, open, high, low, close, volume, sesion)
                        VALUES (?,?,?,?,?,?,?,?,?)''',
                        (sym, dt_str, '5m', b.open, b.high, b.low, b.close, b.volume, 'regular'))
                    total_guardadas += 1
                fecha_fin = barras[0].date.strftime('%Y%m%d %H:%M:%S')
                ib.sleep(1.2)
            conn.commit(); conn.close()
            print(f"  ✓ {sym}: {total_guardadas} velas")
        except Exception as e:
            print(f"  ✗ {sym}: {e}")
    ib.disconnect()
    print("✓ Huecos de intradía rellenados\n")
except Exception as e:
    print(f"✗ PASO 6 FALLÓ (¿está IB Gateway abierto?): {e}\n")

print("=" * 70)
print("RUTINA COMPLETA")
print("=" * 70)