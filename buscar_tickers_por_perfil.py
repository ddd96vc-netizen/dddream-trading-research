"""
buscar_tickers_por_perfil.py
===============================
Script APARTE de rutina_diaria.py (no lo toca, no lo reemplaza). Sale a
buscar activamente tickers que cumplan el perfil de cada trader real,
en vez de esperar a que el scanner generico los traiga por casualidad
-- de ~150 tickers reales operados por tus traders, el scanner
generico solo habia pescado una fraccion chica.

Reutiliza tu infraestructura de Finviz ya existente en database.py
(enriquecer_completo), pero corriendola UNA VEZ POR PERFIL, con los
rangos ENSANCHADOS respecto a las medianas exactas -- mejor de mas que
de menos, para no perder candidatos reales por quedarnos cortos.

Todo lo que encuentra se guarda en scanner_results (tu tabla de
siempre, INSERT OR IGNORE -- si rutina_diaria.py ya trajo ese symbol
hoy, no se duplica) y ademas se etiqueta en scanner_perfil_diario con
que perfil lo encontro.

EXTENSIBLE: agregar un perfil nuevo es agregar un diccionario mas a la
lista PERFILES de abajo -- no hace falta tocar el resto del script.

Uso: python buscar_tickers_por_perfil.py
Pensado para encadenarse asi (opcional, no obligatorio):
    python scripts\\rutina_diaria.py && python buscar_tickers_por_perfil.py
"""

import importlib.util
import datetime
import sys
from pathlib import Path

# app/ en el path: database.py y este script importan app/finviz_screener.py
sys.path.insert(0, str(Path(__file__).resolve().parent / "app"))


def cargar_modulo(nombre, candidatos_relativos):
    base = Path(__file__).resolve().parent
    for rel in candidatos_relativos:
        ruta = base / rel
        if ruta.exists():
            spec = importlib.util.spec_from_file_location(nombre, ruta)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise FileNotFoundError(f"No encuentro {nombre} en {candidatos_relativos} (relativo a {base})")


try:
    database_module = cargar_modulo("database_dddream", ["app/database.py", "database.py"])
except ModuleNotFoundError as e:
    print(f"✗ Falta una dependencia de database.py en este entorno: {e}")
    print("  Corre esto con el MISMO python.exe que usaste para rutina_diaria.py")
    raise SystemExit(1)

Database = database_module.Database


# ══════════════════════════════════════════════════════════════════
#  PERFILES A BUSCAR — agregar uno nuevo = agregar un dict a esta lista.
#  Rangos ENSANCHADOS respecto a las medianas exactas de
#  comparativa_por_trader.py, a proposito, para no perder candidatos.
# ══════════════════════════════════════════════════════════════════

PERFILES = [
    {
        'nombre': 'A_runner_positivo',
        'descripcion': 'ulfurtrading/Charlie de la Vega/CF Iglesias/Erotikarl/Xavier Comas',
        # -- filtro inicial en Finviz (grueso, para no perder nada) --
        'finviz_cambio_min': 5, 'finviz_volumen_min': 300_000,
        'finviz_precio_min': 1, 'finviz_precio_max': 20,
        'finviz_market_caps': ['Small ($300mln to $2bln)', 'Micro ($50mln to $300mln)', 'Nano (under $50mln)'],
        # -- filtro final, numerico, ensanchado (float/rvol/change/inst) --
        'float_max': 8.0, 'rvol_min': 2.0, 'change_min': 3.0, 'inst_max': 15.0,
    },
    {
        'nombre': 'A2_runner_fade_rojo',
        'descripcion': 'Crvicky21 -- mismo float chico, pero RVOL bajo y dia ROJO',
        'finviz_cambio_min': -30,  # se mapea a 'Down X%' -- ver mapear_cambio_finviz()
        'finviz_volumen_min': 300_000,
        'finviz_precio_min': 1, 'finviz_precio_max': 20,
        'finviz_market_caps': ['Small ($300mln to $2bln)', 'Micro ($50mln to $300mln)', 'Nano (under $50mln)'],
        'float_max': 8.0, 'rvol_min': 0.2, 'rvol_max': 4.0, 'change_max': -7.0, 'inst_max': 15.0,
    },
    {
        'nombre': 'B_float_grande_inst',
        'descripcion': 'David Vepreak -- float grande, RVOL bajo, institucional alto',
        'finviz_cambio_min': None,  # sin filtro de direccion -- perfil B acepta subida o bajada
        'finviz_volumen_min': 300_000,
        'finviz_precio_min': 1, 'finviz_precio_max': 20,
        'finviz_market_caps': ['Small ($300mln to $2bln)', 'Mid ($2bln to $10bln)'],
        'float_min': 15.0, 'rvol_max': 3.0, 'change_min': -8.0, 'change_max': 12.0, 'inst_min': 12.0,
        # ⚠ PERFIL MENOS CONFIABLE DE LOS TRES. Con float grande + RVOL bajo +
        # cambio moderado califica casi cualquier accion mediana en un dia
        # normal (~800/dia sin limite). Se corta a los 5 MAS CERCANOS a la
        # mediana real de David (float 41.9M, inst 14.7%, RVOL 1.2x) en vez de
        # los 5 primeros que salgan -- asi al menos son los mas parecidos a el.
        # Solo 19 avistamientos suyos: no alcanza para un perfil solido todavia.
        'limite_diario': 5,
        'objetivo_cercania': {'float_M': 41.9, 'inst_own': 14.7, 'rvol': 1.2},
    },
    # -- Agregar perfiles nuevos aca, mismo formato --
]


