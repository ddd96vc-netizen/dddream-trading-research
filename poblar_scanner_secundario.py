"""
poblar_scanner_secundario.py
--------------------------------
Universo SECUNDARIO, totalmente aislado del principal. Mismo escaneo de
Finviz, pero con criterios más laxos (~5-8 candidatos/día esperados en
vez de 1-2), guardado en su PROPIA tabla para no mezclarse nunca con
scanner_results (el que usan las 4 estrategias en vivo).

POR QUE EXISTE
El universo principal (CAMBIO_MIN=5%) viene dando 1-2 candidatos/día,
muy poco para que el monitor tenga con qué trabajar. En vez de tocar el
filtro que ya define "dónde funciona la estrategia" (tu criterio: mejor
calidad que cantidad), este es un segundo pipeline en paralelo, separado
a propósito, para ver cómo se comportan las mismas 4 estrategias en un
universo más amplio, sin contaminar el registro forward principal.

TABLA NUEVA: scanner_results_secundario (mismas columnas que
scanner_results, para poder reusar la misma lógica de análisis después).

LIMITACION IMPORTANTE — precio sin cambiar
finvizfinance solo acepta rangos de precio predefinidos ('$1 to $5',
'$1 to $10', '$1 to $20', etc.) — no admite un máximo arbitrario como
$25 o $30. Para no arriesgar un filtro que silenciosamente no aplique
bien, este script deja el precio IGUAL que el principal ($1-$20) y solo
amplía cambio% y volumen, que sí se pueden extender con opciones nuevas
de Finviz que existen pero el proyecto no usaba (Up 1%/2%/3%/4%,
Over 100K/300K).

SIN PROBAR CONTRA FINVIZ REAL — si alguna de las opciones nuevas
('Up 3%', 'Over 300K') no es un valor válido para finvizfinance, va a
dar error o devolver 0 resultados. Revisá la primera corrida con
cuidado, igual que pasó con otros scripts hoy.

Se corre desde la RAIZ del proyecto.
Uso:
    python poblar_scanner_secundario.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
from datetime import date

from database import Database

# ── Filtro secundario: más laxo que el principal, precio SIN cambiar ──
PRECIO_MIN = 1
PRECIO_MAX = 20          # sin cambiar (ver nota arriba)
CAMBIO_MIN = 3            # antes 5 -> ahora 3
VOLUMEN_MIN = 300_000     # antes 500,000 -> ahora 300,000
FLOAT_MAX_M = None
INST_MAX_PCT = None

TABLA = "scanner_results_secundario"


def _mapear_cambio_extendido(pct):
    """Extiende las opciones de Finviz para 'Change' hacia abajo de 5%.
    Estos valores ('Up 1%'...'Up 4%') existen en el filtro real de
    Finviz pero el proyecto no los usaba todavía — sin probar acá."""
    if pct >= 20: return 'Up 20%'
    if pct >= 15: return 'Up 15%'
    if pct >= 10: return 'Up 10%'
    if pct >= 5:  return 'Up 5%'
    if pct >= 4:  return 'Up 4%'
    if pct >= 3:  return 'Up 3%'
    if pct >= 2:  return 'Up 2%'
    return 'Up 1%'


def _mapear_volumen_extendido(vol):
    """Extiende 'Current Volume' hacia abajo de 200K."""
    if vol >= 2_000_000: return 'Over 2M'
    if vol >= 1_000_000: return 'Over 1M'
    if vol >= 500_000:   return 'Over 500K'
    if vol >= 300_000:   return 'Over 300K'
    if vol >= 200_000:   return 'Over 200K'
    return 'Over 100K'


def crear_tabla_secundaria(conn):
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLA} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE, symbol TEXT, price REAL, change_pct REAL,
            volume INTEGER, float_shares REAL, short_float_pct REAL,
            rvol REAL, gap_pct REAL, atr REAL, rsi REAL, inst_own REAL,
            UNIQUE(fecha, symbol)
        )
    """)
    conn.commit()


def escanear_y_guardar():
    from finviz_screener import screener   # app/finviz_screener.py (finvizfinance dejó de funcionar)
    import yfinance as yf

    db = Database()
    conn = db.conectar()
    crear_tabla_secundaria(conn)

    print("=" * 70)
    print("UNIVERSO SECUNDARIO (aislado, no toca scanner_results)")
    print(f"Filtro: cambio>={CAMBIO_MIN}%  volumen>={VOLUMEN_MIN:,}  "
          f"precio ${PRECIO_MIN}-${PRECIO_MAX} (sin cambios)")
    print("=" * 70)

    filtros = {
        'Price': '$1 to $20',
        'Change': _mapear_cambio_extendido(CAMBIO_MIN),
        'Current Volume': _mapear_volumen_extendido(VOLUMEN_MIN),
        'Market Cap.': 'Small ($300mln to $2bln)',
    }
    print(f"Filtros enviados a Finviz: {filtros}\n")

    try:
        df = screener('overview', filters_dict=filtros)
    except Exception as e:
        print(f"FALLO consultando Finviz: {e}")
        conn.close()
        return

    if df is None or df.empty:
        print("Sin resultados con este filtro.")
        conn.close()
        return

    print(f"OK: {len(df)} candidatos encontrados, obteniendo detalles...")
    # El ticker ya viene exacto (data-ticker): sin parche de letra duplicada
    tickers_encontrados = list(df['Ticker'])

    detalles = db.enriquecer_completo(tickers_encontrados)

    hoy = date.today()
    guardados = 0
    for i, (_, row) in enumerate(df.iterrows()):
        symbol = tickers_encontrados[i]
        price = float(str(row['Price']).replace(',', '')) if row['Price'] else None
        volume = int(float(str(row['Volume']).replace(',', ''))) if row['Volume'] else None

        change_pct = None
        try:
            hist = yf.Ticker(symbol).history(period='2d')
            if len(hist) >= 2:
                change_pct = round(((hist['Open'].iloc[-1] - hist['Close'].iloc[-2])
                                    / hist['Close'].iloc[-2]) * 100, 2)
        except Exception:
            pass

        det = detalles.get(symbol, {})
        float_shares = det.get('float_shares')
        short_float_pct = det.get('short_float_pct')
        rvol = det.get('rvol')
        gap_pct = det.get('gap_pct')
        atr = det.get('atr')
        rsi = det.get('rsi')
        inst_own = det.get('inst_own')

        if det:
            print(f"  {symbol} - Float: {float_shares} | Short: {short_float_pct}% | "
                  f"RVOL: {rvol} | Gap: {gap_pct}%")
        else:
            print(f"  {symbol} - sin datos extra en el screener")

        try:
            conn.execute(f"""
                INSERT OR IGNORE INTO {TABLA}
                (fecha, symbol, price, change_pct, volume, float_shares,
                 short_float_pct, rvol, gap_pct, atr, rsi, inst_own)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (hoy, symbol, price, change_pct, volume, float_shares,
                  short_float_pct, rvol, gap_pct, atr, rsi, inst_own))
            guardados += 1
        except Exception as e:
            print(f"  Error guardando {symbol}: {e}")

    conn.commit()
    conn.close()
    print(f"\nOK: {guardados} tickers guardados en {TABLA} (tabla aislada, "
          "scanner_results principal intacto).")


if __name__ == "__main__":
    escanear_y_guardar()
