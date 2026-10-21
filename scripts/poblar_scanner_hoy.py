"""
poblar_scanner_hoy.py
--------------------------------
Versión liviana de rutina_diaria.py que corre SOLO el Paso 1 (escaneo de
Finviz -> scanner_results). No toca intradía, SEC EDGAR, ni shortable.

POR QUE EXISTE
rutina_diaria.py tiene 6 pasos; el Paso 2/6 (actualizar intradía de todo
el universo tracked) puede tardar más de 30 minutos. paper_trading_monitor.py
necesita solo el Paso 1 (poblar scanner_results de HOY) antes de la
apertura del mercado, y no debe bloquearse esperando los otros 5 pasos.

DOS BUSQUEDAS, NO UNA — fix del 2026-09-13 (hoy DESACTIVADO, ver más abajo)
Los primeros 5 días de forward mostraron GAPGO disparando 8 veces y
DUMP 2, pero A2 y FRD CERO veces. La causa: el filtro original solo
buscaba SUBIDAS (Change >= 5%), y A2/FRD son estrategias SHORT que
necesitan que la acción esté cayendo (gap down, cierre rojo). Un
scanner de "está subiendo" nunca les iba a dar candidatos.

Ahora se hacen DOS búsquedas en Finviz — subidas (como antes, sin
tocar) y bajadas (nueva) — y ambas se guardan en la MISMA
scanner_results, para que el monitor en vivo vea el universo completo.

OJO 2026-10-21: esta versión (bajada en Downloads desde el 24/09) nunca
se había copiado al proyecto; el monitor siguió corriendo la de una sola
búsqueda. Se instala ahora adaptada a app/finviz_screener.py, porque
finvizfinance dejó de leer el screener de Finviz. 'Down 5%' ya está
probado contra Finviz real (todos los resultados con cambio negativo).

BUSQUEDA DE BAJADAS DESACTIVADA — 2026-10-21
La llamada a buscar_bajadas() está comentada abajo (la función se deja
intacta). El universo sigue siendo SOLO subidas, Small ($300mln to $2bln):
el validado para A2 y FRD, y el que ya tiene su forward en paper_señales
(A2 33 señales, FRD 38, sobre tickers que entraron como subidas).
Motivo: el monitor lanza esto a las 14:50 hora de España = 8:50 ET, antes
de la apertura, así que el 'Change' de Finviz es probablemente el de la
sesión ANTERIOR: 'Down 5%' traería las que cayeron ayer, no los gap downs
de hoy. Activarla sería una hipótesis nueva: backtestear aparte.

Market cap: 'Small ($300mln to $2bln)' en las dos búsquedas, el
universo con el que se validaron las 4 estrategias. No ampliarlo aquí.

La búsqueda de bajada no reutiliza Database.obtener_small_caps_finviz()
porque esa función solo busca subidas. Usa su propia llamada a Finviz +
enriquecimiento, y hace INSERT directo a scanner_results con columnas
detectadas en tiempo real (evita romperse si el esquema cambia).

Se corre desde la RAIZ del proyecto (así lo lanza el monitor).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from datetime import date

from database import Database

PRECIO_MIN = 0
PRECIO_MAX = 20
CAMBIO_MIN = 5
VOLUMEN_MIN = 500_000
FLOAT_MAX_M = None
INST_MAX_PCT = None
MARKET_CAP = 'Small ($300mln to $2bln)'

# Búsqueda de bajadas, para A2 y FRD
DOWN_CAMBIO_MIN = 5.0        # magnitud; se busca 'Down 5%' en Finviz


def _mapear_bajada(pct):
    """Opciones 'Down X%' de Finviz."""
    for umbral in (20, 15, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1):
        if pct >= umbral:
            return f'Down {umbral}%'
    return 'Down'


def buscar_bajadas(db):
    """Segunda búsqueda: acciones que CAYERON hoy. Se inserta en la
    MISMA scanner_results (no aislada), para que el monitor en vivo
    tenga candidatos para A2 y FRD."""
    from finviz_screener import screener
    import yfinance as yf

    print("\n" + "-" * 70)
    print("Búsqueda 2/2: acciones que CAYERON hoy (para A2 y FRD)")
    print("-" * 70)

    filtros = {
        'Price': '$1 to $20',
        'Change': _mapear_bajada(DOWN_CAMBIO_MIN),
        'Current Volume': 'Over 500K',
        'Market Cap.': MARKET_CAP,
    }
    print(f"Filtros: {filtros}")

    try:
        df = screener('overview', filters_dict=filtros)
    except Exception as e:
        print(f"FALLO consultando Finviz para bajadas: {e}")
        return 0

    if df is None or df.empty:
        print("Sin resultados de bajada hoy (puede ser normal).")
        return 0

    print(f"OK: {len(df)} candidatos a la baja, obteniendo detalles...")
    # El ticker ya viene exacto (data-ticker): sin parche de letra duplicada
    tickers = list(df['Ticker'])

    detalles = db.enriquecer_completo(tickers)

    conn = db.conectar()
    cur = conn.cursor()
    columnas_tabla = {r[1] for r in cur.execute(
        "PRAGMA table_info(scanner_results)").fetchall()}

    hoy = date.today()
    guardados = 0
    for i, (_, row) in enumerate(df.iterrows()):
        symbol = tickers[i]
        try:
            price = float(str(row['Price']).replace(',', '')) if row['Price'] else None
        except ValueError:
            price = None
        try:
            volume = int(float(str(row['Volume']).replace(',', ''))) if row['Volume'] else None
        except ValueError:
            volume = None

        change_pct = None
        try:
            hist = yf.Ticker(symbol).history(period='2d')
            if len(hist) >= 2:
                change_pct = round(((hist['Open'].iloc[-1] - hist['Close'].iloc[-2])
                                    / hist['Close'].iloc[-2]) * 100, 2)
        except Exception:
            pass

        det = detalles.get(symbol, {})
        valores = {
            "fecha": hoy, "symbol": symbol, "price": price,
            "change_pct": change_pct, "volume": volume,
            "float_shares": det.get('float_shares'),
            "short_float_pct": det.get('short_float_pct'),
            "rvol": det.get('rvol'), "gap_pct": det.get('gap_pct'),
            "atr": det.get('atr'), "rsi": det.get('rsi'),
            "inst_own": det.get('inst_own'),
        }
        # Solo columnas que de verdad existen en la tabla (por si el
        # esquema real difiere de lo esperado)
        valores = {k: v for k, v in valores.items() if k in columnas_tabla}

        cols = ", ".join(valores.keys())
        placeholders = ", ".join("?" * len(valores))
        try:
            cur.execute(
                f"INSERT OR IGNORE INTO scanner_results ({cols}) VALUES ({placeholders})",
                list(valores.values()),
            )
            if det:
                print(f"  ✓ {symbol} - Float: {det.get('float_shares')} | "
                      f"Short: {det.get('short_float_pct')}% | "
                      f"RVOL: {det.get('rvol')} | Gap: {det.get('gap_pct')}%")
            else:
                print(f"  ✓ {symbol} - sin datos extra en el screener")
            guardados += 1
        except Exception as e:
            print(f"  Error guardando {symbol}: {e}")

    conn.commit()
    conn.close()
    print(f"\n{guardados} tickers de BAJADA guardados en scanner_results.")
    return guardados


db = Database()
db.crear_tabla()

print("=" * 70)
print("Poblando scanner_results de hoy (solo Paso 1, sin el resto de la rutina)")
print("=" * 70)

print("Búsqueda de acciones que SUBIERON (universo de las 4 estrategias)")
try:
    tickers_subida = db.obtener_small_caps_finviz(
        cambio_min=CAMBIO_MIN, volumen_min=VOLUMEN_MIN,
        precio_min=PRECIO_MIN, precio_max=PRECIO_MAX,
        float_max_millones=FLOAT_MAX_M, inst_max_pct=INST_MAX_PCT,
        market_cap=MARKET_CAP,
    )
    print(f"OK: {len(tickers_subida)} tickers de subida encontrados y guardados.")
except Exception as e:
    print(f"FALLO la búsqueda de subida: {e}")
    tickers_subida = []

# Búsqueda de bajadas DESACTIVADA (ver docstring). Para reactivarla,
# descomentar este bloque y sumar n_bajada en el TOTAL.
# n_bajada = 0
# try:
#     n_bajada = buscar_bajadas(db)
# except Exception as e:
#     print(f"\nFALLO la búsqueda de bajada (no crítico, la de subida ya está "
#           f"guardada): {e}")

print("\n" + "=" * 70)
print(f"TOTAL: {len(tickers_subida)} de subida = universo de hoy listo para las 4 estrategias.")
print("=" * 70)

# Si la búsqueda de subidas falló o no trajo nada, salir con error para
# que el monitor lo avise (antes terminaba con código 0 y 0 tickers, y el
# fallo de Finviz pasó desapercibido 3 días).
if not tickers_subida:
    sys.exit(1)