# ══════════════════════════════════════════════════════════════════
#  MAPEO DE FILTRO NEGATIVO (Finviz solo trae 'Up X%' de fabrica en tu
#  codigo actual -- agrego el equivalente 'Down X%' para perfiles rojos)
# ══════════════════════════════════════════════════════════════════

def mapear_cambio_finviz(pct):
    """pct puede ser positivo (busca 'Up'), negativo (busca 'Down'), o None
    (sin filtro de direccion -- usar None explicito, no un numero magico)."""
    if pct is None:
        return None
    if pct <= -20:
        return 'Down 20%'  # Finviz no tiene "Down 30%", el mas fuerte disponible es 20%
    if pct <= -15:
        return 'Down 15%'
    if pct <= -10:
        return 'Down 10%'
    if pct <= -5:
        return 'Down 5%'
    if pct <= 0:
        return None
    if pct >= 20:
        return 'Up 20%'
    if pct >= 15:
        return 'Up 15%'
    if pct >= 10:
        return 'Up 10%'
    return 'Up 5%'


def mapear_volumen_finviz(vol):
    if vol >= 2_000_000:
        return 'Over 2M'
    if vol >= 1_000_000:
        return 'Over 1M'
    if vol >= 500_000:
        return 'Over 500K'
    return 'Over 200K'


def mapear_precio_finviz(pmin, pmax):
    opciones = {
        (1, 5): '$1 to $5', (1, 10): '$1 to $10', (1, 20): '$1 to $20',
        (5, 10): '$5 to $10', (5, 20): '$5 to $20', (10, 20): '$10 to $20',
    }
    return opciones.get((int(pmin), int(pmax)), '$1 to $20')


# (2026-10-21) Se quitó corregir_ticker() y la lista TICKERS_DOBLE_LETRA_REALES:
# la "letra duplicada" era la letra del logo que Finviz pinta delante del
# ticker. app/finviz_screener.py lee el ticker exacto de data-ticker, así
# que ya no hace falta adivinar (y el parche fallaba con tickers nuevos de
# letra doble que no estaban en la lista).


def parsear_change_pct(valor_crudo):
    """
    El cambio% se lee de la tabla Overview cruda. Con app/finviz_screener.py
    viene como texto con signo ('5.23%'). Se deja la heurística para
    fracciones (0.0523) por si acaso: un cambio real filtrado por Finviz
    (ej. 'Up 5%') nunca da |valor|<1.5 si ya está en puntos porcentuales.
    """
    if valor_crudo is None:
        return None
    s = str(valor_crudo).strip()
    if s in ('', '-', 'nan', 'None'):
        return None
    tiene_signo_pct = '%' in s
    s = s.replace('%', '').replace(',', '')
    try:
        v = float(s)
    except ValueError:
        return None
    if tiene_signo_pct:
        return round(v, 2)
    if abs(v) < 1.5:
        return round(v * 100, 2)
    return round(v, 2)


