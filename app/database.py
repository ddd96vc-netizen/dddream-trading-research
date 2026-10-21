from pathlib import Path
import sqlite3
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os


load_dotenv()

API_KEY = os.getenv('FINNHUB_API_KEY')

class Database:
    def __init__(self, ruta=None):
        # Ruta absoluta a partir de este archivo: antes era 'database/dddream.db'
        # relativa a la carpeta actual, y corriendo desde otra carpeta fallaba
        # o sqlite creaba una base vacía nueva.
        if ruta is None:
            ruta = str(Path(__file__).resolve().parent.parent / 'database' / 'dddream.db')
        self.ruta = ruta
        print(f'Base de Datos en {self.ruta}')
   
    def conectar(self):
        conn = sqlite3.connect(self.ruta)
        return conn

    
    def cargar_mapa_cik(self):
        """Descarga el mapa ticker->CIK de la SEC (una vez, se reutiliza)."""
        import requests
        headers = {'User-Agent': 'DDDreaM Personal Project tucorreo@ejemplo.com'}
        resp = requests.get('https://www.sec.gov/files/company_tickers.json', headers=headers, timeout=15)
        data = resp.json()
        mapa = {}
        for item in data.values():
            mapa[item['ticker'].upper()] = str(item['cik_str']).zfill(10)
        return mapa

    def consultar_alertas_sec(self, symbols, dias_atras=14):
        """
        Consulta SEC EDGAR por filings recientes relevantes (8-K, S-1,
        424B5, S-3...) para una lista de tickers. Guarda alertas nuevas.
        Devuelve dict {symbol: [alertas]}.
        """
        import requests
        from datetime import date, timedelta

        headers = {'User-Agent': 'DDDreaM Personal Project tucorreo@ejemplo.com'}
        cik_map = self.cargar_mapa_cik()
        alertas_relevantes = {'8-K', 'S-1', 'S-1/A', '424B5', '424B4', 'S-3', 'S-3/A'}
        limite = date.today() - timedelta(days=dias_atras)

        conn = self.conectar()
        cursor = conn.cursor()
        resultado = {}

        for symbol in symbols:
            cik = cik_map.get(symbol.upper())
            if not cik:
                continue
            url = f'https://data.sec.gov/submissions/CIK{cik}.json'
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                data = resp.json()
            except Exception:
                continue

            recientes = data.get('filings', {}).get('recent', {})
            forms = recientes.get('form', [])
            fechas = recientes.get('filingDate', [])
            encontradas = []

            for i, form in enumerate(forms):
                if form not in alertas_relevantes:
                    continue
                try:
                    fecha_filing = date.fromisoformat(fechas[i])
                except Exception:
                    continue
                if fecha_filing < limite:
                    continue
                encontradas.append({'form': form, 'fecha': fechas[i]})
                cursor.execute('''
                    INSERT OR IGNORE INTO alertas_sec
                    (symbol, tipo_filing, fecha_filing, fecha_registro)
                    VALUES (?, ?, ?, ?)
                ''', (symbol, form, fechas[i], str(date.today())))

            if encontradas:
                resultado[symbol] = encontradas

        conn.commit()
        conn.close()
        return resultado

    def crear_tabla(self):
        conn = self.conectar()
        cursor = conn.cursor()
        # Nota: las tablas 'tickers', 'daily_data' y 'gaps' (el sistema de
        # histórico diario del prototipo inicial) se archivaron en legacy.py.
        # Si tu BD ya las tenía creadas, siguen ahí sin usarse; no se borran.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scanner_results (
                id INTEGER PRIMARY KEY,
                fecha DATE NOT NULL,
                symbol TEXT NOT NULL,
                price REAL,
                change_pct REAL,
                volume INTEGER,
                float_shares REAL,
                short_float_pct REAL,
                rvol REAL,
                gap_pct REAL,
                atr REAL,
                rsi REAL,
                UNIQUE(fecha, symbol))
            ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alertas_sec (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                tipo_filing TEXT,
                fecha_filing TEXT,
                fecha_registro TEXT,
                UNIQUE(symbol, tipo_filing, fecha_filing)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intraday_data (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                datetime TEXT NOT NULL,
                interval TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                vwap REAL,
                sesion TEXT,
                UNIQUE(symbol, datetime, interval))
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS x_tickers (
                symbol TEXT PRIMARY KEY,
                fecha_agregado TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS x_avistamientos (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                fecha TEXT NOT NULL,
                trader TEXT NOT NULL,
                imagen TEXT,
                nota TEXT,
                fecha_registro TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS noticias (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                fecha TEXT NOT NULL,
                headline TEXT,
                resumen TEXT,
                fuente TEXT,
                url TEXT,
                fecha_registro TEXT,
                UNIQUE(symbol, fecha, headline)
            )
        ''')

        # Migración segura: si x_avistamientos ya existía con el esquema
        # viejo (columna 'direccion'), añadimos imagen/nota sin tocar nada
        # más. No falla si las columnas ya existen.
        for columna in ['imagen', 'nota']:
            try:
                cursor.execute(f'ALTER TABLE x_avistamientos ADD COLUMN {columna} TEXT')
            except Exception:
                pass
                
        # Migración segura: participación institucional (% Inst Own de Finviz),
        # dato que ya se descargaba pero nunca se guardaba.
        try:
            cursor.execute('ALTER TABLE scanner_results ADD COLUMN inst_own REAL')
        except Exception:
            pass
        
        try:
            cursor.execute('ALTER TABLE noticias ADD COLUMN hora TEXT')
        except Exception:
            pass
        try:
            cursor.execute('ALTER TABLE scanner_results ADD COLUMN intradia_intentos INTEGER DEFAULT 0')
        except Exception:
            pass
        conn.commit()
        conn.close()
        print("tabla correctamente creada campeon y tambien daily_data y de gaps creados")

    def obtener_small_caps_finviz(self, cambio_min=5, volumen_min=500000, precio_min=1, precio_max=20,
                                    float_max_millones=None, inst_max_pct=None,
                                    market_cap='Small ($300mln to $2bln)'):
        # market_cap: 'Small' es el universo con el que se validaron las 4
        # estrategias del monitor -- NO cambiarlo aquí o el forward deja de
        # medir lo validado. Deja fuera micro y nano caps (<$300M): ej.
        # 21/10/2026, Small=35 tickers vs bajo $2B=93. Ampliar a
        # '-Small (under $2bln)' es una hipótesis nueva: backtestear aparte.
        from finviz_screener import screener
        from datetime import date

        print(f"Buscando small caps en Finviz...")

        # Mapeo de cambio % a las opciones que acepta Finviz. Antes todo lo
        # menor a 5% se mandaba como 'Up 5%' (el Grupo 3 con cambio_min=2
        # filtraba en realidad con 5%). Finviz sí acepta Up 1%..Up 10%.
        def mapear_cambio(pct):
            for umbral in (20, 15, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1):
                if pct >= umbral:
                    return f'Up {umbral}%'
            return 'Up'

        # Mapeo de volumen a las opciones que acepta Finviz
        def mapear_volumen(vol):
            for umbral, texto in ((20_000_000, 'Over 20M'), (10_000_000, 'Over 10M'),
                                  (5_000_000, 'Over 5M'), (2_000_000, 'Over 2M'),
                                  (1_000_000, 'Over 1M'), (750_000, 'Over 750K'),
                                  (500_000, 'Over 500K'), (400_000, 'Over 400K'),
                                  (300_000, 'Over 300K'), (200_000, 'Over 200K'),
                                  (100_000, 'Over 100K')):
                if vol >= umbral:
                    return texto
            return 'Over 50K'

        # Mapeo de precio a las opciones que acepta Finviz
        def mapear_precio(pmin, pmax):
            opciones = {
                (1, 5):  '$1 to $5',
                (1, 10): '$1 to $10',
                (1, 20): '$1 to $20',
                (5, 10): '$5 to $10',
                (5, 20): '$5 to $20',
                (10, 20):'$10 to $20',
            }
            return opciones.get((int(pmin), int(pmax)), '$1 to $20')

        filtros = {
            'Price':          mapear_precio(precio_min, precio_max),
            'Change':         mapear_cambio(cambio_min),
            'Current Volume': mapear_volumen(volumen_min),
            'Market Cap.':    market_cap,
        }
        print(f"  Filtros: {filtros}")

        try:
            df = screener('overview', filters_dict=filtros)

            if df is None or df.empty:
                print("✗ No se encontraron resultados")
                return []

            print(f"✓ {len(df)} small caps encontradas, obteniendo detalles...")

            # El ticker sale de data-ticker: ya no hace falta el parche de la
            # "letra inicial duplicada" (era la letra del logo de Finviz).
            tickers_encontrados = list(df['Ticker'])

            # Traer float/short/rvol/atr/rsi/gap pidiendo a Finviz SOLO estos
            # tickers. Si Finviz no lo encuentra, yfinance actúa de respaldo.
            detalles = self.enriquecer_completo(tickers_encontrados)

            conn = self.conectar()
            cursor = conn.cursor()
            hoy = date.today()
            tickers = []

            for _, row in df.iterrows():
                symbol = row['Ticker']
                price = float(str(row['Price']).replace(',', '')) if row['Price'] else None
                volume = int(float(str(row['Volume']).replace(',', ''))) if row['Volume'] else None
                
                # Calcular change_pct real desde yfinance (congelado en el momento del scan)
                change_pct = None
                try:
                    hist = yf.Ticker(symbol).history(period='2d')
                    if len(hist) >= 2:
                        close_ayer = hist['Close'].iloc[-2]
                        open_hoy   = hist['Open'].iloc[-1]
                        change_pct = round(((open_hoy - close_ayer) / close_ayer) * 100, 2)
                    elif len(hist) == 1:
                        open_p  = hist['Open'].iloc[-1]
                        close_p = hist['Close'].iloc[-1]
                        change_pct = round(((close_p - open_p) / open_p) * 100, 2)
                except Exception:
                    pass

                # Detalles extra de cada ticker (del lote ya consultado arriba)
                det = detalles.get(symbol, {})
                float_shares = det.get('float_shares')
                short_float_pct = det.get('short_float_pct')
                rvol = det.get('rvol')
                gap_pct = det.get('gap_pct')
                atr = det.get('atr')
                rsi = det.get('rsi')
                inst_own = det.get('inst_own')

                if det:
                    print(f"  ✓ {symbol} - Float: {float_shares} | Short: {short_float_pct}% | RVOL: {rvol} | Gap: {gap_pct}%")
                else:
                    print(f"  ⚠ {symbol} - sin datos extra en el screener de Finviz")

                # Guardar en scanner_results
                # Filtro opcional de float/institucional (perfil de traders de X, ajustable)
                if float_max_millones is not None and float_shares is not None:
                    if float_shares / 1e6 > float_max_millones:
                        continue
                if inst_max_pct is not None and inst_own is not None:
                    if inst_own > inst_max_pct:
                        continue

                # Guardar en scanner_results
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO scanner_results
                        (fecha, symbol, price, change_pct, volume, float_shares, short_float_pct, rvol, gap_pct, atr, rsi, inst_own)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (hoy, symbol, price, change_pct, volume, float_shares, short_float_pct, rvol, gap_pct, atr, rsi, inst_own))
                except Exception as e:
                    print(f"  ✗ Error guardando {symbol}: {e}")

                tickers.append(symbol)

            conn.commit()
            conn.close()
            print(f"\n✓ {len(tickers)} tickers guardados en scanner_results")
            return tickers

        except Exception as e:
            print(f"✗ Error en Finviz: {e}")
            return []   
        
    def descargar_intradia_con_vwap(self, symbol, periodo='60d'):
        import yfinance as yf
        import pandas as pd

        conn = self.conectar()
        cursor = conn.cursor()
        guardados = 0

        for intervalo in ['1m', '5m']:
            print(f"  Descargando {symbol} - {intervalo} ({periodo}) [con premarket]...")

            try:
                ticker = yf.Ticker(symbol)
                periodo_real = '8d' if intervalo == '1m' else periodo
                # prepost=True trae premarket (4:00) y after-hours (hasta 20:00)
                datos = ticker.history(period=periodo_real, interval=intervalo, prepost=True)

                if datos.empty:
                    print(f"  ✗ Sin datos para {symbol} {intervalo}")
                    continue

                # Asegurar timezone US/Eastern para clasificar sesión por hora ET
                if datos.index.tz is None:
                    datos.index = datos.index.tz_localize('UTC').tz_convert('America/New_York')
                else:
                    datos.index = datos.index.tz_convert('America/New_York')

                # Clasificar cada vela: pre (4:00-9:30), regular (9:30-16:00), after (16:00-20:00)
                def clasificar(ts):
                    minutos = ts.hour * 60 + ts.minute
                    if 240 <= minutos < 570:       # 04:00 - 09:30
                        return 'pre'
                    elif 570 <= minutos < 960:     # 09:30 - 16:00
                        return 'regular'
                    else:                          # 16:00 - 20:00
                        return 'after'

                datos['sesion'] = [clasificar(ts) for ts in datos.index]
                datos['fecha'] = datos.index.date
                datos['precio_tipico'] = (datos['High'] + datos['Low'] + datos['Close']) / 3

                # VWAP LIMPIO: solo se calcula sobre la sesión regular (como TradingView)
                datos['vwap'] = None
                solo_regular = datos[datos['sesion'] == 'regular'].copy()
                if not solo_regular.empty:
                    vwap_reg = solo_regular.groupby('fecha').apply(
                        lambda g: (g['precio_tipico'] * g['Volume']).cumsum() / g['Volume'].cumsum(),
                        include_groups=False
                    ).reset_index(level=0, drop=True)
                    datos.loc[solo_regular.index, 'vwap'] = vwap_reg

                for dt, row in datos.iterrows():
                    try:
                        vwap_val = row['vwap']
                        vwap_final = float(vwap_val) if vwap_val is not None and str(vwap_val) != 'nan' else None
                        cursor.execute('''
                            INSERT OR IGNORE INTO intraday_data
                            (symbol, datetime, interval, open, high, low, close, volume, vwap, sesion)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            symbol,
                            str(dt),
                            intervalo,
                            float(row['Open']),
                            float(row['High']),
                            float(row['Low']),
                            float(row['Close']),
                            int(row['Volume']),
                            vwap_final,
                            row['sesion']
                        ))
                        guardados += 1
                    except Exception:
                        continue

                print(f"  ✓ {len(datos)} velas guardadas para {symbol} {intervalo}")

            except Exception as e:
                print(f"  ✗ Error {symbol} {intervalo}: {e}")

        conn.commit()
        conn.close()
        print(f"✓ Total guardadas: {guardados} filas para {symbol}")

    def obtener_intradia(self, symbol, intervalo='5m'):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT datetime, open, high, low, close, volume, vwap, sesion
            FROM intraday_data
            WHERE symbol = ? AND interval = ?
            ORDER BY datetime
        ''', (symbol, intervalo))
        resultados = cursor.fetchall()
        conn.close()
        return resultados

    def obtener_intradia_en_vivo(self, symbol, intervalo='1m'):
        """
        Trae datos intradía FRESCOS de yfinance SIN guardar en la BD.
        Solo para visualizar en vivo. No toca scanner_results ni intraday_data.
        Devuelve la misma estructura que obtener_intradia:
        lista de tuplas (datetime, open, high, low, close, volume, vwap)
        """
        import yfinance as yf

        # Límites de yfinance gratis: 1m=8d, 5m=60d. Para "en vivo" usamos poco rango.
        periodo = '5d' if intervalo == '1m' else '10d'

        try:
            ticker = yf.Ticker(symbol)
            datos = ticker.history(period=periodo, interval=intervalo)

            if datos.empty:
                return []

            # VWAP por día (se resetea cada sesión)
            datos['fecha'] = datos.index.date
            datos['precio_tipico'] = (datos['High'] + datos['Low'] + datos['Close']) / 3
            datos['vwap'] = datos.groupby('fecha').apply(
                lambda g: (g['precio_tipico'] * g['Volume']).cumsum() / g['Volume'].cumsum(),
                include_groups=False
            ).reset_index(level=0, drop=True)

            resultados = []
            for dt, row in datos.iterrows():
                vwap_val = float(row['vwap']) if not str(row['vwap']) == 'nan' else None
                resultados.append((
                    str(dt),
                    float(row['Open']),
                    float(row['High']),
                    float(row['Low']),
                    float(row['Close']),
                    int(row['Volume']),
                    vwap_val
                ))
            return resultados

        except Exception as e:
            print(f"✗ Error obteniendo datos en vivo de {symbol}: {e}")
            return []

    def obtener_tickers_seguimiento(self):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT symbol, price, change_pct, volume, float_shares,
                   short_float_pct, rvol, gap_pct, rsi, fecha
            FROM scanner_results sr
            WHERE fecha = (SELECT MAX(fecha) FROM scanner_results WHERE symbol = sr.symbol)
            ORDER BY fecha DESC, symbol ASC
        ''')
        resultados = cursor.fetchall()
        conn.close()
        return resultados

    def obtener_rango_fechas_intradia(self, symbol):
        """
        Devuelve (fecha_desde, fecha_hasta) de los datos intradía guardados
        para un símbolo, mirando la tabla intraday_data.
        Devuelve (None, None) si no hay datos.
        """
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MIN(datetime), MAX(datetime)
            FROM intraday_data
            WHERE symbol = ?
        ''', (symbol,))
        fila = cursor.fetchone()
        conn.close()
        if fila and fila[0] and fila[1]:
            # datetime viene como 'YYYY-MM-DD HH:MM:SS...' -> cortamos a fecha
            return fila[0][:10], fila[1][:10]
        return None, None

    def enriquecer_desde_finviz_screener(self, symbols, filtros_market_cap=None):
        """
        Trae float, short float, RVOL, ATR, RSI, gap, precio, volumen y cambio %
        para una LISTA de símbolos en pasadas por el screener de Finviz
        (vistas Ownership + Technical). El quote individual de Finviz está roto;
        esta vía SÍ funciona.
        Ahora se piden a Finviz SOLO estos símbolos (parámetro t= del screener),
        así que cubre cualquier market cap, nano caps incluidas, y es mucho más
        rápido que bajarse rangos enteros de market cap para buscarlos ahí.
        filtros_market_cap: ya no se usa; se deja para no romper llamadas viejas.
        Devuelve dict: {symbol: {price, change_pct, volume, float_shares,
                                  short_float_pct, rvol, atr, rsi, gap_pct}}
        """
        from finviz_screener import screener

        def limpiar(val):
            if val is None or val == '-' or str(val).lower() == 'nan':
                return None
            s = str(val).replace('%', '').replace(',', '').strip()
            try:
                if s.endswith('B'):
                    return float(s[:-1]) * 1e9
                if s.endswith('M'):
                    return float(s[:-1]) * 1e6
                if s.endswith('K'):
                    return float(s[:-1]) * 1e3
                return float(s)
            except Exception:
                return None

        resultado = {}
        pendientes = set(s.upper().strip() for s in symbols)
        if not pendientes:
            return resultado

        try:
            df_own = screener('ownership', tickers=pendientes)
        except Exception as e:
            print(f"  (aviso: Ownership falló: {e})")
            df_own = None

        try:
            df_tec = screener('technical', tickers=pendientes)
        except Exception as e:
            print(f"  (aviso: Technical falló: {e})")
            df_tec = None

        own = {row['Ticker']: row for _, row in df_own.iterrows()} if df_own is not None and not df_own.empty else {}
        tec = {row['Ticker']: row for _, row in df_tec.iterrows()} if df_tec is not None and not df_tec.empty else {}

        for sym in pendientes:
            o_row = own.get(sym)
            if o_row is None:
                continue

            t_row = tec.get(sym)

            vol = limpiar(o_row.get('Volume'))
            avg_vol = limpiar(o_row.get('Avg Volume'))
            rvol = round(vol / avg_vol, 2) if (vol and avg_vol and avg_vol > 0) else None

            # El lector nuevo da los % ya en porcentaje ('10.69%' -> 10.69),
            # no en fracción como finvizfinance: ya NO se multiplica por 100.
            cambio = limpiar(o_row.get('Change'))
            gap = limpiar(t_row.get('Gap')) if t_row is not None else None
            inst = limpiar(o_row.get('Inst Own'))

            resultado[sym] = {
                'price': limpiar(o_row.get('Price')),
                'change_pct': round(cambio, 2) if cambio is not None else None,
                'volume': int(vol) if vol else None,
                'float_shares': limpiar(o_row.get('Float')),
                'short_float_pct': limpiar(o_row.get('Short Float')),
                'rvol': rvol,
                'atr': limpiar(t_row.get('ATR')) if t_row is not None else None,
                'rsi': limpiar(t_row.get('RSI')) if t_row is not None else None,
                'gap_pct': round(gap, 2) if gap is not None else None,
                'inst_own': round(inst, 1) if inst is not None else None,
            }

        if resultado:
            print(f"  ✓ {len(resultado)} encontrados en Finviz")
        faltan = pendientes - set(resultado)
        if faltan:
            print(f"  ⚠ {len(faltan)} símbolos no aparecieron en Finviz: {sorted(faltan)}")

        return resultado

    def enriquecer_desde_yfinance(self, symbols):
        """
        Respaldo cuando Finviz no encuentra el ticker en ningún rango de
        market cap. Usa yfinance .info — no da ATR/RSI/gap, pero sí cubre
        float, short float, RVOL, precio y volumen. Gratis, sin scraping.
        Devuelve dict con la misma forma que enriquecer_desde_finviz_screener.
        """
        import yfinance as yf

        resultado = {}
        for sym in set(s.upper().strip() for s in symbols):
            try:
                info = yf.Ticker(sym).info
                if not info or info.get('regularMarketPrice') is None:
                    continue

                float_shares = info.get('floatShares')
                short_pct_frac = info.get('shortPercentOfFloat')  # fracción, ej 0.05 = 5%
                inst_pct_frac = info.get('heldPercentInstitutions')  # fracción, ej 0.20 = 20%
                volume = info.get('volume') or info.get('regularMarketVolume')
                avg_vol = info.get('averageVolume')
                rvol = round(volume / avg_vol, 2) if (volume and avg_vol and avg_vol > 0) else None
                price = info.get('regularMarketPrice') or info.get('currentPrice')

                resultado[sym] = {
                    'price': price,
                    'change_pct': None,  # se calcula aparte con el método histórico ya existente
                    'volume': volume,
                    'float_shares': float_shares,
                    'short_float_pct': round(short_pct_frac * 100, 2) if short_pct_frac is not None else None,
                    'rvol': rvol,
                    'atr': None,
                    'rsi': None,
                    'gap_pct': None,
                    'inst_own': round(inst_pct_frac * 100, 1) if inst_pct_frac is not None else None,
                }
            except Exception as e:
                print(f"  ⚠ yfinance no pudo con {sym}: {e}")
                continue

        if resultado:
            print(f"  ✓ {len(resultado)} completados vía yfinance (respaldo)")

        return resultado

    def enriquecer_completo(self, symbols, filtros_market_cap=None):
        """
        Orquesta la búsqueda de datos: primero Finviz (varios rangos de
        market cap), y para lo que quede sin encontrar, yfinance como
        segundo intento. Es el método que deben usar todas las rutas de
        añadir/reparar tickers.
        """
        resultado = self.enriquecer_desde_finviz_screener(symbols, filtros_market_cap=filtros_market_cap)

        pendientes = [s for s in symbols if s.upper().strip() not in resultado]
        if pendientes:
            print(f"  → Probando yfinance como respaldo para {len(pendientes)} símbolos...")
            respaldo = self.enriquecer_desde_yfinance(pendientes)
            resultado.update(respaldo)

        return resultado

    def agregar_ticker_manual(self, symbol, datos_finviz=None, descargar_intradia=True):
        """
        Añade un ticker a scanner_results + intradía.
        datos_finviz: dict opcional {symbol: {...}} ya pre-consultado (para
        lotes, así solo se golpea Finviz UNA vez por lote, no por ticker).
        Si no se pasa, hace la consulta él mismo (más lento, un símbolo).
        """
        from datetime import date

        symbol = symbol.upper().strip()
        print(f"Añadiendo manualmente {symbol}...")

        info = None
        if datos_finviz and symbol in datos_finviz:
            info = datos_finviz[symbol]
            print(f"  ✓ Datos obtenidos para {symbol}")
        else:
            try:
                lote = self.enriquecer_completo([symbol])
                info = lote.get(symbol)
                if info:
                    print(f"  ✓ Datos obtenidos para {symbol}")
                else:
                    print(f"  ⚠ {symbol} no se encontró ni en Finviz ni en yfinance")
            except Exception as e:
                print(f"  ⚠ No se pudieron obtener datos para {symbol}: {e}")

        price = change_pct = volume = float_shares = None
        short_float_pct = rvol = gap_pct = atr = rsi = inst_own = None
        if info:
            price = info.get('price')
            change_pct = info.get('change_pct')
            volume = info.get('volume')
            float_shares = info.get('float_shares')
            short_float_pct = info.get('short_float_pct')
            rvol = info.get('rvol')
            atr = info.get('atr')
            rsi = info.get('rsi')
            gap_pct = info.get('gap_pct')
            inst_own = info.get('inst_own')
        else:
            print(f"  (se añadirá igual, solo sin esas métricas)")

        # Respaldo directo con yfinance: cambio % real (congelado en el
        # momento) y precio de cierre, por si Finviz ni el respaldo de
        # .info lo trajeron -- mismo método que ya usa el scanner normal.
        if change_pct is None or price is None:
            try:
                hist = yf.Ticker(symbol).history(period='2d')
                if len(hist) >= 2:
                    close_ayer = hist['Close'].iloc[-2]
                    open_hoy = hist['Open'].iloc[-1]
                    if change_pct is None:
                        change_pct = round(((open_hoy - close_ayer) / close_ayer) * 100, 2)
                    if price is None:
                        price = round(hist['Close'].iloc[-1], 4)
                elif len(hist) == 1:
                    open_p = hist['Open'].iloc[-1]
                    close_p = hist['Close'].iloc[-1]
                    if change_pct is None:
                        change_pct = round(((close_p - open_p) / open_p) * 100, 2)
                    if price is None:
                        price = round(close_p, 4)
            except Exception as e:
                print(f"  ⚠ Respaldo de cambio%/precio con yfinance falló para {symbol}: {e}")

        conn = self.conectar()
        cursor = conn.cursor()
        hoy = date.today()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO scanner_results
                (fecha, symbol, price, change_pct, volume, float_shares, short_float_pct, rvol, gap_pct, atr, rsi, inst_own)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (hoy, symbol, price, change_pct, volume, float_shares, short_float_pct, rvol, gap_pct, atr, rsi, inst_own))
            conn.commit()
        except Exception as e:
            print(f"✗ Error guardando {symbol}: {e}")
        conn.close()

        # Siempre actualizamos su intradía, exista ya o sea nuevo
        if descargar_intradia:
            self.descargar_intradia_con_vwap(symbol)
        return symbol

    def eliminar_ticker(self, symbol):
        conn = self.conectar()
        cursor = conn.cursor()
    
        # Primero obtenemos el ticker_id si existe en la tabla tickers
        cursor.execute('SELECT id FROM tickers WHERE symbol = ?', (symbol,))
        fila = cursor.fetchone()
        ticker_id = fila[0] if fila else None
    
        # Borrar de scanner_results
        cursor.execute('DELETE FROM scanner_results WHERE symbol = ?', (symbol,))
    
        # Borrar de intraday_data
        cursor.execute('DELETE FROM intraday_data WHERE symbol = ?', (symbol,))
    
        # Si tenía ticker_id, borrar de daily_data, gaps y tickers
        if ticker_id is not None:
            cursor.execute('DELETE FROM daily_data WHERE ticker_id = ?', (ticker_id,))
            cursor.execute('DELETE FROM gaps WHERE ticker_id = ?', (ticker_id,))
            cursor.execute('DELETE FROM tickers WHERE id = ?', (ticker_id,))
    
        conn.commit()
        conn.close()
        print(f"✓ {symbol} eliminado completamente de la BD")

    def actualizar_metricas_manual(self, symbol, float_shares=None, short_float_pct=None, rvol=None, inst_own=None):
        """
        Permite fijar float/short float/RVOL/institucional a mano para un
        ticker, como último recurso cuando ni Finviz ni yfinance los tienen.
        Solo actualiza los campos que se pasen (no None); el resto no se toca.
        float_shares se espera ya en unidades absolutas (no millones).
        """
        symbol = symbol.upper().strip()
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE scanner_results
            SET float_shares = COALESCE(?, float_shares),
                short_float_pct = COALESCE(?, short_float_pct),
                rvol = COALESCE(?, rvol),
                inst_own = COALESCE(?, inst_own)
            WHERE symbol = ?
        ''', (float_shares, short_float_pct, rvol, inst_own, symbol))
        conn.commit()
        filas = cursor.rowcount
        conn.close()
        return filas > 0

    def migrar_columna_sesion(self):
        conn = self.conectar()
        cursor = conn.cursor()
        try:
            cursor.execute('ALTER TABLE intraday_data ADD COLUMN sesion TEXT')
            conn.commit()
            print("✓ Columna 'sesion' añadida a intraday_data")
        except Exception as e:
            print(f"  (columna sesion ya existe o error: {e})")
        conn.close()

    def detectar_gap_and_go(self, symbol, intervalo='5m'):
        """
        Detecta Gap & Go por día: primera vela de sesión regular que CIERRA
        por encima del PM High. Mide resultado a 15, 30 y 60 min tras la rotura.
        Devuelve lista de dicts, uno por día con señal.
        """
        from collections import defaultdict
        from datetime import datetime as dt_parse

        datos = self.obtener_intradia(symbol, intervalo)
        if not datos:
            return []

        vol_rvol = self.calcular_volumen_rvol_por_dia(symbol, intervalo)
        # Agrupar velas por día
        por_dia = defaultdict(list)
        for d in datos:
            fecha = d[0][:10]
            por_dia[fecha].append(d)

        # minutos por vela según intervalo (para calcular ventanas)
        paso = 1 if intervalo == '1m' else 5
        velas_15 = max(1, 15 // paso)
        velas_30 = max(1, 30 // paso)
        velas_60 = max(1, 60 // paso)

        resultados = []

        for fecha, velas in por_dia.items():
            # sesion está en índice 7; si no existe, asumimos regular
            pre = [v for v in velas if (len(v) > 7 and v[7] == 'pre')]
            regular = [v for v in velas if (len(v) <= 7 or v[7] == 'regular')]

            if not pre or not regular:
                continue  # necesitamos premarket Y sesión regular

            pm_high = max(v[2] for v in pre)  # high del premarket

            # Buscar primera vela regular que CIERRA por encima del PM High
            rotura_idx = None
            for i, v in enumerate(regular):
                if v[4] > pm_high:  # close > pm_high
                    rotura_idx = i
                    break

            if rotura_idx is None:
                # Hubo premarket pero nunca rompió → señal fallida/no dada
                resultados.append({
                    'fecha': fecha,
                    'pm_high': round(pm_high, 4),
                    'rotura': False,
                    'hora_rotura': None,
                    'precio_rotura': None,
                    'mov_15': None, 'mov_30': None, 'mov_60': None,
                    'max_dia_post': None,
                    'rvol': vol_rvol.get(fecha, {}).get('rvol'),
                })
                continue

            v_rotura = regular[rotura_idx]
            precio_rotura = v_rotura[4]
            hora_rotura = v_rotura[0][11:16]  # HH:MM

            def mov_pct(n_velas):
                fin = min(rotura_idx + n_velas, len(regular) - 1)
                precio_fin = regular[fin][4]
                return round(((precio_fin - precio_rotura) / precio_rotura) * 100, 2)

            # Máximo alcanzado tras la rotura (hasta fin de sesión)
            highs_post = [regular[j][2] for j in range(rotura_idx, len(regular))]
            max_post = max(highs_post) if highs_post else precio_rotura
            max_post_pct = round(((max_post - precio_rotura) / precio_rotura) * 100, 2)

            resultados.append({
                'fecha': fecha,
                'pm_high': round(pm_high, 4),
                'rotura': True,
                'hora_rotura': hora_rotura,
                'precio_rotura': round(precio_rotura, 4),
                'mov_15': mov_pct(velas_15),
                'mov_30': mov_pct(velas_30),
                'mov_60': mov_pct(velas_60),
                'max_dia_post': max_post_pct,
                'rvol': vol_rvol.get(fecha, {}).get('rvol'),
            })

        return resultados    
    
    def detectar_vwap_bounce(self, symbol, intervalo='5m'):
        """
        Detecta rebotes en VWAP: vela cuyo LOW toca/cruza el VWAP pero
        CIERRA por encima. Mide resultado a 15/30/60 min tras cada rebote.
        Solo en sesión regular (el VWAP solo existe ahí).
        """
        from collections import defaultdict

        datos = self.obtener_intradia(symbol, intervalo)
        if not datos:
            return []

        por_dia = defaultdict(list)
        for d in datos:
            por_dia[d[0][:10]].append(d)

        paso = 1 if intervalo == '1m' else 5
        v15 = max(1, 15 // paso)
        v30 = max(1, 30 // paso)
        v60 = max(1, 60 // paso)

        resultados = []

        for fecha, velas in por_dia.items():
            # Solo sesión regular y con VWAP válido
            regular = [v for v in velas
                       if (len(v) <= 7 or v[7] == 'regular') and v[6] is not None]
            if len(regular) < 3:
                continue

            rebotes_dia = []
            for i, v in enumerate(regular):
                low   = v[3]
                close = v[4]
                vwap  = v[6]
                if vwap is None:
                    continue
                # Low toca o cruza VWAP, pero cierra por encima = rebote
                if low <= vwap and close > vwap:
                    precio_reb = close
                    hora = v[0][11:16]

                    def mov(n):
                        fin = min(i + n, len(regular) - 1)
                        pf = regular[fin][4]
                        return round(((pf - precio_reb) / precio_reb) * 100, 2)

                    rebotes_dia.append({
                        'hora': hora,
                        'precio': round(precio_reb, 4),
                        'vwap': round(vwap, 4),
                        'mov_15': mov(v15),
                        'mov_30': mov(v30),
                        'mov_60': mov(v60),
                    })

            if rebotes_dia:
                # Promedios del día
                n = len(rebotes_dia)
                resultados.append({
                    'fecha': fecha,
                    'n_rebotes': n,
                    'rebotes': rebotes_dia,
                    'prom_15': round(sum(r['mov_15'] for r in rebotes_dia) / n, 2),
                    'prom_30': round(sum(r['mov_30'] for r in rebotes_dia) / n, 2),
                    'prom_60': round(sum(r['mov_60'] for r in rebotes_dia) / n, 2),
                })

        return resultados
    
    def detectar_reciclaje(self, symbol, intervalo='5m'):
        """
        Cuenta micro-impulsos por día: subida de +2% o más en 2-3 velas.
        Más micro-impulsos = más oportunidades de reciclaje.
        Incluye premarket y regular.
        """
        from collections import defaultdict

        datos = self.obtener_intradia(symbol, intervalo)
        if not datos:
            return []

        por_dia = defaultdict(list)
        for d in datos:
            por_dia[d[0][:10]].append(d)

        UMBRAL = 1.0       # % mínimo de subida
        VENTANA = 2        # en 2-3 velas

        resultados = []

        for fecha, velas in por_dia.items():
            # Excluir after-hours para que no ensucie (pre + regular)
            activas = [v for v in velas
                       if (len(v) <= 7 or v[7] in ('pre', 'regular'))]
            if len(activas) < VENTANA:
                continue

            impulsos = []
            i = 0
            while i < len(activas) - 1:
                base = activas[i][4]  # close de partida
                mejor_subida = 0
                fin_idx = i
                # Mirar hasta VENTANA velas adelante
                for j in range(i + 1, min(i + VENTANA + 1, len(activas))):
                    alto = activas[j][2]  # high
                    subida = ((alto - base) / base) * 100
                    if subida > mejor_subida:
                        mejor_subida = subida
                        fin_idx = j
                if mejor_subida >= UMBRAL:
                    impulsos.append({
                        'hora': activas[i][0][11:16],
                        'subida': round(mejor_subida, 2),
                    })
                    i = fin_idx  # saltar al final del impulso para no recontar
                else:
                    i += 1

            if impulsos:
                n = len(impulsos)
                resultados.append({
                    'fecha': fecha,
                    'n_impulsos': n,
                    'impulsos': impulsos,
                    'subida_max': round(max(im['subida'] for im in impulsos), 2),
                    'subida_prom': round(sum(im['subida'] for im in impulsos) / n, 2),
                })

        return resultados

    def calcular_volumen_rvol_por_dia(self, symbol, intervalo='5m'):
        """
        Calcula para cada día: volumen total (pre+regular) y RVOL acumulativo
        (volumen del día ÷ promedio de volumen de TODOS los días previos).
        Devuelve dict: {fecha: {'volumen': X, 'rvol': Y}}
        """
        from collections import defaultdict

        datos = self.obtener_intradia(symbol, intervalo)
        if not datos:
            return {}

        # Sumar volumen por día (pre + regular, excluye after-hours)
        vol_por_dia = defaultdict(int)
        for d in datos:
            sesion = d[7] if len(d) > 7 and d[7] else 'regular'
            if sesion in ('pre', 'regular'):
                vol_por_dia[d[0][:10]] += (d[5] or 0)

        # Ordenar días cronológicamente
        dias_ord = sorted(vol_por_dia.keys())

        resultado = {}
        acumulado = []  # volúmenes de días previos
        for dia in dias_ord:
            vol = vol_por_dia[dia]
            if acumulado:
                promedio = sum(acumulado) / len(acumulado)
                rvol = round(vol / promedio, 2) if promedio > 0 else None
            else:
                rvol = None  # primer día no tiene previos
            resultado[dia] = {'volumen': vol, 'rvol': rvol}
            acumulado.append(vol)

        return resultado
    
    def calcular_rvol_accionable_por_dia(self, symbol, intervalo='5m'):
        """
        Calcula dos RVOL accionables por día (datos conocidos al operar):
        - rvol_pre: volumen premarket del día ÷ promedio premarket de días previos
        - rvol_30: volumen primera media hora (9:30-10:00) ÷ promedio previo
        Devuelve dict: {fecha: {'rvol_pre': X, 'rvol_30': Y}}
        """
        from collections import defaultdict

        datos = self.obtener_intradia(symbol, intervalo)
        if not datos:
            return {}

        # Volumen premarket y primera media hora por día
        vol_pre = defaultdict(int)
        vol_30 = defaultdict(int)

        for d in datos:
            fecha = d[0][:10]
            hora_min = d[0][11:16]  # 'HH:MM'
            sesion = d[7] if len(d) > 7 and d[7] else 'regular'
            vol = d[5] or 0

            if sesion == 'pre':
                vol_pre[fecha] += vol
            elif sesion == 'regular' and '09:30' <= hora_min < '10:00':
                vol_30[fecha] += vol

        # Todos los días (union de los que tienen pre o regular)
        todos_dias = sorted(set(list(vol_pre.keys()) + list(vol_30.keys())))

        resultado = {}
        acum_pre = []
        acum_30 = []
        for dia in todos_dias:
            vp = vol_pre.get(dia, 0)
            v30 = vol_30.get(dia, 0)

            rvol_pre = round(vp / (sum(acum_pre)/len(acum_pre)), 2) if acum_pre and sum(acum_pre) > 0 else None
            rvol_30 = round(v30 / (sum(acum_30)/len(acum_30)), 2) if acum_30 and sum(acum_30) > 0 else None

            resultado[dia] = {'rvol_pre': rvol_pre, 'rvol_30': rvol_30}

            if vp > 0:
                acum_pre.append(vp)
            if v30 > 0:
                acum_30.append(v30)

        return resultado

    def analisis_agregado(self, setup='gapgo', intervalo='5m'):
        """
        Recorre TODOS los tickers en seguimiento, detecta el setup indicado
        en cada uno, y junta todos los resultados en una sola lista.
        Añade rvol_30 (accionable) y premarket_vivo (sí/no) a cada caso.
        setup: 'gapgo' | 'vwap' | 'reciclaje'
        """
        tickers = self.obtener_tickers_seguimiento()
        simbolos = [t[0] for t in tickers]

        agregado = []

        for symbol in simbolos:
            # Métricas accionables por día de este ticker
            rvol_acc = self.calcular_rvol_accionable_por_dia(symbol, intervalo)

            # Detectar premarket vivo por día (volumen pre > 0)
            from collections import defaultdict
            datos = self.obtener_intradia(symbol, intervalo)
            vol_pre = defaultdict(int)
            for d in datos:
                if len(d) > 7 and d[7] == 'pre':
                    vol_pre[d[0][:10]] += (d[5] or 0)

            def enriquecer(fecha):
                acc = rvol_acc.get(fecha, {})
                return {
                    'symbol': symbol,
                    'rvol_30': acc.get('rvol_30'),
                }

            if setup == 'gapgo':
                res = self.detectar_gap_and_go(symbol, intervalo)
                for r in res:
                    if r['rotura']:
                        fila = enriquecer(r['fecha'])
                        fila.update({
                            'fecha': r['fecha'],
                            'mov_15': r['mov_15'],
                            'mov_30': r['mov_30'],
                            'mov_60': r['mov_60'],
                            'max_post': r['max_dia_post'],
                        })
                        agregado.append(fila)

            elif setup == 'vwap':
                res = self.detectar_vwap_bounce(symbol, intervalo)
                for r in res:
                    fila = enriquecer(r['fecha'])
                    fila.update({
                        'fecha': r['fecha'],
                        'mov_15': r['prom_15'],
                        'mov_30': r['prom_30'],
                        'mov_60': r['prom_60'],
                        'max_post': None,
                        'n_eventos': r['n_rebotes'],
                    })
                    agregado.append(fila)

            elif setup == 'reciclaje':
                res = self.detectar_reciclaje(symbol, intervalo)
                for r in res:
                    fila = enriquecer(r['fecha'])
                    fila.update({
                        'fecha': r['fecha'],
                        'mov_15': None,
                        'mov_30': None,
                        'mov_60': None,
                        'max_post': r['subida_max'],
                        'n_eventos': r['n_impulsos'],
                        'subida_prom': r['subida_prom'],
                    })
                    agregado.append(fila)

        return agregado
    
    def medir_r_gap_and_go(self, symbol, intervalo='5m', stop_pct=3.0, target_pct=6.0):
        """
        Para cada Gap & Go (rotura PM High), simula un trade:
        - Entrada: precio de rotura
        - Stop: entrada * (1 - stop_pct/100)
        - Target: entrada * (1 + target_pct/100)
        - Resultado: lo que toque primero (si una vela toca ambos, asume STOP).
        Devuelve lista de casos con su resultado en R.
        """
        from collections import defaultdict

        

        datos = self.obtener_intradia(symbol, intervalo)
        if not datos:
            return []

        rvol_acc = self.calcular_rvol_accionable_por_dia(symbol, intervalo)

        por_dia = defaultdict(list)
        for d in datos:
            por_dia[d[0][:10]].append(d)

        resultados = []

        for fecha, velas in por_dia.items():
            pre = [v for v in velas if len(v) > 7 and v[7] == 'pre']
            regular = [v for v in velas if len(v) <= 7 or v[7] == 'regular']
            if not pre or not regular:
                continue

            pm_high = max(v[2] for v in pre)

            # Buscar rotura: primera vela regular que CIERRA sobre PM High
            rotura_idx = None
            for i, v in enumerate(regular):
                if v[4] > pm_high:
                    rotura_idx = i
                    break
            if rotura_idx is None:
                continue

            entrada = regular[rotura_idx][4]
            hora_rotura = regular[rotura_idx][0][11:16]
            stop = entrada * (1 - stop_pct / 100)
            target = entrada * (1 + target_pct / 100)

            # Recorrer velas DESPUÉS de la rotura hasta que toque stop o target
            resultado_r = None
            hora_salida = None
            for j in range(rotura_idx + 1, len(regular)):
                v = regular[j]
                low = v[3]
                high = v[2]
                toca_stop = low <= stop
                toca_target = high >= target
                if toca_stop and toca_target:
                    resultado_r = -1.0   # vela ambigua -> asume stop (conservador)
                    hora_salida = v[0][11:16]
                    break
                elif toca_stop:
                    resultado_r = -1.0
                    hora_salida = v[0][11:16]
                    break
                elif toca_target:
                    resultado_r = round(target_pct / stop_pct, 2)  # +R según ratio
                    hora_salida = v[0][11:16]
                    break

            # Si no tocó ninguno, cerró la sesión: resultado = movimiento final en R
            if resultado_r is None:
                cierre = regular[-1][4]
                mov_pct = ((cierre - entrada) / entrada) * 100
                resultado_r = round(mov_pct / stop_pct, 2)  # en múltiplos de R
                hora_salida = 'cierre'

            resultados.append({
                'fecha': fecha,
                'entrada': round(entrada, 4),
                'stop': round(stop, 4),
                'target': round(target, 4),
                'resultado_r': resultado_r,
                'hora_rotura': hora_rotura,
                'hora_salida': hora_salida,
                'rvol_30': rvol_acc.get(fecha, {}).get('rvol_30'),
            })

        return resultados

    def r_agregado_gapgo(self, intervalo='5m', stop_pct=3.0, target_pct=6.0, solo_primera_hora=False):
        """
        Mide R en Gap & Go para TODOS los tickers en seguimiento.
        Junta todos los trades en una lista, con su RVOL 30min para segmentar.
        solo_primera_hora: si True, descarta roturas fuera de 9:30-10:00
        (el filtro de hora que se validó como clave del edge).
        """
        tickers = self.obtener_tickers_seguimiento()
        simbolos = [t[0] for t in tickers]

        todos = []
        for symbol in simbolos:
            trades = self.medir_r_gap_and_go(symbol, intervalo, stop_pct, target_pct)
            for tr in trades:
                if solo_primera_hora:
                    hora = tr.get('hora_rotura') or ''
                    if not ('09:30' <= hora < '10:00'):
                        continue
                tr['symbol'] = symbol
                todos.append(tr)

        return todos
    
    def agregar_avistamiento_x(self, symbol, fecha, trader, imagen=None, nota=None, datos_finviz=None):
        """
        Registra que un trader operó 'symbol' en 'fecha', con una foto (opcional)
        y una nota/frase (opcional) para investigar ese día más adelante.
        Si el ticker no existe en la BD principal, lo añade (clona) con su intradía.
        Si ya existe, solo registra el avistamiento.
        datos_finviz: dict opcional ya pre-consultado (para lotes).
        """
        symbol = symbol.upper().strip()
        from datetime import date

        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM scanner_results WHERE symbol = ?', (symbol,))
        existe_principal = cursor.fetchone()[0] > 0
        conn.close()

        mensaje = ""
        if not existe_principal:
            try:
                self.agregar_ticker_manual(symbol, datos_finviz=datos_finviz)
                mensaje = f"✓ {symbol} no estaba en la BD principal — añadido con su intradía."
            except Exception as e:
                mensaje = f"⚠ {symbol}: no se pudo añadir a la BD principal ({e}). Se registra igual el avistamiento."

        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO x_tickers (symbol, fecha_agregado)
            VALUES (?, ?)
        ''', (symbol, str(date.today())))
        cursor.execute('''
            INSERT INTO x_avistamientos (symbol, fecha, trader, imagen, nota, fecha_registro)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (symbol, fecha, trader.strip(), imagen, nota, str(date.today())))
        conn.commit()
        conn.close()

        return mensaje

    def reparar_datos_finviz_faltantes(self):
        """
        Repara float/short/rvol/atr/rsi/gap/inst_own en scanner_results para
        símbolos que quedaron sin esos datos (por el bug del quote individual
        roto, por haber quedado fuera del filtro cuando se añadieron, o
        porque son de antes de que empezáramos a guardar inst_own).
        Consulta el screener de Finviz (Small + Micro cap) UNA vez para
        todos los que faltan, y actualiza lo que encuentre.
        Devuelve (reparados, lista_sin_encontrar).
        """
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT symbol FROM scanner_results
            WHERE float_shares IS NULL OR rvol IS NULL OR inst_own IS NULL
        ''')
        simbolos = [r[0] for r in cursor.fetchall()]
        conn.close()

        if not simbolos:
            print("✓ No hay tickers pendientes de reparar")
            return 0, []

        print(f"Intentando reparar {len(simbolos)} tickers sin datos completos...")
        detalles = self.enriquecer_completo(simbolos)

        conn = self.conectar()
        cursor = conn.cursor()
        reparados = 0
        for sym in simbolos:
            det = detalles.get(sym)
            if not det:
                continue
            cursor.execute('''
                UPDATE scanner_results
                SET float_shares = ?, short_float_pct = ?, rvol = ?,
                    gap_pct = ?, atr = ?, rsi = ?, inst_own = ?
                WHERE symbol = ?
            ''', (det.get('float_shares'), det.get('short_float_pct'), det.get('rvol'),
                  det.get('gap_pct'), det.get('atr'), det.get('rsi'), det.get('inst_own'), sym))
            reparados += 1
        conn.commit()
        conn.close()

        sin_encontrar = [s for s in simbolos if s not in detalles]
        print(f"✓ {reparados} reparados · {len(sin_encontrar)} fuera de rango (Small/Micro), no se pudieron reparar")
        if sin_encontrar:
            print(f"  Sin datos: {sin_encontrar}")

        return reparados, sin_encontrar

    def agregar_lote_x(self, symbols, fecha, trader, imagen=None, notas_individuales=None, nota_general=None):
        """
        Añade VARIOS tickers de golpe, compartiendo fecha/trader/imagen
        (una publicación de X con varios tickers). Consulta Finviz UNA sola
        vez para todo el lote (rápido), en vez de una vez por ticker.
        notas_individuales: dict {symbol: nota} — tiene prioridad sobre nota_general.
        Devuelve lista de (symbol, mensaje).
        """
        notas_individuales = notas_individuales or {}
        symbols = [s.upper().strip() for s in symbols if s.strip()]

        # Solo golpeamos Finviz para los que de verdad son nuevos
        conn = self.conectar()
        cursor = conn.cursor()
        nuevos = []
        for sym in symbols:
            cursor.execute('SELECT COUNT(*) FROM scanner_results WHERE symbol = ?', (sym,))
            if cursor.fetchone()[0] == 0:
                nuevos.append(sym)
        conn.close()

        datos_finviz = {}
        
        if nuevos:
            print(f"Consultando Finviz para {len(nuevos)} tickers nuevos del lote...")
            datos_finviz = self.enriquecer_completo(nuevos)

        resultados = []
        for sym in symbols:
            nota = notas_individuales.get(sym) or nota_general
            msg = self.agregar_avistamiento_x(sym, fecha, trader, imagen=imagen,
                                               nota=nota, datos_finviz=datos_finviz)
            resultados.append((sym, msg))

        return resultados

    def obtener_x_tickers_con_avistamientos(self, filtro_datos=None):
        """
        Devuelve todos los tickers de la sub-base X con sus avistamientos.
        filtro_datos: None (todos) | 'con_datos' | 'sin_datos'
        'con_datos' = tiene float o RVOL guardado. 'sin_datos' = le falta todo.
        """
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('SELECT symbol, fecha_agregado FROM x_tickers ORDER BY fecha_agregado DESC')
        tickers = cursor.fetchall()

        resultado = []
        for symbol, fecha_agregado in tickers:
            cursor.execute('''
                SELECT fecha, trader, imagen, nota FROM x_avistamientos
                WHERE symbol = ? ORDER BY fecha DESC
            ''', (symbol,))
            avistamientos = cursor.fetchall()

            cursor.execute('''
                SELECT float_shares, rvol FROM scanner_results
                WHERE symbol = ? ORDER BY fecha DESC LIMIT 1
            ''', (symbol,))
            datos_row = cursor.fetchone()
            tiene_datos = bool(datos_row and (datos_row[0] is not None or datos_row[1] is not None))

            if filtro_datos == 'con_datos' and not tiene_datos:
                continue
            if filtro_datos == 'sin_datos' and tiene_datos:
                continue

            resultado.append({
                'symbol': symbol,
                'fecha_agregado': fecha_agregado,
                'avistamientos': avistamientos,
                'tiene_datos': tiene_datos,
            })
        conn.close()
        return resultado

    def obtener_x_agrupado_por_publicacion(self):
        """
        Agrupa los avistamientos por (fecha, trader, imagen) para reconstruir
        las 'publicaciones' originales de X: varios tickers, mismo día,
        mismo trader, misma foto.
        """
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fecha, trader, imagen, symbol, nota
            FROM x_avistamientos
            ORDER BY fecha DESC, trader ASC, id ASC
        ''')
        filas = cursor.fetchall()
        conn.close()

        from collections import OrderedDict
        grupos = OrderedDict()
        for fecha, trader, imagen, symbol, nota in filas:
            clave = (fecha, trader, imagen)
            if clave not in grupos:
                grupos[clave] = []
            grupos[clave].append({'symbol': symbol, 'nota': nota})

        resultado = []
        for (fecha, trader, imagen), tickers in grupos.items():
            resultado.append({
                'fecha': fecha, 'trader': trader, 'imagen': imagen, 'tickers': tickers
            })
        resultado.sort(key=lambda x: x['fecha'], reverse=True)
        return resultado
    
    def barrido_r_gapgo(self, intervalo='5m', stop_min=2.0, stop_max=7.0, target_max=7.0, paso=0.5, solo_rvol_alto=False, solo_primera_hora=False):
        """
        Barrido optimizado: lee el intradía UNA vez por ticker, detecta las
        roturas una vez, y recalcula solo el R para cada combinación stop/target.
        Stop desde stop_min (descarta stops irreales).
        """
        from collections import defaultdict

        tickers = self.obtener_tickers_seguimiento()
        simbolos = [t[0] for t in tickers]

        # ── FASE 1: detectar todas las roturas UNA sola vez ──
        # Para cada rotura guardamos: entrada, y las velas posteriores (high/low)
        roturas = []  # lista de dicts: {entrada, highs_post, lows_post, cierre, rvol_30}

        for symbol in simbolos:
            datos = self.obtener_intradia(symbol, intervalo)
            if not datos:
                continue
            rvol_acc = self.calcular_rvol_accionable_por_dia(symbol, intervalo)

            por_dia = defaultdict(list)
            for d in datos:
                por_dia[d[0][:10]].append(d)

            for fecha, velas in por_dia.items():
                pre = [v for v in velas if len(v) > 7 and v[7] == 'pre']
                regular = [v for v in velas if len(v) <= 7 or v[7] == 'regular']
                if not pre or not regular:
                    continue
                pm_high = max(v[2] for v in pre)

                rotura_idx = None
                for i, v in enumerate(regular):
                    if v[4] > pm_high:
                        rotura_idx = i
                        break
                if rotura_idx is None:
                    continue

                entrada = regular[rotura_idx][4]
                hora_rotura = regular[rotura_idx][0][11:16]
                post = regular[rotura_idx + 1:]  # velas después de la rotura
                roturas.append({
                    'entrada': entrada,
                    'hora': hora_rotura,
                    'highs': [v[2] for v in post],
                    'lows': [v[3] for v in post],
                    'cierre': regular[-1][4],
                    'rvol_30': rvol_acc.get(fecha, {}).get('rvol_30'),
                })

        # ── FASE 2: generar combinaciones y calcular R (rápido) ──
        valores_stop = []
        v = stop_min
        while v <= stop_max + 0.001:
            valores_stop.append(round(v, 1))
            v += paso

        valores_target = []
        v = paso
        while v <= target_max + 0.001:
            valores_target.append(round(v, 1))
            v += paso

        resultados = []

        for stop_pct in valores_stop:
            for target_pct in valores_target:
                if target_pct <= stop_pct:
                    continue  # target debe ser mayor que stop
                total_r = 0
                n = 0
                wins = 0
                for r in roturas:
                    if solo_rvol_alto:
                        if r['rvol_30'] is None or r['rvol_30'] <= 1.5:
                            continue
                    if solo_primera_hora:
                        if not ('09:30' <= r['hora'] < '10:00'):
                            continue
                    entrada = r['entrada']
                    stop = entrada * (1 - stop_pct / 100)
                    target = entrada * (1 + target_pct / 100)

                    resultado_r = None
                    for j in range(len(r['highs'])):
                        toca_stop = r['lows'][j] <= stop
                        toca_target = r['highs'][j] >= target
                        if toca_stop:  # conservador: stop primero si ambos
                            resultado_r = -1.0
                            break
                        elif toca_target:
                            resultado_r = target_pct / stop_pct
                            break
                    if resultado_r is None:
                        mov_pct = ((r['cierre'] - entrada) / entrada) * 100
                        resultado_r = mov_pct / stop_pct

                    total_r += resultado_r
                    n += 1
                    if resultado_r > 0:
                        wins += 1

                if n > 0:
                    resultados.append({
                        'stop': stop_pct,
                        'target': target_pct,
                        'ratio': round(target_pct / stop_pct, 2),
                        'n': n,
                        'r_esperado': round(total_r / n, 4),
                        'r_total': round(total_r, 1),
                        'win_rate': round(wins / n * 100, 1),
                    })

        resultados.sort(key=lambda x: x['r_esperado'], reverse=True)
        return resultados

    # ══════════════════════════════════════════════════════════════════
    #  FIRST RED DAY (SHORT) — integrado desde los scripts de análisis
    #  Edge confirmado: sobreextensión ≥30% + entrada pierde_open
    # ══════════════════════════════════════════════════════════════════

    def reconstruir_dias_desde_intradia(self, symbol, intervalo='5m'):
        """
        Reconstruye velas diarias (open, high, low, close, volumen) desde
        el intradía guardado, agrupando por sesión regular. Cada día
        conserva también sus velas originales ('velas') para poder
        simular entradas intradía en el día siguiente.
        """
        datos = self.obtener_intradia(symbol, intervalo)
        if not datos:
            return []
        from collections import defaultdict
        por_dia = defaultdict(list)
        for d in datos:
            por_dia[d[0][:10]].append(d)
        dias = []
        for fecha in sorted(por_dia.keys()):
            regular = [v for v in por_dia[fecha] if len(v) <= 7 or v[7] == 'regular']
            if not regular:
                continue
            dias.append({
                'fecha': fecha,
                'open': regular[0][1],
                'high': max(v[2] for v in regular),
                'low': min(v[3] for v in regular),
                'close': regular[-1][4],
                'volumen': sum(v[5] or 0 for v in regular),
                'velas': regular,
            })
        return dias

    def _medir_short(self, velas, entrada_precio, idx_desde, stop_pct, target_pct):
        """
        Simula un SHORT: stop ARRIBA, target ABAJO. Conservador: si una
        vela toca ambos, se asume que tocó el stop primero.
        """
        stop = entrada_precio * (1 + stop_pct / 100)
        target = entrada_precio * (1 - target_pct / 100)
        for v in velas[idx_desde:]:
            if v[2] >= stop:
                return -1.0
            elif v[3] <= target:
                return round(target_pct / stop_pct, 3)
        cierre = velas[-1][4]
        return round(((entrada_precio - cierre) / entrada_precio * 100) / stop_pct, 3)

    def _medir_long(self, velas, entrada_precio, idx_desde, stop_pct, target_pct):
        """
        Simula un LONG: stop ABAJO, target ARRIBA. Conservador: si una
        vela toca ambos, se asume que tocó el stop primero.
        """
        stop = entrada_precio * (1 - stop_pct / 100)
        target = entrada_precio * (1 + target_pct / 100)
        for v in velas[idx_desde:]:
            if v[3] <= stop:
                return -1.0
            elif v[2] >= target:
                return round(target_pct / stop_pct, 3)
        cierre = velas[-1][4]
        return round(((cierre - entrada_precio) / entrada_precio * 100) / stop_pct, 3)

    def detectar_first_red_day(self, symbol, min_verdes=2, tipo_rojo='ambas',
                                 vol_decreciente=True, sobreext_min=30.0,
                                 entrada='pierde_open', stop_pct=3.0, target_pct=6.0):
        """
        Detecta First Red Day SHORT: tras min_verdes días verdes con
        sobreextensión >= sobreext_min%, el primer día rojo se opera en
        corto al día SIGUIENTE (D+1) — entrada realista, sin lookahead.
        entrada: 'pierde_open' | 'dia_siguiente' | 'pierde_vwap'
        """
        dias = self.reconstruir_dias_desde_intradia(symbol, '5m')
        if len(dias) < min_verdes + 2:
            return []

        def es_verde(d):
            return d['close'] >= d['open']

        def sobreext(indices_prev):
            prev = [dias[j] for j in indices_prev]
            mn = min(d['low'] for d in prev)
            mx = max(d['high'] for d in prev)
            return (mx - mn) / mn * 100 if mn > 0 else 0

        def punto_entrada(dia_op):
            velas = dia_op['velas']
            if entrada == 'dia_siguiente':
                return velas[0][1], 1
            elif entrada == 'pierde_vwap':
                for k, v in enumerate(velas):
                    if len(v) > 6 and v[6] is not None and v[4] < v[6]:
                        return v[4], k + 1
                return None, None
            else:  # pierde_open (por defecto)
                op = velas[0][1]
                for k, v in enumerate(velas):
                    if v[3] < op:
                        return op, k + 1
                return None, None

        resultados = []
        for i in range(min_verdes, len(dias) - 1):
            previos_idx = list(range(i - min_verdes, i))
            if not all(es_verde(dias[j]) for j in previos_idx):
                continue
            dia, ant = dias[i], dias[i - 1]
            rojo_apertura = dia['close'] < dia['open']
            rojo_cierre_ant = dia['close'] < ant['close']
            if tipo_rojo == 'apertura' and not rojo_apertura:
                continue
            if tipo_rojo == 'cierre_ant' and not rojo_cierre_ant:
                continue
            if tipo_rojo == 'ambas' and not (rojo_apertura and rojo_cierre_ant):
                continue
            if vol_decreciente and not (dia['volumen'] < ant['volumen']):
                continue

            sob = sobreext(previos_idx)
            if sob < sobreext_min:
                continue

            dia_operativa = dias[i + 1]
            entrada_precio, idx_desde = punto_entrada(dia_operativa)
            if entrada_precio is None:
                continue

            r = self._medir_short(dia_operativa['velas'], entrada_precio, idx_desde, stop_pct, target_pct)
            resultados.append({
                'fecha_senal': dia['fecha'],
                'fecha_operativa': dia_operativa['fecha'],
                'sobreextension': round(sob, 1),
                'entrada': round(entrada_precio, 4),
                'resultado_r': r,
            })

        return resultados

    def procesar_pendientes_enriquecimiento(self, limite=15):
        """
        Procesa en pequeños lotes los tickers de scanner_results que
        quedaron sin float/rvol (guardados 'rápido' sin enriquecer).
        Pensado para correr en segundo plano cada cierto tiempo.
        Devuelve cuántos se enriquecieron en esta pasada.
        """
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT symbol FROM scanner_results
            WHERE float_shares IS NULL AND rvol IS NULL
            LIMIT ?
        ''', (limite,))
        simbolos = [r[0] for r in cursor.fetchall()]
        conn.close()

        if not simbolos:
            return 0

        detalles = self.enriquecer_completo(simbolos)

        conn = self.conectar()
        cursor = conn.cursor()
        actualizados = 0
        for sym in simbolos:
            det = detalles.get(sym)
            if not det:
                continue
            cursor.execute('''
                UPDATE scanner_results
                SET price = COALESCE(price, ?), change_pct = COALESCE(change_pct, ?),
                    volume = COALESCE(volume, ?), float_shares = ?, short_float_pct = ?,
                    rvol = ?, gap_pct = ?, atr = ?, rsi = ?, inst_own = ?
                WHERE symbol = ?
            ''', (det.get('price'), det.get('change_pct'), det.get('volume'),
                  det.get('float_shares'), det.get('short_float_pct'), det.get('rvol'),
                  det.get('gap_pct'), det.get('atr'), det.get('rsi'), det.get('inst_own'), sym))
            actualizados += 1
        conn.commit()
        conn.close()
        return actualizados

    def procesar_pendientes_intradia(self, limite=5, max_intentos=2):
        """
        Descarga el intradía para tickers sin velas guardadas. Si un
        ticker falla max_intentos veces seguidas (probablemente no existe
        de verdad, ej. símbolo corrupto), se deja de reintentar para no
        atascar la cola con el mismo ticker para siempre.
        """
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT sr.symbol FROM scanner_results sr
            WHERE NOT EXISTS (
                SELECT 1 FROM intraday_data i WHERE i.symbol = sr.symbol
            )
            AND COALESCE(sr.intradia_intentos, 0) < ?
            LIMIT ?
        ''', (max_intentos, limite))
        simbolos = [r[0] for r in cursor.fetchall()]
        conn.close()

        procesados = 0
        for sym in simbolos:
            try:
                self.descargar_intradia_con_vwap(sym)
            except Exception as e:
                print(f"[fondo-intradia] error con {sym}: {e}")

            conn = self.conectar()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM intraday_data WHERE symbol = ?', (sym,))
            tiene_datos = cursor.fetchone()[0] > 0
            if not tiene_datos:
                cursor.execute('''
                    UPDATE scanner_results
                    SET intradia_intentos = COALESCE(intradia_intentos, 0) + 1
                    WHERE symbol = ?
                ''', (sym,))
            conn.commit()
            conn.close()
            procesados += 1

        return procesados

    def r_agregado_first_red_day(self, min_verdes=2, tipo_rojo='ambas', vol_decreciente=True,
                                   sobreext_min=30.0, entrada='pierde_open',
                                   stop_pct=3.0, target_pct=6.0):
        """Mide R en First Red Day para TODOS los tickers en seguimiento."""
        tickers = self.obtener_tickers_seguimiento()
        simbolos = [t[0] for t in tickers]
        todos = []
        for symbol in simbolos:
            trades = self.detectar_first_red_day(symbol, min_verdes, tipo_rojo, vol_decreciente,
                                                    sobreext_min, entrada, stop_pct, target_pct)
            for tr in trades:
                tr['symbol'] = symbol
                todos.append(tr)
        return todos

    def barrido_r_first_red_day(self, min_verdes=2, tipo_rojo='ambas', vol_decreciente=True,
                                  sobreext_min=30.0, entrada='pierde_open',
                                  stop_min=2.0, stop_max=7.0, target_max=10.0, paso=0.5):
        """
        Barrido de stop/target para First Red Day, con el resto de filtros
        fijos (los que elige el usuario). Recopila las señales UNA vez y
        recalcula el R para cada combinación (rápido).
        """
        tickers = self.obtener_tickers_seguimiento()
        simbolos = [t[0] for t in tickers]

        señales = []
        for symbol in simbolos:
            dias = self.reconstruir_dias_desde_intradia(symbol, '5m')
            if len(dias) < min_verdes + 2:
                continue

            def es_verde(d):
                return d['close'] >= d['open']

            def sobreext(indices_prev):
                prev = [dias[j] for j in indices_prev]
                mn = min(d['low'] for d in prev)
                mx = max(d['high'] for d in prev)
                return (mx - mn) / mn * 100 if mn > 0 else 0

            for i in range(min_verdes, len(dias) - 1):
                previos_idx = list(range(i - min_verdes, i))
                if not all(es_verde(dias[j]) for j in previos_idx):
                    continue
                dia, ant = dias[i], dias[i - 1]
                rojo_apertura = dia['close'] < dia['open']
                rojo_cierre_ant = dia['close'] < ant['close']
                if tipo_rojo == 'apertura' and not rojo_apertura:
                    continue
                if tipo_rojo == 'cierre_ant' and not rojo_cierre_ant:
                    continue
                if tipo_rojo == 'ambas' and not (rojo_apertura and rojo_cierre_ant):
                    continue
                if vol_decreciente and not (dia['volumen'] < ant['volumen']):
                    continue
                sob = sobreext(previos_idx)
                if sob < sobreext_min:
                    continue

                dia_op = dias[i + 1]
                velas = dia_op['velas']
                entrada_precio = None
                idx_desde = None
                if entrada == 'dia_siguiente':
                    entrada_precio, idx_desde = velas[0][1], 1
                elif entrada == 'pierde_vwap':
                    for k, v in enumerate(velas):
                        if len(v) > 6 and v[6] is not None and v[4] < v[6]:
                            entrada_precio, idx_desde = v[4], k + 1
                            break
                else:
                    op = velas[0][1]
                    for k, v in enumerate(velas):
                        if v[3] < op:
                            entrada_precio, idx_desde = op, k + 1
                            break

                if entrada_precio is None:
                    continue

                post = velas[idx_desde:]
                señales.append({
                    'entrada': entrada_precio,
                    'highs': [v[2] for v in post],
                    'lows': [v[3] for v in post],
                    'cierre': velas[-1][4],
                })

        return self._barrer_stop_target_short(señales, stop_min, stop_max, target_max, paso)

    # ══════════════════════════════════════════════════════════════════
    #  OVEREXTENDED GAP DOWN (SHORT)
    #  Edge emergente confirmado: sobreextensión ≥50% + rebote_resist
    # ══════════════════════════════════════════════════════════════════

    def detectar_overextended_gap_down(self, symbol, gap_min=2.0, dias_sob=2, sobreext_min=50.0,
                                         entrada='rebote_resist', stop_pct=3.0, target_pct=6.0):
        """
        Detecta Overextended Gap Down SHORT: tras sobreextensión previa,
        la acción abre por debajo del cierre anterior (gap down). Se
        opera el rebote hacia la resistencia del día anterior, o la
        pérdida del open, en corto.
        entrada: 'rebote_resist' | 'pierde_open'
        """
        dias = self.reconstruir_dias_desde_intradia(symbol, '5m')
        if len(dias) < dias_sob + 2:
            return []

        def sobreext_prev(i, n):
            prev = dias[max(0, i - n):i]
            if not prev:
                return 0
            mn = min(d['low'] for d in prev)
            mx = max(d['high'] for d in prev)
            return (mx - mn) / mn * 100 if mn > 0 else 0

        resultados = []
        for i in range(1, len(dias) - 1):
            ant, dia = dias[i - 1], dias[i]
            gap = (ant['close'] - dia['open']) / ant['close'] * 100
            if gap < gap_min:
                continue
            sob = sobreext_prev(i, dias_sob)
            if sob < sobreext_min:
                continue

            velas = dia['velas']
            entrada_precio, idx_desde = None, None
            if entrada == 'rebote_resist':
                for k, v in enumerate(velas):
                    if v[2] >= ant['close'] * 0.98:
                        entrada_precio, idx_desde = v[4], k + 1
                        break
            else:
                op = velas[0][1]
                for k, v in enumerate(velas):
                    if v[3] < op:
                        entrada_precio, idx_desde = op, k + 1
                        break

            if entrada_precio is None:
                continue

            r = self._medir_short(velas, entrada_precio, idx_desde, stop_pct, target_pct)
            resultados.append({
                'fecha': dia['fecha'],
                'gap_pct': round(gap, 2),
                'sobreextension': round(sob, 1),
                'entrada': round(entrada_precio, 4),
                'resultado_r': r,
            })

        return resultados

    def r_agregado_overext_gap_down(self, gap_min=2.0, dias_sob=2, sobreext_min=50.0,
                                      entrada='rebote_resist', stop_pct=3.0, target_pct=6.0):
        """Mide R en Overextended Gap Down para TODOS los tickers en seguimiento."""
        tickers = self.obtener_tickers_seguimiento()
        simbolos = [t[0] for t in tickers]
        todos = []
        for symbol in simbolos:
            trades = self.detectar_overextended_gap_down(symbol, gap_min, dias_sob, sobreext_min,
                                                            entrada, stop_pct, target_pct)
            for tr in trades:
                tr['symbol'] = symbol
                todos.append(tr)
        return todos

    def barrido_r_overext_gap_down(self, gap_min=2.0, dias_sob=2, sobreext_min=50.0,
                                     entrada='rebote_resist',
                                     stop_min=2.0, stop_max=7.0, target_max=10.0, paso=0.5):
        """Barrido de stop/target para Overextended Gap Down, resto de filtros fijos."""
        tickers = self.obtener_tickers_seguimiento()
        simbolos = [t[0] for t in tickers]

        señales = []
        for symbol in simbolos:
            dias = self.reconstruir_dias_desde_intradia(symbol, '5m')
            if len(dias) < dias_sob + 2:
                continue

            def sobreext_prev(i, n):
                prev = dias[max(0, i - n):i]
                if not prev:
                    return 0
                mn = min(d['low'] for d in prev)
                mx = max(d['high'] for d in prev)
                return (mx - mn) / mn * 100 if mn > 0 else 0

            for i in range(1, len(dias) - 1):
                ant, dia = dias[i - 1], dias[i]
                gap = (ant['close'] - dia['open']) / ant['close'] * 100
                if gap < gap_min:
                    continue
                sob = sobreext_prev(i, dias_sob)
                if sob < sobreext_min:
                    continue

                velas = dia['velas']
                entrada_precio, idx_desde = None, None
                if entrada == 'rebote_resist':
                    for k, v in enumerate(velas):
                        if v[2] >= ant['close'] * 0.98:
                            entrada_precio, idx_desde = v[4], k + 1
                            break
                else:
                    op = velas[0][1]
                    for k, v in enumerate(velas):
                        if v[3] < op:
                            entrada_precio, idx_desde = op, k + 1
                            break

                if entrada_precio is None:
                    continue

                post = velas[idx_desde:]
                señales.append({
                    'entrada': entrada_precio,
                    'highs': [v[2] for v in post],
                    'lows': [v[3] for v in post],
                    'cierre': velas[-1][4],
                })

        return self._barrer_stop_target_short(señales, stop_min, stop_max, target_max, paso)

    def _barrer_stop_target_short(self, señales, stop_min, stop_max, target_max, paso):
        """
        Barrido genérico de stop/target para SHORTS, sobre una lista de
        señales ya recopiladas (con 'entrada', 'highs', 'lows', 'cierre').
        Compartido por First Red Day y Overextended Gap Down.
        """
        valores_stop = []
        v = stop_min
        while v <= stop_max + 0.001:
            valores_stop.append(round(v, 1))
            v += paso

        valores_target = []
        v = paso
        while v <= target_max + 0.001:
            valores_target.append(round(v, 1))
            v += paso

        resultados = []
        for stop_pct in valores_stop:
            for target_pct in valores_target:
                total_r = 0
                n = 0
                wins = 0
                for s in señales:
                    entrada_precio = s['entrada']
                    stop = entrada_precio * (1 + stop_pct / 100)
                    target = entrada_precio * (1 - target_pct / 100)
                    r = None
                    for j in range(len(s['highs'])):
                        if s['highs'][j] >= stop:      # conservador: stop primero si ambos
                            r = -1.0
                            break
                        elif s['lows'][j] <= target:
                            r = target_pct / stop_pct
                            break
                    if r is None:
                        r = ((entrada_precio - s['cierre']) / entrada_precio * 100) / stop_pct
                    total_r += r
                    n += 1
                    if r > 0:
                        wins += 1

                if n > 0:
                    resultados.append({
                        'stop': stop_pct,
                        'target': target_pct,
                        'ratio': round(target_pct / stop_pct, 2),
                        'n': n,
                        'r_esperado': round(total_r / n, 4),
                        'win_rate': round(wins / n * 100, 1),
                    })

        resultados.sort(key=lambda x: x['r_esperado'], reverse=True)
        return resultados

    def _barrer_stop_target_long(self, señales, stop_min, stop_max, target_max, paso):
        """
        Barrido genérico de stop/target para LONGS, sobre una lista de
        señales ya recopiladas (con 'entrada', 'highs', 'lows', 'cierre').
        Compartido por VWAP Bounce y Reciclaje.
        """
        valores_stop = []
        v = stop_min
        while v <= stop_max + 0.001:
            valores_stop.append(round(v, 1))
            v += paso

        valores_target = []
        v = paso
        while v <= target_max + 0.001:
            valores_target.append(round(v, 1))
            v += paso

        resultados = []
        for stop_pct in valores_stop:
            for target_pct in valores_target:
                total_r = 0
                n = 0
                wins = 0
                for s in señales:
                    entrada_precio = s['entrada']
                    stop = entrada_precio * (1 - stop_pct / 100)
                    target = entrada_precio * (1 + target_pct / 100)
                    r = None
                    for j in range(len(s['lows'])):
                        if s['lows'][j] <= stop:
                            r = -1.0
                            break
                        elif s['highs'][j] >= target:
                            r = target_pct / stop_pct
                            break
                    if r is None:
                        r = ((s['cierre'] - entrada_precio) / entrada_precio * 100) / stop_pct
                    total_r += r
                    n += 1
                    if r > 0:
                        wins += 1

                if n > 0:
                    resultados.append({
                        'stop': stop_pct,
                        'target': target_pct,
                        'ratio': round(target_pct / stop_pct, 2),
                        'n': n,
                        'r_esperado': round(total_r / n, 4),
                        'win_rate': round(wins / n * 100, 1),
                    })

        resultados.sort(key=lambda x: x['r_esperado'], reverse=True)
        return resultados

    # ══════════════════════════════════════════════════════════════════
    #  VWAP BOUNCE (LONG) — ahora con R real, no solo promedios
    # ══════════════════════════════════════════════════════════════════

    def medir_r_vwap_bounce(self, symbol, intervalo='5m', stop_pct=2.0, target_pct=4.0):
        """
        Mide R real (LONG) para CADA rebote de VWAP detectado en el día
        (vela cuyo low toca/cruza el VWAP pero cierra por encima).
        """
        datos = self.obtener_intradia(symbol, intervalo)
        if not datos:
            return []
        from collections import defaultdict
        por_dia = defaultdict(list)
        for d in datos:
            por_dia[d[0][:10]].append(d)

        resultados = []
        for fecha, velas in por_dia.items():
            regular = [v for v in velas if (len(v) <= 7 or v[7] == 'regular') and v[6] is not None]
            if len(regular) < 3:
                continue
            for i, v in enumerate(regular):
                low, close, vwap = v[3], v[4], v[6]
                if vwap is None:
                    continue
                if low <= vwap and close > vwap:
                    r = self._medir_long(regular, close, i + 1, stop_pct, target_pct)
                    resultados.append({
                        'fecha': fecha,
                        'hora': v[0][11:16],
                        'entrada': round(close, 4),
                        'resultado_r': r,
                    })

        return resultados

    def r_agregado_vwap_bounce(self, intervalo='5m', stop_pct=2.0, target_pct=4.0):
        """Mide R en VWAP Bounce para TODOS los tickers en seguimiento."""
        tickers = self.obtener_tickers_seguimiento()
        simbolos = [t[0] for t in tickers]
        todos = []
        for symbol in simbolos:
            trades = self.medir_r_vwap_bounce(symbol, intervalo, stop_pct, target_pct)
            for tr in trades:
                tr['symbol'] = symbol
                todos.append(tr)
        return todos

    def barrido_r_vwap_bounce(self, intervalo='5m', stop_min=1.0, stop_max=5.0, target_max=10.0, paso=0.5):
        """Barrido de stop/target para VWAP Bounce sobre todos los tickers."""
        tickers = self.obtener_tickers_seguimiento()
        simbolos = [t[0] for t in tickers]

        señales = []
        for symbol in simbolos:
            datos = self.obtener_intradia(symbol, intervalo)
            if not datos:
                continue
            from collections import defaultdict
            por_dia = defaultdict(list)
            for d in datos:
                por_dia[d[0][:10]].append(d)

            for fecha, velas in por_dia.items():
                regular = [v for v in velas if (len(v) <= 7 or v[7] == 'regular') and v[6] is not None]
                if len(regular) < 3:
                    continue
                for i, v in enumerate(regular):
                    low, close, vwap = v[3], v[4], v[6]
                    if vwap is None:
                        continue
                    if low <= vwap and close > vwap:
                        post = regular[i + 1:]
                        señales.append({
                            'entrada': close,
                            'highs': [x[2] for x in post],
                            'lows': [x[3] for x in post],
                            'cierre': regular[-1][4],
                        })

        return self._barrer_stop_target_long(señales, stop_min, stop_max, target_max, paso)

    # ══════════════════════════════════════════════════════════════════
    #  RECICLAJE (LONG) — micro-impulsos, ahora con R real
    # ══════════════════════════════════════════════════════════════════

    def medir_r_reciclaje(self, symbol, stop_pct=1.0, target_pct=2.0, umbral=1.0, ventana=2):
        """
        Mide R real (LONG) para cada micro-impulso detectado. Entra en la
        base del impulso (close antes de la subida), stop/target pequeños
        (scalping). Corre en 1 minuto, como el detector original.
        """
        datos = self.obtener_intradia(symbol, '1m')
        if not datos:
            return []
        from collections import defaultdict
        por_dia = defaultdict(list)
        for d in datos:
            por_dia[d[0][:10]].append(d)

        resultados = []
        for fecha, velas in por_dia.items():
            activas = [v for v in velas if (len(v) <= 7 or v[7] in ('pre', 'regular'))]
            if len(activas) < ventana:
                continue
            i = 0
            while i < len(activas) - 1:
                base = activas[i][4]
                mejor_subida = 0
                fin_idx = i
                for j in range(i + 1, min(i + ventana + 1, len(activas))):
                    alto = activas[j][2]
                    subida = ((alto - base) / base) * 100
                    if subida > mejor_subida:
                        mejor_subida = subida
                        fin_idx = j
                if mejor_subida >= umbral:
                    # Entrada REALISTA: al cierre de la vela donde se confirmó
                    # el impulso, no en la base (eso sería mirar el futuro).
                    entrada_real = activas[fin_idx][4]
                    r = self._medir_long(activas, entrada_real, fin_idx + 1, stop_pct, target_pct)
                    resultados.append({
                        'fecha': fecha,
                        'hora': activas[fin_idx][0][11:16],
                        'entrada': round(entrada_real, 4),
                        'subida_detectada': round(mejor_subida, 2),
                        'resultado_r': r,
                    })
                    i = fin_idx
                else:
                    i += 1

        return resultados

    def r_agregado_reciclaje(self, stop_pct=1.0, target_pct=2.0, umbral=1.0, ventana=2):
        """Mide R en Reciclaje para TODOS los tickers en seguimiento."""
        tickers = self.obtener_tickers_seguimiento()
        simbolos = [t[0] for t in tickers]
        todos = []
        for symbol in simbolos:
            trades = self.medir_r_reciclaje(symbol, stop_pct, target_pct, umbral, ventana)
            for tr in trades:
                tr['symbol'] = symbol
                todos.append(tr)
        return todos

    def barrido_r_reciclaje(self, stop_min=0.5, stop_max=3.0, target_max=6.0, paso=0.5,
                              umbral=1.0, ventana=2):
        """Barrido de stop/target para Reciclaje sobre todos los tickers."""
        tickers = self.obtener_tickers_seguimiento()
        simbolos = [t[0] for t in tickers]

        señales = []
        for symbol in simbolos:
            datos = self.obtener_intradia(symbol, '1m')
            if not datos:
                continue
            from collections import defaultdict
            por_dia = defaultdict(list)
            for d in datos:
                por_dia[d[0][:10]].append(d)

            for fecha, velas in por_dia.items():
                activas = [v for v in velas if (len(v) <= 7 or v[7] in ('pre', 'regular'))]
                if len(activas) < ventana:
                    continue
                i = 0
                while i < len(activas) - 1:
                    base = activas[i][4]
                    mejor_subida = 0
                    fin_idx = i
                    for j in range(i + 1, min(i + ventana + 1, len(activas))):
                        alto = activas[j][2]
                        subida = ((alto - base) / base) * 100
                        if subida > mejor_subida:
                            mejor_subida = subida
                            fin_idx = j
                    if mejor_subida >= umbral:
                        entrada_real = activas[fin_idx][4]
                        post = activas[fin_idx + 1:]
                        señales.append({
                            'entrada': entrada_real,
                            'highs': [x[2] for x in post],
                            'lows': [x[3] for x in post],
                            'cierre': activas[-1][4],
                        })
                        i = fin_idx
                    else:
                        i += 1

        return self._barrer_stop_target_long(señales, stop_min, stop_max, target_max, paso)

    # ══════════════════════════════════════════════════════════════════
    #  NOTICIAS / CATALIZADOR (Finnhub) — confirmado gratis por el RAG
    # ══════════════════════════════════════════════════════════════════

    def obtener_noticias_finnhub(self, symbol, dias_atras=30):
        """
        Trae noticias de Finnhub para un ticker en los últimos N días y
        las guarda (evita duplicados). Requiere FINNHUB_API_KEY en el .env
        (la misma que ya usa el proyecto). No se llama automáticamente en
        cada scan — es una consulta bajo demanda (botón en /estudio), para
        no gastar de más la cuota gratis ni ralentizar el scanner diario.
        """
        import requests
        from datetime import date, timedelta as td

        api_key = os.getenv('FINNHUB_API_KEY')
        if not api_key:
            print("⚠ No hay FINNHUB_API_KEY configurada en tu .env")
            return []

        symbol = symbol.upper().strip()
        hoy = date.today()
        desde = hoy - td(days=dias_atras)

        url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={desde}&to={hoy}&token={api_key}"

        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
        except Exception as e:
            print(f"✗ Error consultando Finnhub para {symbol}: {e}")
            return []

        if not isinstance(data, list):
            print(f"⚠ Respuesta inesperada de Finnhub para {symbol}: {data}")
            return []

        conn = self.conectar()
        cursor = conn.cursor()
        guardadas = 0
        resultado = []
        for item in data:
            ts = item.get('datetime')
            if not ts:
                continue
            fecha_noticia = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            headline = (item.get('headline') or '').strip()
            resumen = (item.get('summary') or '').strip()
            fuente = item.get('source', '')
            link = item.get('url', '')
            if not headline:
                continue
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO noticias
                    (symbol, fecha, headline, resumen, fuente, url, fecha_registro)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, fecha_noticia, headline, resumen, fuente, link, str(date.today())))
                if cursor.rowcount > 0:
                    guardadas += 1
            except Exception:
                pass
            resultado.append({
                'fecha': fecha_noticia, 'headline': headline, 'resumen': resumen,
                'fuente': fuente, 'url': link,
            })
        conn.commit()
        conn.close()

        resultado.sort(key=lambda x: x['fecha'], reverse=True)
        print(f"✓ {len(resultado)} noticias obtenidas para {symbol} ({guardadas} nuevas guardadas)")
        return resultado

    def obtener_noticias_guardadas(self, symbol, limite=30):
        """Devuelve las noticias ya guardadas de un ticker, sin consultar Finnhub."""
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fecha, headline, resumen, fuente, url
            FROM noticias WHERE symbol = ? ORDER BY fecha DESC LIMIT ?
        ''', (symbol.upper().strip(), limite))
        filas = cursor.fetchall()
        conn.close()
        return filas