def parsear_numero(valor_crudo):
    if valor_crudo is None:
        return None
    s = str(valor_crudo).strip().replace(',', '')
    if s in ('', '-', 'nan', 'None'):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def cumple_filtro_final(float_M, rvol, change_pct, inst_own, perfil):
    """
    OJO: institucional en blanco (None) se trata como PASA los filtros
    de inst_max -- Finviz casi nunca reporta Inst Own para microcaps,
    el dato en blanco ahi normalmente significa "casi nula", no "desconocida
    y por eso descartar". Float/RVOL/change en blanco SI se tratan como
    fallo (ahi la ausencia de dato es mas sospechosa, no un patron esperado).
    """
    motivos_fallo = []
    if 'float_max' in perfil and (float_M is None or float_M > perfil['float_max']):
        motivos_fallo.append('float_max')
    if 'float_min' in perfil and (float_M is None or float_M < perfil['float_min']):
        motivos_fallo.append('float_min')
    if 'rvol_min' in perfil and (rvol is None or rvol < perfil['rvol_min']):
        motivos_fallo.append('rvol_min')
    if 'rvol_max' in perfil and (rvol is None or rvol > perfil['rvol_max']):
        motivos_fallo.append('rvol_max')
    if 'change_min' in perfil and (change_pct is None or change_pct < perfil['change_min']):
        motivos_fallo.append('change_min')
    if 'change_max' in perfil and (change_pct is None or change_pct > perfil['change_max']):
        motivos_fallo.append('change_max')
    if 'inst_min' in perfil and inst_own is not None and inst_own < perfil['inst_min']:
        motivos_fallo.append('inst_min')
    if 'inst_min' in perfil and inst_own is None:
        motivos_fallo.append('inst_min')  # para perfil B, SI necesitamos saber que es alto -- blanco no sirve
    if 'inst_max' in perfil and inst_own is not None and inst_own > perfil['inst_max']:
        motivos_fallo.append('inst_max')
    # inst_own=None NO cuenta como fallo de inst_max (microcaps rara vez lo reportan)
    return len(motivos_fallo) == 0, motivos_fallo


def crear_tabla_perfil_si_no_existe(db):
    conn = db.conectar(); c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS scanner_perfil_diario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            symbol TEXT NOT NULL,
            perfiles_coincide TEXT,
            ya_operado_por TEXT,
            fecha_clasificacion TEXT,
            UNIQUE(fecha, symbol)
        )
    ''')
    conn.commit(); conn.close()


def buscar_perfil(db, perfil):
    import time
    # finvizfinance dejó de leer el screener tras el rediseño de Finviz
    # (16/10/2026): devolvía 0 resultados sin dar error.
    from finviz_screener import screener

    filtro_cambio = mapear_cambio_finviz(perfil['finviz_cambio_min'])
    filtros_finviz = {
        'Price': mapear_precio_finviz(perfil['finviz_precio_min'], perfil['finviz_precio_max']),
        'Current Volume': mapear_volumen_finviz(perfil['finviz_volumen_min']),
    }
    if filtro_cambio:
        filtros_finviz['Change'] = filtro_cambio

    encontrados_totales = {}
    for market_cap in perfil['finviz_market_caps']:
        filtros_finviz['Market Cap.'] = market_cap
        print(f"    consultando Finviz con filtros: {filtros_finviz}")
        try:
            df = screener('overview', filters_dict=filtros_finviz)
        except Exception as e:
            print(f"    ⚠ Finviz fallo para {market_cap}: {e}")
            time.sleep(3)
            continue
        if df is None or df.empty:
            print(f"    (0 resultados para {market_cap} con esos filtros exactos)")
            time.sleep(3)
            continue
        for _, row in df.iterrows():
            encontrados_totales[row['Ticker']] = row   # ticker exacto (data-ticker)
        time.sleep(2)  # pausa entre consultas para no gatillar el limite de Finviz

    if not encontrados_totales:
        return []

    symbols = list(encontrados_totales.keys())
    print(f"    {len(symbols)} candidatos brutos de Finviz, enriqueciendo con float/rvol/inst...")
    detalles = db.enriquecer_completo(symbols)

    aprobados = []
    conteo_fallos = {}
    for symbol in symbols:
        det = detalles.get(symbol, {})
        row = encontrados_totales[symbol]
        # price/change_pct/volume: de la tabla Overview cruda. Con
        # finvizfinance la columna se llamaba 'Change %'; app/finviz_screener.py
        # la devuelve como 'Change'. Se aceptan las dos por si acaso: pedir el
        # nombre equivocado devuelve None en silencio y NADA pasa los filtros.
        price = parsear_numero(row.get('Price'))
        change_pct = parsear_change_pct(row.get('Change', row.get('Change %')))
        volume = parsear_numero(row.get('Volume'))
        # float/rvol/inst/gap: del enriquecimiento, ahi si funcionan bien.
        float_shares = det.get('float_shares')
        float_M = (float_shares / 1e6) if float_shares else None
        rvol = det.get('rvol')
        gap_pct = det.get('gap_pct')
        inst_own = det.get('inst_own')

        pasa, motivos = cumple_filtro_final(float_M, rvol, change_pct, inst_own, perfil)
        for m in motivos:
            conteo_fallos[m] = conteo_fallos.get(m, 0) + 1
        if pasa:
            aprobados.append({
                'symbol': symbol, 'price': price, 'change_pct': change_pct, 'volume': volume,
                'float_shares': float_shares, 'float_M': float_M,  # float_M para el calculo de cercania
                'rvol': rvol, 'gap_pct': gap_pct, 'inst_own': inst_own,
            })

    if conteo_fallos:
        print(f"    Motivos de rechazo (un candidato puede fallar por mas de uno): {conteo_fallos}")

    # -- Limite diario con ordenamiento por cercania (solo si el perfil lo pide) --
    limite = perfil.get('limite_diario')
    objetivo = perfil.get('objetivo_cercania')
    if limite and len(aprobados) > limite:
        if objetivo:
            def distancia(a):
                """Distancia normalizada a la mediana real del trader: cada
                variable se divide por su propio objetivo, asi float (decenas
                de millones) y RVOL (unidades) pesan parecido en vez de que
                float domine todo por su escala."""
                d = 0.0
                for campo, valor_objetivo in objetivo.items():
                    valor = a.get(campo)
                    if valor is None or valor_objetivo in (None, 0):
                        d += 1.0  # penaliza el dato faltante, sin descartar
                        continue
                    d += abs(valor - valor_objetivo) / abs(valor_objetivo)
                return d
            aprobados.sort(key=distancia)
            print(f"    {len(aprobados)} pasaron el filtro -> recortado a los {limite} MAS CERCANOS "
                  f"al perfil real del trader {objetivo}")
        else:
            print(f"    {len(aprobados)} pasaron el filtro -> recortado a los primeros {limite}")
        aprobados = aprobados[:limite]

    return aprobados


def guardar_resultados(db, hoy, resultados_por_perfil):
    conn = db.conectar(); c = conn.cursor()

    guardados_scanner, guardados_etiqueta = 0, 0
    perfiles_por_symbol = {}

    for nombre_perfil, aprobados in resultados_por_perfil.items():
        for r in aprobados:
            perfiles_por_symbol.setdefault(r['symbol'], []).append(nombre_perfil)
            try:
                c.execute('''
                    INSERT OR IGNORE INTO scanner_results
                    (fecha, symbol, price, change_pct, volume, float_shares, rvol, inst_own)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (hoy, r['symbol'], r['price'], r['change_pct'], r['volume'],
                      r['float_shares'], r['rvol'], r['inst_own']))
                if c.rowcount > 0:
                    guardados_scanner += 1
            except Exception as e:
                print(f"  ✗ Error guardando {r['symbol']} en scanner_results: {e}")

    for symbol, perfiles in perfiles_por_symbol.items():
        try:
            c.execute('''
                INSERT OR REPLACE INTO scanner_perfil_diario
                (fecha, symbol, perfiles_coincide, fecha_clasificacion)
                VALUES (?, ?, ?, ?)
            ''', (hoy, symbol, ','.join(perfiles), datetime.datetime.now().isoformat(timespec='seconds')))
            guardados_etiqueta += 1
        except Exception as e:
            print(f"  ✗ Error etiquetando {symbol}: {e}")

    conn.commit(); conn.close()
    return guardados_scanner, guardados_etiqueta


def main():
    db = Database()
    crear_tabla_perfil_si_no_existe(db)
    hoy = datetime.date.today().isoformat()

    print(f"Buscando tickers para {len(PERFILES)} perfiles ({hoy})...\n")

    resultados_por_perfil = {}
    for perfil in PERFILES:
        print(f"--- {perfil['nombre']} ({perfil['descripcion']}) ---")
        aprobados = buscar_perfil(db, perfil)
        resultados_por_perfil[perfil['nombre']] = aprobados
        print(f"    ✓ {len(aprobados)} tickers cumplen el filtro final de este perfil\n")
        import time
        time.sleep(5)  # pausa entre perfiles completos, mismo motivo

    guardados_scanner, guardados_etiqueta = guardar_resultados(db, hoy, resultados_por_perfil)

    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    for nombre_perfil, aprobados in resultados_por_perfil.items():
        print(f"  {nombre_perfil}: {len(aprobados)} tickers -> {[a['symbol'] for a in aprobados]}")
    print(f"\n✓ {guardados_scanner} filas nuevas en scanner_results (las que ya estaban de hoy se ignoraron).")
    print(f"✓ {guardados_etiqueta} symbols etiquetados en scanner_perfil_diario.")


if __name__ == '__main__':
    main()