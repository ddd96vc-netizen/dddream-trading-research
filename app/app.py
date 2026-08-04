from database import Database
import plotly.graph_objects as go
from database import Database
from plotly.subplots import make_subplots
import json
import os
from werkzeug.utils import secure_filename
from flask import Flask, request, redirect

'''def generar_grafico(symbol, datos_historico):
    fechas = []
    closes = []

    for fila in datos_historico:
        date = fila[0]
        close = fila[4]

        fechas.append(date)
        closes.append(close)

    fig = go.Figure()  
    fig.add_trace(go.Scatter(
        x=fechas,
        y=closes,
        mode='lines',
        name='Close Price',
        line=dict(color='#00ff00', width=2)  
    ))  

    fig.update_layout(
        title=f'📈 {symbol} - Histórico de Precios (1 año)',
        xaxis_title='Tiempo',
        yaxis_title='Precio ($)',
        template='plotly_dark',
        hovermode='x unified',
        height=600,
        xaxis_rangeslider_visible=False,
        xaxis=dict(
            rangeselector=dict(
                buttons=[
                    dict(count=1,  label="1D", step="day",  stepmode="backward"),
                    dict(count=5,  label="5D", step="day",  stepmode="backward"),
                    dict(count=10, label="10D", step="day", stepmode="backward"),
                    dict(count=1,  label="1M", step="month", stepmode="backward"),
                    dict(step="all", label="Todo")
                ],
                bgcolor='#0a0a0a',
                activecolor='#00ff00',
                font=dict(color='#00ff00')
            ),
            # Por defecto muestra solo los últimos 5 días
            range=[fechas[-min(len(fechas), 390)], fechas[-1]]
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )       

    html_grafico = fig.to_html(include_plotlyjs='cdn', div_id=f"graph-{symbol}")
    return html_grafico
'''

app = Flask(__name__)
db = Database()
db.crear_tabla()


UPLOAD_FOLDER = os.path.join('static', 'x_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    """Página principal - Menú de navegación"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>DDDreaM</title>
        <style>
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background-color: #0d0d0d;
                color: #00ff00;
                padding: 0;
                margin: 0;
                min-height: 100vh;
            }
            .hero {
                text-align: center;
                padding: 70px 20px 40px 20px;
                border-bottom: 1px solid #1f5f1f;
            }
            .hero h1 {
                font-size: 3.2em;
                margin: 0;
                letter-spacing: 4px;
                text-shadow: 0 0 20px rgba(0,255,0,0.4);
            }
            .hero .sub {
                color: #888;
                margin-top: 12px;
                font-size: 15px;
                letter-spacing: 1px;
            }
            .contenedor {
                max-width: 1000px;
                margin: 0 auto;
                padding: 40px 25px;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 20px;
            }
            .card {
                background: #141414;
                border: 1px solid #1f5f1f;
                border-radius: 10px;
                padding: 24px;
                text-decoration: none;
                display: block;
                transition: all .15s;
            }
            .card:hover {
                border-color: #00ff00;
                background: #191919;
                transform: translateY(-2px);
            }
            .card .icono { font-size: 28px; margin-bottom: 10px; }
            .card .titulo { color: #00ff00; font-size: 17px; font-weight: bold; margin-bottom: 6px; }
            .card .desc { color: #888; font-size: 13px; line-height: 1.5; }
            .card.x { border-color: #1DA1F2; }
            .card.x .titulo { color: #1DA1F2; }
            .card.backtest { border-color: #ff9800; }
            .card.backtest .titulo { color: #ff9800; }
            .card.agregado { border-color: #2962ff; }
            .card.agregado .titulo { color: #5e85ff; }
            .quick {
                margin-top: 35px;
                background: #141414;
                border: 1px solid #333;
                border-radius: 10px;
                padding: 20px 24px;
            }
            .quick label { display:block; color:#888; font-size:12px; letter-spacing:1px; margin-bottom:8px; }
            .quick form { display:flex; gap:10px; }
            .quick input {
                flex:1; background:#0a0a0a; color:#00ff00; border:1px solid #00ff00;
                padding:10px 12px; border-radius:6px; font-size:14px;
            }
            .quick button {
                background:#00ff00; color:#000; border:none; padding:10px 22px;
                border-radius:6px; font-weight:bold; cursor:pointer;
            }
        </style>
    </head>
    <body>
        <div class="hero">
            <h1>🎯 DDDreaM</h1>
            <div class="sub">Tu Flash Research propio de small caps · Backtesting con tus datos guardados</div>
        </div>

        <div class="contenedor">
            <div class="grid">
                <a href="/scanner" class="card">
                    <div class="icono">📊</div>
                    <div class="titulo">Scanner</div>
                    <div class="desc">Busca small caps operables, guarda su intradía y gestiona tu seguimiento.</div>
                </a>
                <a href="/analisis" class="card">
                    <div class="icono">🔬</div>
                    <div class="titulo">Análisis por Ticker</div>
                    <div class="desc">Gap & Go, VWAP Bounce y Reciclaje, día a día, para un ticker concreto.</div>
                </a>
                <a href="/agregado" class="card agregado">
                    <div class="icono">🌐</div>
                    <div class="titulo">Vista Agregada</div>
                    <div class="desc">Todos tus tickers juntos. Validación de edge con muestra completa.</div>
                </a>
                <a href="/backtest" class="card backtest">
                    <div class="icono">💰</div>
                    <div class="titulo">Backtest R</div>
                    <div class="desc">Mide si el Gap & Go gana dinero de verdad. Ajusta stop/target y lanza el barrido.</div>
                </a>
                <a href="/x" class="card x">
                    <div class="icono">📱</div>
                    <div class="titulo">X (Twitter) Watchlist</div>
                    <div class="desc">Casos de estudio: qué operaron los grandes, cuándo, con foto y notas.</div>
                </a>
            </div>

            <div class="quick">
                <label>IR DIRECTO A UN TICKER</label>
                <form onsubmit="event.preventDefault(); if(this.symbol.value) window.location.href='/estudio/' + this.symbol.value.toUpperCase();">
                    <input type="text" name="symbol" placeholder="Ej: GME" required>
                    <button type="submit">Ver gráfico →</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/api/status')
def status():
    """API - Devuelve JSON"""
    return {
        "status": "online",
        "app": "DDDreaM",
        "phase": "1 - Foundation",
        "version": "1.0.0"
    }

@app.route('/scanner')
def scanner():
    tickers_seguimiento = db.obtener_tickers_seguimiento()

    reparados_param = request.args.get('reparados')
    sin_encontrar_param = request.args.get('sin_encontrar')
    banner_reparacion = ""
    if reparados_param is not None:
        banner_reparacion = f"""
        <div style="background:#0a1a0a; border:1px solid #ff9800; padding:10px 16px;
                    border-radius:6px; margin-bottom:15px; font-size:13px; max-width:1200px;">
            🔧 Reparación completada: <b style="color:#00ff00;">{reparados_param}</b> tickers actualizados con datos de Finviz.
            {f'<span style="color:#888;"> · {sin_encontrar_param} fuera de rango (Small/Micro), no se pudieron reparar.</span>' if int(sin_encontrar_param or 0) > 0 else ''}
        </div>"""

    filas_html = ""
    for t in tickers_seguimiento:
        symbol, price, change_pct, volume, float_shares, short_float_pct, rvol, gap_pct, rsi, fecha = t

        change_class = "gap-positive" if change_pct and change_pct > 0 else "gap-negative"
        float_fmt = f"{float_shares/1e6:.1f}M" if float_shares else "N/A"
        price_fmt = f"${price:.2f}" if price is not None else "N/A"
        change_fmt = f"{change_pct:.2f}%" if change_pct is not None else "N/A"
        volume_fmt = f"{int(volume):,}" if volume is not None else "N/A"

        # Rango de fechas de datos intradía (desde / hasta)
        desde, hasta = db.obtener_rango_fechas_intradia(symbol)
        if desde and hasta:
            rango_fmt = f"{desde} → {hasta}"
        else:
            rango_fmt = "Sin intradía"

        filas_html += f"""
            <tr>
                <td><a href="/estudio/{symbol}" style="color:#00ff00;">{symbol}</a></td>
                <td>{price_fmt}</td>
                <td class="{change_class}">{change_fmt}</td>
                <td>{volume_fmt}</td>
                <td>{float_fmt}</td>
                <td>{short_float_pct if short_float_pct else 'N/A'}%</td>
                <td>{rvol if rvol else 'N/A'}x</td>
                <td style="font-size:12px;">{rango_fmt}</td>
                <td>
                    <div style="display:flex; gap:4px;">
                        <a href="/scanner/editar/{symbol}"
                           style="margin:0; padding:4px 8px; color:#ff9800; border:1px solid #ff9800; border-radius:3px; text-decoration:none; font-size:13px;">✏️</a>
                        <form method="POST" action="/scanner/eliminar" style="margin:0;"
                              onsubmit="return confirm('¿Eliminar {symbol} de la BD por completo?');">
                            <input type="hidden" name="symbol" value="{symbol}">
                            <button type="submit"
                                    style="margin:0; padding:4px 10px; color:#ff3355; border-color:#ff3355;">🗑</button>
                        </form>
                    </div>
                </td>
            </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Scanner - DDDreaM</title>
        <style>
            body {{ font-family: Arial; background-color: #1a1a1a; color: #00ff00; padding: 30px; }}
            table {{ border-collapse: collapse; width: 100%; max-width: 1200px; margin-bottom: 30px; }}
            th, td {{ border: 1px solid #00ff00; padding: 10px; text-align: left; }}
            th {{ background-color: #0a0a0a; }}
            .gap-positive {{ color: #00ff00; }}
            .gap-negative {{ color: #ff0000; }}
            form {{ margin-bottom: 15px; }}
            input[type=text], input[type=number] {{
                background: #0a0a0a; color: #00ff00;
                border: 1px solid #00ff00; padding: 6px 8px;
                width: 90px; border-radius: 3px;
            }}
            button {{
                background: #0a0a0a; color: #00ff00; border: 1px solid #00ff00;
                padding: 8px 16px; cursor: pointer; margin-left: 10px; border-radius: 3px;
            }}
            button:hover {{ background: #00ff00; color: #000; }}

            .criterios-panel {{
                border: 1px solid #00ff00; background: #0a0a0a;
                padding: 20px 25px; max-width: 1200px;
                margin-bottom: 30px; border-radius: 4px;
            }}
            .criterios-panel h2 {{
                margin: 0 0 18px 0; font-size: 1em;
                letter-spacing: 2px; color: #00ff00;
            }}
            .criterios-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
                gap: 14px 20px; margin-bottom: 18px;
            }}
            .criterio-field label {{
                display: block; font-size: 11px; color: #888;
                margin-bottom: 4px; letter-spacing: 1px;
            }}
            .criterio-field input {{ width: 100%; box-sizing: border-box; }}

            .acciones-extra {{
                display: flex; gap: 15px; flex-wrap: wrap;
                max-width: 1200px; margin-bottom: 25px;
            }}
            .acciones-extra form {{ margin: 0; }}
        </style>
    </head>
    <body>
        <h1>📊 DDDreaM Scanner</h1>
        <div style="display:flex; gap:20px; margin-bottom:15px;">
            <a href="/" style="color:#888; text-decoration:none; font-size:13px;">← Menú principal</a>
            <a href="/x" style="color:#1DA1F2; text-decoration:none; font-size:13px;">📱 Ver watchlist de X →</a>
        </div>
        {banner_reparacion}

        <!-- Panel de criterios -->
        <div class="criterios-panel">
            <h2>⚙ CRITERIOS DE BÚSQUEDA</h2>
            <form method="POST" action="/scanner/buscar">
                <div class="criterios-grid">
                    <div class="criterio-field">
                        <label>PRECIO MÍN ($)</label>
                        <input type="number" name="precio_min" value="1" min="0" step="0.5">
                    </div>
                    <div class="criterio-field">
                        <label>PRECIO MÁX ($)</label>
                        <input type="number" name="precio_max" value="20" min="0" step="0.5">
                    </div>
                    <div class="criterio-field">
                        <label>CAMBIO MÍN (%)</label>
                        <input type="number" name="cambio_min" value="5" min="0" step="1">
                    </div>
                    <div class="criterio-field">
                        <label>VOLUMEN MÍN</label>
                        <input type="number" name="volumen_min" value="500000" min="0" step="100000">
                    </div>
                    <div class="criterio-field">
                        <label>FLOAT MÁX (M)</label>
                        <input type="number" name="float_max" value="100" min="0" step="10">
                    </div>
                    <div class="criterio-field">
                        <label>RVOL MÍN (x)</label>
                        <input type="number" name="rvol_min" value="1.5" min="0" step="0.5">
                    </div>
                    <div class="criterio-field">
                        <label>SHORT FLOAT MÍN (%)</label>
                        <input type="number" name="short_min" value="" min="0" step="1">
                    </div>
                </div>
                <button type="submit">🔍 Lanzar Scanner</button>
            </form>
        </div>

        <!-- Acciones extra -->
        <div class="acciones-extra">
            <form method="POST" action="/scanner/agregar_x_lote" enctype="multipart/form-data"
                  style="display:flex; flex-direction:column; gap:10px; border:1px solid #1DA1F2; padding:14px 16px; border-radius:6px; max-width:560px;">
                <div style="color:#1DA1F2; font-size:12px; font-weight:bold;">📱 AÑADIR TICKERS DE UNA PUBLICACIÓN DE X (varios a la vez)</div>
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <input type="text" name="trader_x" placeholder="Trader (ej: Edu Trades)" required style="flex:1; min-width:150px;">
                    <input type="date" name="fecha_x" required style="background:#0a0a0a; color:#00ff00; border:1px solid #00ff00; padding:6px; border-radius:3px;">
                </div>
                <textarea name="tickers_x" placeholder="Un ticker por línea. Para nota individual: TICKER: tu nota&#10;Ej:&#10;GME&#10;AMC: rompió resistencia limpio&#10;BBBY"
                          required rows="4" style="background:#0a0a0a; color:#00ff00; border:1px solid #00ff00; padding:8px; border-radius:3px; font-family:monospace; resize:vertical;"></textarea>
                <input type="text" name="nota_general_x" placeholder="Nota general (opcional, para los que no tengan la suya propia)"
                       style="background:#0a0a0a; color:#00ff00; border:1px solid #00ff00; padding:6px; border-radius:3px;">
                <input type="file" name="imagen_x" accept="image/*" style="color:#00ff00;">
                <button type="submit" style="border-color:#1DA1F2; color:#1DA1F2; align-self:flex-start;">➕ Añadir todos</button>
            </form>
            <form method="POST" action="/scanner/actualizar">
                <button type="submit">🔄 Actualizar intradía ({len(tickers_seguimiento)} tickers)</button>
            </form>
            <form method="POST" action="/scanner/reparar_float"
                  onsubmit="return confirm('Esto puede tardar un minuto. ¿Reparar float/RVOL de todos los tickers que les falte?');">
                <button type="submit" style="border-color:#ff9800; color:#ff9800;">🔧 Reparar float/RVOL faltantes</button>
            </form>
        </div>

        <!-- Tabla -->
        <table>
            <tr>
                <th>Symbol</th><th>Precio</th><th>Cambio %</th><th>Volumen</th>
                <th>Float</th><th>Short Float</th><th>RVOL</th>
                <th>Datos (desde → hasta)</th><th>Acción</th>
            </tr>
            {filas_html if filas_html else '<tr><td colspan="9" style="text-align:center;color:#555;">Sin resultados aún — lanza el scanner</td></tr>'}
        </table>

    </body>
    </html>
    """
    return html

@app.route('/scanner/buscar', methods=['POST'])
def scanner_buscar():
    # Criterios del formulario con valores por defecto
    precio_min  = float(request.form.get('precio_min',  1))
    precio_max  = float(request.form.get('precio_max',  20))
    cambio_min  = int(float(request.form.get('cambio_min', 5)))
    volumen_min = int(float(request.form.get('volumen_min', 500_000)))

    float_max_str = request.form.get('float_max', '').strip()
    float_max_M   = float(float_max_str) if float_max_str else None

    rvol_min_str = request.form.get('rvol_min', '').strip()
    rvol_min     = float(rvol_min_str) if rvol_min_str else None

    short_min_str = request.form.get('short_min', '').strip()
    short_min     = float(short_min_str) if short_min_str else None

    # 1. Scan Finviz con criterios del usuario
    tickers = db.obtener_small_caps_finviz(
        cambio_min=cambio_min,
        volumen_min=volumen_min,
        precio_min=precio_min,
        precio_max=precio_max,
    )

    # 2. Filtros extra post-scan (float, RVOL, short float)
    if tickers and (float_max_M is not None or rvol_min is not None or short_min is not None):
        from datetime import date
        conn = db.conectar()
        cursor = conn.cursor()
        hoy = date.today()
        cursor.execute('''
            SELECT symbol, price, change_pct, volume, float_shares,
                   short_float_pct, rvol, gap_pct, atr, rsi
            FROM scanner_results WHERE fecha = ?
        ''', (hoy,))
        rows = cursor.fetchall()
        conn.close()

        keys = ["symbol", "price", "change_pct", "volume", "float_shares",
                "short_float_pct", "rvol", "gap_pct", "atr", "rsi"]
        tickers_info = [dict(zip(keys, r)) for r in rows]

        candidatos = []
        for tk in tickers_info:
            if float_max_M is not None and tk.get("float_shares"):
                if tk["float_shares"] / 1e6 > float_max_M:
                    continue
            if rvol_min is not None and tk.get("rvol"):
                if tk["rvol"] < rvol_min:
                    continue
            if short_min is not None and tk.get("short_float_pct"):
                if tk["short_float_pct"] < short_min:
                    continue
            candidatos.append(tk["symbol"])
        tickers = candidatos

    # 3. Descarga intradía para los que pasaron
    for tk in tickers:
        db.descargar_intradia_con_vwap(tk)

    return redirect('/scanner')

@app.route('/scanner/eliminar', methods=['POST'])
def scanner_eliminar():
    symbol = request.form.get('symbol', '').strip()
    if symbol:
        db.eliminar_ticker(symbol)
    return redirect('/scanner')


@app.route('/scanner/editar/<symbol>', methods=['GET', 'POST'])
def scanner_editar(symbol):
    symbol = symbol.upper()

    if request.method == 'POST':
        def parse_num(val):
            val = (val or '').strip()
            if not val:
                return None
            try:
                return float(val)
            except ValueError:
                return None

        float_m = parse_num(request.form.get('float_manual', ''))
        if float_m is not None:
            float_m = float_m * 1e6  # el usuario escribe en millones de acciones
        short_m = parse_num(request.form.get('short_manual', ''))
        rvol_m = parse_num(request.form.get('rvol_manual', ''))

        db.actualizar_metricas_manual(symbol, float_shares=float_m,
                                       short_float_pct=short_m, rvol=rvol_m)
        return redirect('/scanner')

    # GET: mostrar formulario con los valores actuales (si hay)
    conn = db.conectar()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT price, change_pct, volume, float_shares, short_float_pct, rvol
        FROM scanner_results WHERE symbol = ? ORDER BY fecha DESC LIMIT 1
    ''', (symbol,))
    info = cursor.fetchone()
    conn.close()

    float_actual = f"{info[3]/1e6:.2f}" if info and info[3] else ''
    short_actual = f"{info[4]:.2f}" if info and info[4] is not None else ''
    rvol_actual = f"{info[5]:.2f}" if info and info[5] is not None else ''

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Editar {symbol} - DDDreaM</title>
        <style>
            body {{ font-family:'Segoe UI',Arial; background:#0d0d0d; color:#00ff00; padding:30px; }}
            .caja {{ background:#141414; border:1px solid #ff9800; border-radius:8px; padding:24px; max-width:420px; }}
            label {{ display:block; font-size:12px; color:#888; margin:14px 0 6px 0; letter-spacing:1px; }}
            input {{ width:100%; box-sizing:border-box; background:#0a0a0a; color:#00ff00;
                    border:1px solid #00ff00; padding:8px; border-radius:4px; }}
            button {{ margin-top:20px; background:#ff9800; color:#000; border:none;
                     padding:10px 22px; border-radius:6px; font-weight:bold; cursor:pointer; }}
            a {{ color:#888; text-decoration:none; font-size:13px; }}
        </style>
    </head>
    <body>
        <a href="/scanner">← Volver al scanner</a>
        <div class="caja">
            <h2 style="margin-top:0;">✏️ Editar métricas de {symbol}</h2>
            <p style="color:#888; font-size:13px;">
                Último recurso: rellena solo lo que Finviz/yfinance no pudieron traer.
                Deja vacío lo que no sepas — no se sobrescribe si lo dejas en blanco.
            </p>
            <form method="POST">
                <label>FLOAT (en millones de acciones)</label>
                <input type="number" step="0.1" name="float_manual" value="{float_actual}" placeholder="Ej: 15.5">
                <label>SHORT FLOAT (%)</label>
                <input type="number" step="0.01" name="short_manual" value="{short_actual}" placeholder="Ej: 8.2">
                <label>RVOL (x)</label>
                <input type="number" step="0.01" name="rvol_manual" value="{rvol_actual}" placeholder="Ej: 3.5">
                <button type="submit">💾 Guardar</button>
            </form>
        </div>
    </body>
    </html>
    """
    return html


@app.route('/scanner/agregar_x_lote', methods=['POST'])
def scanner_agregar_x_lote():
    fecha = request.form.get('fecha_x', '').strip()
    trader = request.form.get('trader_x', '').strip()
    nota_general = request.form.get('nota_general_x', '').strip() or None
    tickers_raw = request.form.get('tickers_x', '').strip()

    # Guardar la imagen UNA sola vez — compartida por todos los tickers de esta publicación
    imagen_filename = None
    archivo = request.files.get('imagen_x')
    if archivo and archivo.filename:
        ext = os.path.splitext(archivo.filename)[1]
        nombre_seguro = secure_filename(f"{trader}_{fecha}{ext}")
        archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_seguro))
        imagen_filename = nombre_seguro

    if fecha and trader and tickers_raw:
        lineas = [l.strip() for l in tickers_raw.replace(',', '\n').split('\n') if l.strip()]
        symbols = []
        notas_individuales = {}
        for linea in lineas:
            if ':' in linea:
                sym, nota_ind = linea.split(':', 1)
                sym = sym.strip().upper()
                nota_ind = nota_ind.strip()
                if sym:
                    symbols.append(sym)
                    if nota_ind:
                        notas_individuales[sym] = nota_ind
            else:
                sym = linea.strip().upper()
                if sym:
                    symbols.append(sym)

        if symbols:
            db.agregar_lote_x(symbols, fecha, trader, imagen=imagen_filename,
                               notas_individuales=notas_individuales, nota_general=nota_general)

    return redirect('/scanner')


@app.route('/x')
def x_watchlist():
    vista = request.args.get('vista', 'ticker')  # ticker | dia
    filtro_datos = request.args.get('datos', 'todos')  # todos | con_datos | sin_datos

    def tab(clave, etiqueta):
        activo = 'active' if vista == clave else ''
        return f'<a href="/x?vista={clave}" class="tab {activo}">{etiqueta}</a>'
    tabs_html = tab('ticker', 'Por Ticker') + tab('dia', 'Por Publicación (día)')

    def filtro_link(clave, etiqueta, color):
        activo = 'active' if filtro_datos == clave else ''
        return f'<a href="/x?vista=ticker&datos={clave}" class="filtro-datos {activo}" style="border-color:{color}; color:{color};">{etiqueta}</a>'

    contenido = ""

    if vista == 'dia':
        publicaciones = db.obtener_x_agrupado_por_publicacion()
        if publicaciones:
            for pub in publicaciones:
                img_html = f'<img src="/static/x_uploads/{pub["imagen"]}" style="max-width:340px; border-radius:6px; margin:10px 0; display:block; border:1px solid #333;">' if pub['imagen'] else ''
                tickers_html = ""
                for t in pub['tickers']:
                    nota_t = f' — <span style="color:#ccc; font-style:italic;">"{t["nota"]}"</span>' if t['nota'] else ''
                    tickers_html += f'<div style="padding:4px 0;"><a href="/estudio/{t["symbol"]}" style="color:#00ff00; font-weight:bold; text-decoration:none;">{t["symbol"]}</a>{nota_t}</div>'
                contenido += f"""
                <div class="x-card">
                    <div class="x-card-header">
                        <span style="color:#1DA1F2; font-weight:bold;">{pub['trader']}</span>
                        <span style="color:#888; font-size:12px;">{pub['fecha']} · {len(pub['tickers'])} ticker(s)</span>
                    </div>
                    {img_html}
                    {tickers_html}
                </div>"""
        else:
            contenido = '<p style="color:#666;">Sin publicaciones registradas aún.</p>'
    else:
        filtro_bd = None if filtro_datos == 'todos' else filtro_datos
        datos = db.obtener_x_tickers_con_avistamientos(filtro_datos=filtro_bd)

        filtros_html = f"""
        <div style="display:flex; gap:8px; margin-bottom:20px;">
            {filtro_link('todos', 'Todos', '#888')}
            {filtro_link('con_datos', '✓ Con datos', '#26a69a')}
            {filtro_link('sin_datos', '⚠ Sin datos (buscar)', '#ff9800')}
        </div>"""
        contenido += filtros_html

        for item in datos:
            symbol = item['symbol']
            badge_datos = ('<span style="background:#0a2a0a; color:#26a69a; border:1px solid #26a69a; padding:2px 8px; border-radius:10px; font-size:11px;">✓ Datos completos</span>'
                            if item['tiene_datos'] else
                            f'<a href="/scanner/editar/{symbol}" style="background:#2a1a0a; color:#ff9800; border:1px solid #ff9800; padding:2px 8px; border-radius:10px; font-size:11px; text-decoration:none;">⚠ Sin datos — rellenar</a>')

            avist_html = ""
            for fecha, trader, imagen, nota in item['avistamientos']:
                img_html = f'<img src="/static/x_uploads/{imagen}" style="max-width:280px; border-radius:6px; margin-top:8px; display:block; border:1px solid #333;">' if imagen else ''
                nota_html = f'<div style="color:#ccc; font-style:italic; margin-top:6px;">"{nota}"</div>' if nota else ''
                avist_html += f"""
                <div class="avistamiento" style="display:block; padding:10px 0; border-bottom:1px solid #1a1a1a;">
                    <div style="display:flex; gap:15px;">
                        <span class="av-fecha">{fecha}</span>
                        <span class="av-trader">{trader}</span>
                    </div>
                    {nota_html}
                    {img_html}
                </div>"""

            contenido += f"""
            <div class="x-card">
                <div class="x-card-header">
                    <a href="/estudio/{symbol}" style="color:#00ff00; font-size:18px; font-weight:bold; text-decoration:none;">{symbol}</a>
                    <div style="display:flex; align-items:center; gap:10px;">
                        {badge_datos}
                        <span style="color:#888; font-size:12px;">{len(item['avistamientos'])} avistamiento(s)</span>
                    </div>
                </div>
                {avist_html}
            </div>"""
        if not datos:
            contenido += '<p style="color:#666;">Sin tickers para este filtro.</p>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>X Watchlist - DDDreaM</title>
        <style>
            body {{ font-family:'Segoe UI',Arial; background:#0d0d0d; color:#00ff00; padding:25px; }}
            h1 {{ margin:0 0 5px 0; }}
            .sub {{ color:#888; margin-bottom:15px; font-size:13px; }}
            .tabs {{ display:flex; gap:10px; margin:20px 0 25px 0; }}
            .tab {{ color:#888; border:1px solid #333; padding:8px 18px; border-radius:4px;
                    font-size:13px; text-decoration:none; }}
            .tab:hover {{ border-color:#1DA1F2; color:#1DA1F2; }}
            .tab.active {{ color:#1DA1F2; border-color:#1DA1F2; font-weight:bold; }}
            .filtro-datos {{ padding:6px 14px; border:1px solid; border-radius:14px; font-size:12px; text-decoration:none; }}
            .filtro-datos.active {{ font-weight:bold; background:#141414; }}
            .x-card {{ background:#141414; border:1px solid #1DA1F2; border-radius:8px;
                       padding:16px 20px; margin-bottom:14px; max-width:700px; }}
            .x-card-header {{ display:flex; justify-content:space-between; align-items:center;
                              margin-bottom:10px; padding-bottom:10px; border-bottom:1px solid #222; }}
            .avistamiento {{ display:flex; gap:15px; padding:6px 0; font-size:13px; color:#b2b5be; }}
            .av-fecha {{ color:#2962ff; min-width:90px; }}
            .av-trader {{ min-width:160px; }}
            a.volver {{ color:#888; text-decoration:none; font-size:13px; }}
        </style>
    </head>
    <body>
        <h1>📱 X (Twitter) — Tickers de los Grandes</h1>
        <div class="sub">Sub-base de casos de estudio: qué operaron y cuándo, para investigar después</div>
        <a href="/" style="color:#888; text-decoration:none; font-size:13px;">← Menú principal</a>

        <div class="tabs">{tabs_html}</div>

        {contenido}

        <br><a href="/scanner" class="volver">← Volver al scanner</a>
    </body>
    </html>
    """
    return html

@app.route('/scanner/actualizar', methods=['POST'])
def scanner_actualizar():
    tickers_seguimiento = db.obtener_tickers_seguimiento()
    for t in tickers_seguimiento:
        symbol = t[0]
        db.descargar_intradia_con_vwap(symbol)
    return redirect('/scanner')

@app.route('/scanner/reparar_float', methods=['POST'])
def scanner_reparar_float():
    reparados, sin_encontrar = db.reparar_datos_finviz_faltantes()
    return redirect(f'/scanner?reparados={reparados}&sin_encontrar={len(sin_encontrar)}')

@app.route('/estudio/<symbol>')
def estudio(symbol):
    intervalo = request.args.get('intervalo', '1m')
    en_vivo   = request.args.get('vivo', '0') == '1'
    modo      = request.args.get('modo', 'mio')  # 'mio' = mi grafico | 'tv' = TradingView

    symbol = symbol.upper()

    # ── Métricas de cabecera (siempre desde la BD, datos del scan) ──────
    conn = db.conectar()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT price, change_pct, volume, float_shares,
               short_float_pct, rvol, gap_pct, atr, rsi, fecha, inst_own
        FROM scanner_results
        WHERE symbol = ?
        ORDER BY fecha DESC LIMIT 1
    ''', (symbol,))
    info = cursor.fetchone()
    conn.close()

    # ── Construir el bloque del gráfico según el modo ───────────────────
    precio_vivo = None
    cambio_vivo = None

    if modo == 'tv':
        # Widget oficial de TradingView (sus datos, su gráfico)
        grafico_html = construir_widget_tradingview(symbol, intervalo)
    else:
        # Mi gráfico con mis datos (BD o en vivo)
        if en_vivo:
            datos = db.obtener_intradia_en_vivo(symbol, intervalo)
        else:
            datos = db.obtener_intradia(symbol, intervalo)

        if not datos:
            grafico_html = f"""
            <div style="padding:40px; text-align:center; color:#888;">
                <h3>No hay datos intradía para {symbol} ({intervalo})</h3>
                <a href="/estudio/{symbol}?intervalo={intervalo}&vivo=1" style="color:#00ff00;">
                    🔴 Intentar traer datos EN VIVO</a>
            </div>
            """
        else:
            grafico_html = construir_grafico(symbol, intervalo, datos)
            # Precio/cambio en vivo del último dato
            if en_vivo:
                cierres_dia = [d for d in datos if d[0][:10] == datos[-1][0][:10]]
                if cierres_dia:
                    precio_vivo = cierres_dia[-1][4]
                    open_dia    = cierres_dia[0][1]
                    if open_dia:
                        cambio_vivo = round(((precio_vivo - open_dia) / open_dia) * 100, 2)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{symbol} - DDDreaM</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background-color: #0d0d0d;
                color: #00ff00;
                padding: 25px;
            }}
            .top-bar {{
                display: flex; align-items: center; gap: 20px;
                margin-bottom: 20px; flex-wrap: wrap;
            }}
            h1 {{ margin: 0; font-size: 28px; }}
            .badge-vivo {{
                background: #ff0033; color: #fff; padding: 4px 12px;
                border-radius: 4px; font-size: 12px; font-weight: bold;
                letter-spacing: 1px; animation: pulse 1.5s infinite;
            }}
            @keyframes pulse {{ 0%,100% {{opacity:1;}} 50% {{opacity:0.4;}} }}
            .badge-bd {{
                background: #0a0a0a; color: #888; border: 1px solid #444;
                padding: 4px 12px; border-radius: 4px; font-size: 12px;
            }}
            .badge-tv {{
                background: #2962ff; color: #fff; padding: 4px 12px;
                border-radius: 4px; font-size: 12px; font-weight: bold;
            }}
            .controls {{
                display: flex; gap: 10px; margin-bottom: 22px;
                flex-wrap: wrap; align-items: center;
            }}
            .controls a {{
                color: #00ff00; text-decoration: none; border: 1px solid #00ff00;
                padding: 7px 16px; border-radius: 4px; font-size: 13px;
                transition: all .15s;
            }}
            .controls a:hover {{ background: #00ff00; color: #000; }}
            .controls a.active {{ background: #00ff00; color: #000; font-weight: bold; }}
            .controls a.vivo {{ border-color: #ff0033; color: #ff3355; }}
            .controls a.vivo:hover, .controls a.vivo.active {{ background: #ff0033; color: #fff; }}
            .controls a.tv {{ border-color: #2962ff; color: #5e85ff; }}
            .controls a.tv:hover, .controls a.tv.active {{ background: #2962ff; color: #fff; }}
            .controls .sep {{ color: #333; margin: 0 6px; }}
            .metrics {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 25px; }}
            .metric {{
                background: #141414; border: 1px solid #1f5f1f;
                padding: 12px 18px; border-radius: 6px; min-width: 110px;
            }}
            .metric-label {{ font-size: 10px; color: #888; margin-bottom: 6px; letter-spacing: 1px; }}
            .metric-value {{ font-size: 19px; font-weight: bold; }}
            .positive {{ color: #00ff00; }}
            .negative {{ color: #ff3355; }}
            .chart-wrap {{
                background: #131722; border: 1px solid #1f5f1f;
                border-radius: 6px; padding: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="top-bar">
            <h1>🎯 {symbol}</h1>
            {'<span class="badge-tv">📊 TRADINGVIEW</span>' if modo == 'tv' else ('<span class="badge-vivo">🔴 EN VIVO</span>' if en_vivo else '<span class="badge-bd">📁 DATOS GUARDADOS</span>')}
        </div>

        <div class="controls">
            <a href="/estudio/{symbol}?intervalo=1m&modo={modo}{'&vivo=1' if en_vivo else ''}"
               class="{'active' if intervalo == '1m' else ''}">1 min</a>
            <a href="/estudio/{symbol}?intervalo=5m&modo={modo}{'&vivo=1' if en_vivo else ''}"
               class="{'active' if intervalo == '5m' else ''}">5 min</a>
            <span class="sep">|</span>
            <a href="/estudio/{symbol}?intervalo={intervalo}&modo=mio"
               class="{'active' if modo == 'mio' and not en_vivo else ''}">📁 Guardado</a>
            <a href="/estudio/{symbol}?intervalo={intervalo}&modo=mio&vivo=1"
               class="vivo {'active' if modo == 'mio' and en_vivo else ''}">🔴 En vivo</a>
            <a href="/estudio/{symbol}?intervalo={intervalo}&modo=tv"
               class="tv {'active' if modo == 'tv' else ''}">📊 TradingView</a>
            <span class="sep">|</span>
            <a href="/scanner">← Scanner</a>
            <a href="/">🏠 Menú</a>
        </div>
    """

    if info:
        precio_mostrar = precio_vivo if (en_vivo and precio_vivo) else info[0]
        cambio_mostrar = cambio_vivo if (en_vivo and cambio_vivo is not None) else info[1]
        change_class = 'positive' if cambio_mostrar and cambio_mostrar > 0 else 'negative'

        def fmt(val, decimals=2, suffix=''):
            if val is None:
                return 'N/A'
            return f"{val:.{decimals}f}{suffix}"

        inst_own_val = info[10] if len(info) > 10 else None
        inst_color = 'negative' if (inst_own_val is not None and inst_own_val > 40) else 'positive'

        html += f"""
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">PRECIO {'(VIVO)' if en_vivo and precio_vivo else ''}</div>
                <div class="metric-value">${fmt(precio_mostrar)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">CAMBIO % {'(VIVO)' if en_vivo and cambio_vivo is not None else ''}</div>
                <div class="metric-value {change_class}">{fmt(cambio_mostrar)}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">VOLUMEN</div>
                <div class="metric-value">{f"{int(info[2]):,}" if info[2] is not None else "N/A"}</div>
            </div>
            <div class="metric">
                <div class="metric-label">FLOAT</div>
                <div class="metric-value">{fmt(info[3]/1e6 if info[3] else None)}M</div>
            </div>
            <div class="metric">
                <div class="metric-label">SHORT FLOAT</div>
                <div class="metric-value">{fmt(info[4])}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">RVOL</div>
                <div class="metric-value">{fmt(info[5])}x</div>
            </div>
            <div class="metric">
                <div class="metric-label">GAP</div>
                <div class="metric-value">{fmt(info[6])}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">RSI</div>
                <div class="metric-value">{fmt(info[8])}</div>
            </div>
            <div class="metric">
                <div class="metric-label">INSTITUCIONAL</div>
                <div class="metric-value {inst_color if inst_own_val is not None else ''}">{fmt(inst_own_val)}%</div>
            </div>
        </div>
        """

    # ── Noticias / catalizador (Finnhub) ────────────────────────────────
    noticias_guardadas = db.obtener_noticias_guardadas(symbol)
    noticias_html = ""
    for fecha_n, headline, resumen, fuente, link in noticias_guardadas:
        resumen_html = f'<div style="color:#888; font-size:12px; margin-top:4px;">{resumen[:200]}{"..." if len(resumen) > 200 else ""}</div>' if resumen else ''
        link_html = f'<a href="{link}" target="_blank" style="color:#2962ff; font-size:11px;">Leer fuente →</a>' if link else ''
        noticias_html += f"""
        <div style="padding:10px 0; border-bottom:1px solid #1a1a1a;">
            <div style="display:flex; gap:12px; align-items:baseline;">
                <span style="color:#2962ff; font-size:12px; min-width:85px;">{fecha_n}</span>
                <span style="font-weight:bold; font-size:13px;">{headline}</span>
            </div>
            {resumen_html}
            <div style="display:flex; gap:10px; margin-top:4px;">
                <span style="color:#666; font-size:11px;">{fuente}</span>
                {link_html}
            </div>
        </div>"""

    noticias_seccion = f"""
    <div class="chart-wrap" style="margin-top:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
            <h3 style="margin:0; font-size:15px; color:#00ff00;">📰 Noticias / Catalizador ({len(noticias_guardadas)} guardadas)</h3>
            <form method="POST" action="/estudio/{symbol}/noticias" style="margin:0;">
                <input type="hidden" name="intervalo" value="{intervalo}">
                <button type="submit" style="background:#0a0a0a; color:#2962ff; border:1px solid #2962ff; padding:6px 14px; border-radius:4px; cursor:pointer; font-size:12px;">🔎 Buscar noticias nuevas (Finnhub)</button>
            </form>
        </div>
        {noticias_html if noticias_html else '<p style="color:#666; font-size:13px;">Sin noticias guardadas aún — dale a "Buscar noticias nuevas".</p>'}
    </div>"""

    html += f"""
        <div class="chart-wrap">
            {grafico_html}
        </div>
        {noticias_seccion}
    </body>
    </html>
    """
    return html


@app.route('/estudio/<symbol>/noticias', methods=['POST'])
def estudio_buscar_noticias(symbol):
    symbol = symbol.upper()
    intervalo = request.form.get('intervalo', '1m')
    db.obtener_noticias_finnhub(symbol, dias_atras=30)
    return redirect(f'/estudio/{symbol}?intervalo={intervalo}')


def construir_grafico(symbol, intervalo, datos):
    """
    Gráfico Plotly estilo TradingView: velas sólidas arriba + volumen abajo.
    """
    fechas = [d[0] for d in datos]
    opens  = [d[1] for d in datos]
    highs  = [d[2] for d in datos]
    lows   = [d[3] for d in datos]
    closes = [d[4] for d in datos]
    vols   = [d[5] for d in datos]
    vwaps  = [d[6] for d in datos]
    # sesion puede no existir en datos viejos -> default 'regular'
    sesiones = [d[7] if len(d) > 7 and d[7] else 'regular' for d in datos]

    # ── Niveles por día: PM High/Low (premarket) y HOD/LOD (regular) ──────
    # Agrupamos índices por fecha (YYYY-MM-DD)
    from collections import defaultdict
    idx_por_dia = defaultdict(list)
    for i, dt in enumerate(fechas):
        idx_por_dia[dt[:10]].append(i)

    niveles_por_dia = {}  # fecha -> dict con pm_high, pm_low, hod, lod, x0, x1
    for dia, indices in idx_por_dia.items():
        pre_highs  = [highs[i] for i in indices if sesiones[i] == 'pre']
        pre_lows   = [lows[i]  for i in indices if sesiones[i] == 'pre']
        reg_highs  = [highs[i] for i in indices if sesiones[i] == 'regular']
        reg_lows   = [lows[i]  for i in indices if sesiones[i] == 'regular']

        niveles_por_dia[dia] = {
            'pm_high': max(pre_highs) if pre_highs else None,
            'pm_low':  min(pre_lows)  if pre_lows  else None,
            'hod':     max(reg_highs) if reg_highs else None,
            'lod':     min(reg_lows)  if reg_lows  else None,
            'x0':      fechas[indices[0]],
            'x1':      fechas[indices[-1]],
        }


    # Cortar VWAP entre días
    vwaps_cortado = []
    fechas_cortado = []
    for i, dt in enumerate(fechas):
        if i > 0 and dt[:10] != fechas[i-1][:10]:
            vwaps_cortado.append(None)
            fechas_cortado.append(dt)
        vwaps_cortado.append(vwaps[i])
        fechas_cortado.append(dt)

    verde = '#26a69a'
    rojo  = '#ef5350'
    colores_vol = [
        'rgba(38,166,154,0.5)' if closes[i] >= opens[i] else 'rgba(239,83,80,0.5)'
        for i in range(len(closes))
    ]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.02, row_heights=[0.78, 0.22]
    )

    fig.add_trace(go.Candlestick(
        x=fechas, open=opens, high=highs, low=lows, close=closes,
        name='Precio',
        increasing=dict(line=dict(color=verde, width=1), fillcolor=verde),
        decreasing=dict(line=dict(color=rojo, width=1), fillcolor=rojo),
        whiskerwidth=0.8,
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=fechas_cortado, y=vwaps_cortado,
        mode='lines', name='VWAP',
        line=dict(color='#2962ff', width=1.6)
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=fechas, y=vols, name='Volumen',
        marker=dict(color=colores_vol, line=dict(width=0)),
        showlegend=False
    ), row=2, col=1)

    # ── Dibujar niveles por día como segmentos horizontales ──────────────
    # Colores: PM High/Low en naranja, HOD en cian, LOD en morado
    config_niveles = [
        ('pm_high', '#ff9800', 'PM High'),
        ('pm_low',  '#ff9800', 'PM Low'),
        ('hod',     '#00bcd4', 'HOD'),
        ('lod',     '#ab47bc', 'LOD'),
    ]
    leyenda_mostrada = set()
    for dia, indices in idx_por_dia.items():
        niv = niveles_por_dia[dia]
        # Fechas (x) de todas las velas de este día, en orden
        fechas_dia = [fechas[i] for i in indices]
        for clave, color, etiqueta in config_niveles:
            valor = niv[clave]
            if valor is None:
                continue
            dash = 'dot' if clave.startswith('pm') else 'dash'
            mostrar_leg = etiqueta not in leyenda_mostrada
            if mostrar_leg:
                leyenda_mostrada.add(etiqueta)
            # Una línea horizontal con el mismo valor en cada vela del día
            fig.add_trace(go.Scatter(
                x=fechas_dia,
                y=[valor] * len(fechas_dia),
                mode='lines',
                name=etiqueta,
                legendgroup=etiqueta,
                showlegend=mostrar_leg,
                line=dict(color=color, width=1, dash=dash),
                opacity=0.6,
                hoverinfo='skip'
            ), row=1, col=1)

    bg = '#131722'
    grid = '#1e222d'

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor=bg, plot_bgcolor=bg,
        height=720, hovermode='x unified', dragmode='pan',
        bargap=0.15,
        margin=dict(l=10, r=60, t=30, b=30),
        legend=dict(orientation='h', yanchor='bottom', y=1.0,
                    xanchor='left', x=0, bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#b2b5be')),
        font=dict(color='#b2b5be'),
        xaxis_rangeslider_visible=False,
    )

    rangebreaks = [
        dict(bounds=["sat", "mon"]),
        dict(bounds=[16, 9.5], pattern="hour")
    ]

    velas_dia = 390 if intervalo == '1m' else 78
    rango_ini = [fechas[-min(len(fechas), velas_dia)], fechas[-1]]

    fig.update_xaxes(
        rangebreaks=rangebreaks, gridcolor=grid, zeroline=False,
        showspikes=True, spikemode='across', spikesnap='cursor',
        spikecolor='#787b86', spikethickness=1, spikedash='dot',
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1D", step="day", stepmode="backward"),
                dict(count=3, label="3D", step="day", stepmode="backward"),
                dict(count=5, label="5D", step="day", stepmode="backward"),
                dict(step="all", label="Todo")
            ],
            bgcolor='#1e222d', activecolor='#2962ff',
            font=dict(color='#b2b5be'), y=1.08
        ),
        range=rango_ini, row=1, col=1
    )
    fig.update_xaxes(
        rangebreaks=rangebreaks, gridcolor=grid, zeroline=False,
        range=rango_ini, row=2, col=1
    )
    fig.update_yaxes(gridcolor=grid, side='right', zeroline=False, row=1, col=1)
    fig.update_yaxes(gridcolor=grid, side='right', zeroline=False,
                     showticklabels=True, row=2, col=1)

    return fig.to_html(
        include_plotlyjs='cdn',
        div_id=f"graph-{symbol}",
        config={'scrollZoom': True, 'displaylogo': False}
    )


def construir_widget_tradingview(symbol, intervalo):
    """
    Widget oficial de TradingView incrustado (Advanced Chart).
    Datos y gráfico de TradingView. No usa la BD.
    """
    # TradingView usa intervalos: '1' = 1min, '5' = 5min
    tv_interval = '1' if intervalo == '1m' else '5'

    return f"""
    <div class="tradingview-widget-container" style="height:700px;width:100%;">
      <div id="tv_chart" style="height:100%;width:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{symbol}",
        "interval": "{tv_interval}",
        "timezone": "America/New_York",
        "theme": "dark",
        "style": "1",
        "locale": "es",
        "toolbar_bg": "#131722",
        "enable_publishing": false,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "studies": ["VWAP@tv-basicstudies", "Volume@tv-basicstudies"],
        "container_id": "tv_chart"
      }});
      </script>
    </div>
    <p style="color:#666; font-size:11px; margin-top:8px;">
      Gráfico proporcionado por TradingView. Datos de TradingView, no de tu base de datos.
    </p>
    """

@app.route('/analisis')
def analisis():
    tickers_seg = db.obtener_tickers_seguimiento()
    simbolos = [t[0] for t in tickers_seg]

    symbol = request.args.get('symbol', simbolos[0] if simbolos else '').upper()
    intervalo = request.args.get('intervalo', '5m')
    setup = request.args.get('setup', 'gapgo')  # gapgo | vwap | reciclaje

    # Selector de tickers (mantiene setup e intervalo)
    selector = ""
    for s in simbolos:
        activo = 'active' if s == symbol else ''
        selector += f'<a href="/analisis?symbol={s}&intervalo={intervalo}&setup={setup}" class="tk {activo}">{s}</a>'

    # Pestañas de setup (mantienen symbol e intervalo)
    def tab(clave, etiqueta):
        activo = 'active' if setup == clave else ''
        return f'<a href="/analisis?symbol={symbol}&intervalo={intervalo}&setup={clave}" class="tab {activo}">{etiqueta}</a>'

    tabs_html = tab('gapgo', 'Gap & Go') + tab('vwap', 'VWAP Bounce') + tab('reciclaje', 'Reciclaje')

    resumen = ""
    tabla = ""
    titulo = ""

    if symbol and setup == 'gapgo':
        titulo = f"📈 {symbol} — Gap & Go ({intervalo})"
        resultados = db.detectar_gap_and_go(symbol, intervalo)
        con_rotura = [r for r in resultados if r['rotura']]
        total = len(resultados)
        n_rot = len(con_rotura)
        if con_rotura:
            prom_15 = sum(r['mov_15'] for r in con_rotura) / n_rot
            prom_30 = sum(r['mov_30'] for r in con_rotura) / n_rot
            prom_60 = sum(r['mov_60'] for r in con_rotura) / n_rot
            prom_max = sum(r['max_dia_post'] for r in con_rotura) / n_rot
            verdes_30 = sum(1 for r in con_rotura if r['mov_30'] > 0)
            win_30 = (verdes_30 / n_rot) * 100
            resumen = f"""
            <div class="resumen">
                <div class="stat"><div class="stat-l">DÍAS ANALIZADOS</div><div class="stat-v">{total}</div></div>
                <div class="stat"><div class="stat-l">ROTURAS PM HIGH</div><div class="stat-v">{n_rot}</div></div>
                <div class="stat"><div class="stat-l">% ROTURA</div><div class="stat-v">{(n_rot/total*100):.0f}%</div></div>
                <div class="stat"><div class="stat-l">WIN RATE 30min</div><div class="stat-v {'pos' if win_30>=50 else 'neg'}">{win_30:.0f}%</div></div>
                <div class="stat"><div class="stat-l">PROM +15m</div><div class="stat-v {'pos' if prom_15>0 else 'neg'}">{prom_15:.2f}%</div></div>
                <div class="stat"><div class="stat-l">PROM +30m</div><div class="stat-v {'pos' if prom_30>0 else 'neg'}">{prom_30:.2f}%</div></div>
                <div class="stat"><div class="stat-l">PROM +60m</div><div class="stat-v {'pos' if prom_60>0 else 'neg'}">{prom_60:.2f}%</div></div>
                <div class="stat"><div class="stat-l">PROM MÁX POST</div><div class="stat-v pos">{prom_max:.2f}%</div></div>
            </div>
            """
            # ── Segmentación por RVOL (corte en 1.5x) ──
            con_rvol = [r for r in con_rotura if r.get('rvol') is not None]
            alto = [r for r in con_rvol if r['rvol'] > 1.5]
            bajo = [r for r in con_rvol if r['rvol'] <= 1.5]

            def stats_grupo(grupo):
                if not grupo:
                    return None
                n = len(grupo)
                return {
                    'n': n,
                    'prom_30': sum(r['mov_30'] for r in grupo) / n,
                    'prom_max': sum(r['max_dia_post'] for r in grupo) / n,
                    'win_30': sum(1 for r in grupo if r['mov_30'] > 0) / n * 100,
                }

            s_alto = stats_grupo(alto)
            s_bajo = stats_grupo(bajo)

            def fmt_grupo(nombre, s, color):
                if not s:
                    return f'<div class="seg-col"><div class="seg-titulo" style="color:{color}">{nombre}</div><div style="color:#666;">Sin datos</div></div>'
                return f"""
                <div class="seg-col">
                    <div class="seg-titulo" style="color:{color}">{nombre}</div>
                    <div class="seg-row">Días: <b>{s['n']}</b></div>
                    <div class="seg-row">Win 30m: <b class="{'pos' if s['win_30']>=50 else 'neg'}">{s['win_30']:.0f}%</b></div>
                    <div class="seg-row">Prom 30m: <b class="{'pos' if s['prom_30']>0 else 'neg'}">{s['prom_30']:.2f}%</b></div>
                    <div class="seg-row">Prom máx: <b class="pos">{s['prom_max']:.2f}%</b></div>
                </div>"""

            resumen += f"""
            <div class="segmentacion">
                <div class="seg-header">🔍 SEGMENTACIÓN POR RVOL (corte 1.5x)</div>
                <div class="seg-cols">
                    {fmt_grupo('RVOL ALTO (>1.5x)', s_alto, '#26a69a')}
                    {fmt_grupo('RVOL BAJO (≤1.5x)', s_bajo, '#888')}
                </div>
            </div>"""
        filas = ""
        for r in resultados:
            if not r['rotura']:
                filas += f"""
                <tr style="opacity:0.4;">
                    <td><a href="/estudio/{symbol}?intervalo={intervalo}" style="color:#888;">{r['fecha']}</a></td>
                    <td>{r['pm_high']}</td>
                    <td colspan="6" style="text-align:center;color:#666;">Sin rotura de PM High</td>
                </tr>"""
            else:
                def clase(v): return 'pos' if v and v > 0 else 'neg'
                filas += f"""
                <tr>
                    <td><a href="/estudio/{symbol}?intervalo={intervalo}" style="color:#00ff00;">{r['fecha']}</a></td>
                    <td>{r['pm_high']}</td>
                    <td>{r['hora_rotura']}</td>
                    <td>${r['precio_rotura']}</td>
                    <td class="{clase(r['mov_15'])}">{r['mov_15']}%</td>
                    <td class="{clase(r['mov_30'])}">{r['mov_30']}%</td>
                    <td class="{clase(r['mov_60'])}">{r['mov_60']}%</td>
                    <td class="pos">{r['max_dia_post']}%</td>
                    <td>{r['rvol']}x</td>
                </tr>"""
        tabla = f"""
        <table>
            <tr>
                <th>Fecha</th><th>PM High</th><th>Hora Rotura</th><th>Precio Rotura</th>
                <th>+15min</th><th>+30min</th><th>+60min</th><th>Máx Post</th><th>RVOL</th>
            </tr>
            {filas}
        </table>"""

    elif symbol and setup == 'vwap':
        titulo = f"🔵 {symbol} — VWAP Bounce ({intervalo})"
        resultados = db.detectar_vwap_bounce(symbol, intervalo)
        if resultados:
            total_reb = sum(r['n_rebotes'] for r in resultados)
            n_dias = len(resultados)
            prom_15 = sum(r['prom_15'] for r in resultados) / n_dias
            prom_30 = sum(r['prom_30'] for r in resultados) / n_dias
            prom_60 = sum(r['prom_60'] for r in resultados) / n_dias
            dias_verdes = sum(1 for r in resultados if r['prom_30'] > 0)
            win = (dias_verdes / n_dias) * 100
            resumen = f"""
            <div class="resumen">
                <div class="stat"><div class="stat-l">DÍAS CON REBOTES</div><div class="stat-v">{n_dias}</div></div>
                <div class="stat"><div class="stat-l">TOTAL REBOTES</div><div class="stat-v">{total_reb}</div></div>
                <div class="stat"><div class="stat-l">REBOTES/DÍA</div><div class="stat-v">{total_reb/n_dias:.1f}</div></div>
                <div class="stat"><div class="stat-l">WIN RATE 30min</div><div class="stat-v {'pos' if win>=50 else 'neg'}">{win:.0f}%</div></div>
                <div class="stat"><div class="stat-l">PROM +15m</div><div class="stat-v {'pos' if prom_15>0 else 'neg'}">{prom_15:.2f}%</div></div>
                <div class="stat"><div class="stat-l">PROM +30m</div><div class="stat-v {'pos' if prom_30>0 else 'neg'}">{prom_30:.2f}%</div></div>
                <div class="stat"><div class="stat-l">PROM +60m</div><div class="stat-v {'pos' if prom_60>0 else 'neg'}">{prom_60:.2f}%</div></div>
            </div>"""
            filas = ""
            for r in resultados:
                def clase(v): return 'pos' if v and v > 0 else 'neg'
                filas += f"""
                <tr>
                    <td><a href="/estudio/{symbol}?intervalo={intervalo}" style="color:#00ff00;">{r['fecha']}</a></td>
                    <td>{r['n_rebotes']}</td>
                    <td class="{clase(r['prom_15'])}">{r['prom_15']}%</td>
                    <td class="{clase(r['prom_30'])}">{r['prom_30']}%</td>
                    <td class="{clase(r['prom_60'])}">{r['prom_60']}%</td>
                </tr>"""
            tabla = f"""
            <table>
                <tr><th>Fecha</th><th>Nº Rebotes</th><th>Prom +15min</th><th>Prom +30min</th><th>Prom +60min</th></tr>
                {filas}
            </table>"""
        else:
            tabla = '<p style="color:#666;">Sin rebotes de VWAP detectados (necesita datos con sesión regular).</p>'

    elif symbol and setup == 'reciclaje':
        intervalo_rec = '1m'   # el reciclaje siempre en 1 minuto
        titulo = f"♻️ {symbol} — Reciclaje / Micro-impulsos ({intervalo_rec})"
        resultados = db.detectar_reciclaje(symbol, intervalo_rec)
        if resultados:
            total_imp = sum(r['n_impulsos'] for r in resultados)
            n_dias = len(resultados)
            subida_max = max(r['subida_max'] for r in resultados)
            subida_prom = sum(r['subida_prom'] for r in resultados) / n_dias
            resumen = f"""
            <div class="resumen">
                <div class="stat"><div class="stat-l">DÍAS CON IMPULSOS</div><div class="stat-v">{n_dias}</div></div>
                <div class="stat"><div class="stat-l">TOTAL IMPULSOS</div><div class="stat-v">{total_imp}</div></div>
                <div class="stat"><div class="stat-l">IMPULSOS/DÍA</div><div class="stat-v">{total_imp/n_dias:.1f}</div></div>
                <div class="stat"><div class="stat-l">SUBIDA MÁX</div><div class="stat-v pos">{subida_max}%</div></div>
                <div class="stat"><div class="stat-l">SUBIDA PROM</div><div class="stat-v pos">{subida_prom:.2f}%</div></div>
            </div>"""
            filas = ""
            for r in resultados:
                filas += f"""
                <tr>
                    <td><a href="/estudio/{symbol}?intervalo={intervalo}" style="color:#00ff00;">{r['fecha']}</a></td>
                    <td>{r['n_impulsos']}</td>
                    <td class="pos">{r['subida_max']}%</td>
                    <td class="pos">{r['subida_prom']}%</td>
                </tr>"""
            tabla = f"""
            <table>
                <tr><th>Fecha</th><th>Nº Micro-impulsos</th><th>Subida Máx</th><th>Subida Prom</th></tr>
                {filas}
            </table>"""
        else:
            tabla = '<p style="color:#666;">Sin micro-impulsos detectados.</p>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Análisis - DDDreaM</title>
        <style>
            body {{ font-family:'Segoe UI',Arial; background:#0d0d0d; color:#00ff00; padding:25px; }}
            h1 {{ margin:0 0 5px 0; }}
            .sub {{ color:#888; margin-bottom:20px; font-size:13px; }}
            .tickers {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:25px; }}
            .tk {{ color:#00ff00; text-decoration:none; border:1px solid #1f5f1f;
                   padding:6px 14px; border-radius:4px; font-size:13px; }}
            .tk:hover {{ background:#1f5f1f; }}
            .tk.active {{ background:#00ff00; color:#000; font-weight:bold; }}
            .tabs {{ display:flex; gap:10px; margin-bottom:20px; }}
            .tab {{ color:#888; border:1px solid #333; padding:8px 18px;
                    border-radius:4px; font-size:13px; text-decoration:none; }}
            .tab:hover {{ border-color:#00ff00; color:#00ff00; }}
            .tab.active {{ color:#00ff00; border-color:#00ff00; font-weight:bold; }}
            .resumen {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:25px; }}
            .stat {{ background:#141414; border:1px solid #1f5f1f; padding:12px 18px;
                     border-radius:6px; min-width:120px; }}
            .stat-l {{ font-size:10px; color:#888; margin-bottom:6px; letter-spacing:1px; }}
            .stat-v {{ font-size:20px; font-weight:bold; }}
            table {{ border-collapse:collapse; width:100%; max-width:1100px; }}
            th,td {{ border:1px solid #1f3f1f; padding:9px 12px; text-align:left; font-size:13px; }}
            th {{ background:#0a0a0a; color:#888; letter-spacing:1px; font-size:11px; }}
            .pos {{ color:#26a69a; }}
            .neg {{ color:#ef5350; }}
            a.volver {{ color:#888; text-decoration:none; font-size:13px; }}
        
            .pos {{ color:#26a69a; }}
            .neg {{ color:#ef5350; }}
            a.volver {{ color:#888; text-decoration:none; font-size:13px; }}
            .segmentacion {{ background:#141414; border:1px solid #2962ff; border-radius:6px; padding:18px; margin-bottom:25px; max-width:600px; }}
            .seg-header {{ color:#2962ff; font-size:12px; letter-spacing:1px; margin-bottom:14px; }}
            .seg-cols {{ display:flex; gap:30px; }}
            .seg-col {{ flex:1; }}
            .seg-titulo {{ font-weight:bold; margin-bottom:8px; font-size:13px; }}
            .seg-row {{ font-size:13px; margin-bottom:5px; color:#b2b5be; }}
        </style>
    </head>
    <body>
        <h1>🔬 Análisis</h1>
        <div class="sub">Tu Flash Research propio · Backtesting con tus datos guardados</div>

        <div class="tickers">{selector if selector else '<span style="color:#666;">No hay tickers.</span>'}</div>

        <div class="tabs">{tabs_html}</div>

        <h2 style="font-size:18px;">{titulo}</h2>
        {resumen}
        {tabla}

        <br><a href="/scanner" class="volver">← Volver al scanner</a> &nbsp;·&nbsp;
        <a href="/" class="volver">🏠 Menú principal</a>
    </body>
    </html>
    """
    return html

@app.route('/agregado')
def agregado():
    setup = request.args.get('setup', 'gapgo')
    intervalo = request.args.get('intervalo', '5m')

    # El reciclaje siempre corre en 1 minuto
    if setup == 'reciclaje':
        intervalo = '1m'

    datos = db.analisis_agregado(setup, intervalo)

    # Pestañas de setup
    def tab(clave, etiqueta):
        activo = 'active' if setup == clave else ''
        return f'<a href="/agregado?setup={clave}&intervalo={intervalo}" class="tab {activo}">{etiqueta}</a>'
    tabs_html = tab('gapgo', 'Gap & Go') + tab('vwap', 'VWAP Bounce') + tab('reciclaje', 'Reciclaje')

    nombres = {'gapgo': 'Gap & Go', 'vwap': 'VWAP Bounce', 'reciclaje': 'Reciclaje'}

    # Filtro según el tipo de setup
    if setup == 'reciclaje':
        con_datos = [d for d in datos if d.get('max_post') is not None]
    else:
        con_datos = [d for d in datos if d.get('rvol_30') is not None and d.get('mov_30') is not None]

    panel = ""
    tabla_top = ""

    # ── Reciclaje tiene su propio panel (impulsos, no R) ──
    if setup == 'reciclaje' and con_datos:
        total_imp = sum(d.get('n_eventos', 0) for d in con_datos)
        n_dias = len(con_datos)
        subida_max_global = max(d['max_post'] for d in con_datos)
        subida_prom_global = sum(d.get('subida_prom', 0) for d in con_datos) / n_dias

        # Ranking de tickers con más impulsos (los mejores para reciclar)
        from collections import defaultdict
        imp_por_ticker = defaultdict(lambda: {'impulsos': 0, 'dias': 0, 'sub_max': 0})
        for d in con_datos:
            t = imp_por_ticker[d['symbol']]
            t['impulsos'] += d.get('n_eventos', 0)
            t['dias'] += 1
            t['sub_max'] = max(t['sub_max'], d['max_post'])

        ranking = sorted(imp_por_ticker.items(),
                         key=lambda x: x[1]['impulsos'], reverse=True)[:25]

        filas_rank = ""
        for sym, info in ranking:
            imp_dia = info['impulsos'] / info['dias'] if info['dias'] else 0
            filas_rank += f"""
            <tr>
                <td><a href="/analisis?symbol={sym}&setup=reciclaje" style="color:#00ff00;">{sym}</a></td>
                <td>{info['impulsos']}</td>
                <td>{info['dias']}</td>
                <td>{imp_dia:.1f}</td>
                <td class="pos">{info['sub_max']:.2f}%</td>
            </tr>"""

        panel = f"""
        <div class="segmentacion">
            <div class="seg-header">♻️ RECICLAJE GLOBAL · {n_dias} días-ticker con impulsos</div>
            <div class="seg-cols">
                <div class="seg-col">
                    <div class="seg-big pos">{total_imp}</div>
                    <div class="seg-sub">micro-impulsos totales</div>
                </div>
                <div class="seg-col">
                    <div class="seg-big">{total_imp/n_dias:.1f}</div>
                    <div class="seg-sub">impulsos por día-ticker</div>
                </div>
                <div class="seg-col">
                    <div class="seg-big pos">{subida_prom_global:.2f}%</div>
                    <div class="seg-sub">subida media · máx {subida_max_global:.1f}%</div>
                </div>
            </div>
        </div>
        <h3 style="font-size:15px;margin-top:30px;">🏆 Top 25 tickers para reciclaje (más micro-impulsos)</h3>
        <table>
            <tr><th>Ticker</th><th>Total impulsos</th><th>Días</th><th>Impulsos/día</th><th>Subida máx</th></tr>
            {filas_rank}
        </table>"""
        tabla_top = ""  # ya está todo en panel

    elif con_datos:
        # ── Segmentación global por RVOL 30min (corte 1.5x) ──
        alto = [d for d in con_datos if d['rvol_30'] > 1.5]
        bajo = [d for d in con_datos if d['rvol_30'] <= 1.5]

        def stats(grupo):
            if not grupo:
                return None
            n = len(grupo)
            return {
                'n': n,
                'win30': sum(1 for d in grupo if d['mov_30'] > 0) / n * 100,
                'prom30': sum(d['mov_30'] for d in grupo) / n,
                'prommax': sum(d['max_post'] for d in grupo if d['max_post'] is not None) / max(1, sum(1 for d in grupo if d['max_post'] is not None)),
            }

        s_alto = stats(alto)
        s_bajo = stats(bajo)

        def col(nombre, s, color):
            if not s:
                return f'<div class="seg-col"><div class="seg-titulo" style="color:{color}">{nombre}</div><div style="color:#666;">Sin datos</div></div>'
            return f"""
            <div class="seg-col">
                <div class="seg-titulo" style="color:{color}">{nombre}</div>
                <div class="seg-big {'pos' if s['win30']>=50 else 'neg'}">{s['win30']:.0f}%</div>
                <div class="seg-sub">win rate 30min · {s['n']} casos</div>
                <div class="seg-row">Prom 30m: <b class="{'pos' if s['prom30']>0 else 'neg'}">{s['prom30']:.2f}%</b></div>
                <div class="seg-row">Prom máx: <b class="pos">{s['prommax']:.2f}%</b></div>
            </div>"""

        # Diferencia de edge
        edge_txt = ""
        if s_alto and s_bajo:
            dif_win = s_alto['win30'] - s_bajo['win30']
            dif_prom = s_alto['prom30'] - s_bajo['prom30']
            color_edge = '#26a69a' if dif_win > 0 else '#ef5350'
            edge_txt = f"""
            <div class="edge-box" style="border-color:{color_edge}">
                <b style="color:{color_edge}">📊 EDGE RVOL ALTO vs BAJO</b><br>
                Diferencia win rate: <b class="{'pos' if dif_win>0 else 'neg'}">{dif_win:+.0f} puntos</b> ·
                Diferencia prom 30m: <b class="{'pos' if dif_prom>0 else 'neg'}">{dif_prom:+.2f}%</b>
            </div>"""

        panel = f"""
        <div class="segmentacion">
            <div class="seg-header">🔍 SEGMENTACIÓN GLOBAL POR RVOL 30min (corte 1.5x) · {len(con_datos)} casos totales</div>
            <div class="seg-cols">
                {col('RVOL ALTO (>1.5x)', s_alto, '#26a69a')}
                {col('RVOL BAJO (≤1.5x)', s_bajo, '#888')}
            </div>
            {edge_txt}
        </div>"""

        # ── Tabla: mejores casos por máximo movimiento ──
        ordenados = sorted(con_datos, key=lambda d: d['max_post'] if d['max_post'] is not None else -999, reverse=True)[:30]
        filas = ""
        for d in ordenados:
            def clase(v): return 'pos' if v and v > 0 else 'neg'
            filas += f"""
            <tr>
                <td><a href="/estudio/{d['symbol']}?intervalo={intervalo}" style="color:#00ff00;">{d['symbol']}</a></td>
                <td>{d['fecha']}</td>
                <td>{d['rvol_30']}x</td>
                <td class="{clase(d['mov_15'])}">{d['mov_15']}%</td>
                <td class="{clase(d['mov_30'])}">{d['mov_30']}%</td>
                <td class="{clase(d['mov_60'])}">{d['mov_60']}%</td>
                <td class="pos">{d['max_post']}%</td>
            </tr>"""
        tabla_top = f"""
        <h3 style="font-size:15px;margin-top:30px;">🏆 Top 30 casos por movimiento máximo</h3>
        <table>
            <tr><th>Ticker</th><th>Fecha</th><th>RVOL 30m</th><th>+15m</th><th>+30m</th><th>+60m</th><th>Máx Post</th></tr>
            {filas}
        </table>"""
    else:
        panel = '<p style="color:#666;">No hay casos con datos suficientes para este setup.</p>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vista Agregada - DDDreaM</title>
        <style>
            body {{ font-family:'Segoe UI',Arial; background:#0d0d0d; color:#00ff00; padding:25px; }}
            h1 {{ margin:0 0 5px 0; }}
            .sub {{ color:#888; margin-bottom:20px; font-size:13px; }}
            .tabs {{ display:flex; gap:10px; margin-bottom:25px; }}
            .tab {{ color:#888; border:1px solid #333; padding:8px 18px; border-radius:4px;
                    font-size:13px; text-decoration:none; }}
            .tab:hover {{ border-color:#00ff00; color:#00ff00; }}
            .tab.active {{ color:#00ff00; border-color:#00ff00; font-weight:bold; }}
            .segmentacion {{ background:#141414; border:1px solid #2962ff; border-radius:8px;
                             padding:22px; margin-bottom:25px; max-width:700px; }}
            .seg-header {{ color:#2962ff; font-size:12px; letter-spacing:1px; margin-bottom:20px; }}
            .seg-cols {{ display:flex; gap:40px; }}
            .seg-col {{ flex:1; }}
            .seg-titulo {{ font-weight:bold; margin-bottom:10px; font-size:13px; }}
            .seg-big {{ font-size:38px; font-weight:bold; line-height:1; }}
            .seg-sub {{ font-size:11px; color:#888; margin:6px 0 14px 0; }}
            .seg-row {{ font-size:13px; margin-bottom:5px; color:#b2b5be; }}
            .edge-box {{ margin-top:20px; padding:14px; border:1px solid; border-radius:6px;
                        background:#0a0a0a; font-size:13px; }}
            table {{ border-collapse:collapse; width:100%; max-width:900px; }}
            th,td {{ border:1px solid #1f3f1f; padding:8px 11px; text-align:left; font-size:13px; }}
            th {{ background:#0a0a0a; color:#888; letter-spacing:1px; font-size:11px; }}
            .pos {{ color:#26a69a; }}
            .neg {{ color:#ef5350; }}
            a.volver {{ color:#888; text-decoration:none; font-size:13px; }}
        </style>
    </head>
    <body>
        <h1>🌐 Vista Agregada</h1>
        <div class="sub">Todos los tickers juntos · Validación de edge con muestra completa</div>

        <div class="tabs">{tabs_html}</div>

        <h2 style="font-size:18px;">{nombres[setup]} — Todos los tickers ({intervalo})</h2>
        {panel}
        {tabla_top}

        <br><a href="/analisis" class="volver">← Análisis por ticker</a> &nbsp;·&nbsp;
        <a href="/scanner" class="volver">Scanner</a> &nbsp;·&nbsp;
        <a href="/" class="volver">🏠 Menú principal</a>
    </body>
    </html>
    """
    return html

@app.route('/backtest')
def backtest():
    setup = request.args.get('setup', 'gapgo')  # gapgo | frd | overext
    COSTE_R = 0.1  # coste estimado por trade (slippage + comisión) en R

    def tab(clave, etiqueta):
        activo = 'active' if setup == clave else ''
        return f'<a href="/backtest?setup={clave}" class="tab {activo}">{etiqueta}</a>'
    tabs_html = (tab('gapgo', '📈 Gap & Go (LONG)') +
                 tab('frd', '📉 First Red Day (SHORT)') +
                 tab('overext', '📉 Overext. Gap Down (SHORT)') +
                 tab('vwap', '🔵 VWAP Bounce (LONG)') +
                 tab('reciclaje', '♻️ Reciclaje (LONG)'))

    controles_html = ""
    bloque_barrido = ""
    panel = ""
    titulo_sub = ""

    # ══════════════════════════════════════════════════════════════
    #  GAP & GO (LONG)
    # ══════════════════════════════════════════════════════════════
    if setup == 'gapgo':
        titulo_sub = 'Mide si el Gap & Go (long) gana dinero · Ajusta stop y target'
        stop_pct = float(request.args.get('stop', 2.0))
        target_pct = float(request.args.get('target', 5.0))
        intervalo = '5m'
        solo_hora = request.args.get('hora_alta') == '1'

        hacer_barrido = request.args.get('barrido') == '1'
        solo_alto = request.args.get('rvol_alto') == '1'

        if hacer_barrido:
            top = db.barrido_r_gapgo('5m', stop_min=2.0, stop_max=7.0, target_max=7.0,
                                      paso=0.5, solo_rvol_alto=solo_alto, solo_primera_hora=solo_hora)[:5]
            filas_b = ""
            for i, r in enumerate(top, 1):
                r_neto = r['r_esperado'] - COSTE_R
                signo = 'pos' if r_neto > 0 else 'neg'
                filas_b += f"""
                <tr>
                    <td>{i}</td>
                    <td>{r['stop']}%</td>
                    <td>{r['target']}%</td>
                    <td>{r['ratio']}:1</td>
                    <td>{r['r_esperado']:+.3f}R</td>
                    <td class="{signo}"><b>{r_neto:+.3f}R</b></td>
                    <td>{r['win_rate']}%</td>
                    <td>{r['n']}</td>
                    <td><a href="/backtest?setup=gapgo&stop={r['stop']}&target={r['target']}&hora_alta={'1' if solo_hora else '0'}" style="color:#2962ff;">ver detalle →</a></td>
                </tr>"""
            filtros_txt = []
            if solo_alto: filtros_txt.append('RVOL alto')
            if solo_hora: filtros_txt.append('9:30-10:00')
            etiqueta_filtros = f"({' + '.join(filtros_txt)})" if filtros_txt else "(sin filtros)"
            bloque_barrido = f"""
            <div class="segmentacion" style="border-color:#ff9800; max-width:900px;">
                <div class="seg-header" style="color:#ff9800;">🏆 TOP 5 COMBINACIONES {etiqueta_filtros}</div>
                <table>
                    <tr><th>#</th><th>Stop</th><th>Target</th><th>Ratio</th><th>R bruto</th><th>R neto</th><th>Win rate</th><th>Trades</th><th></th></tr>
                    {filas_b}
                </table>
            </div>"""

        trades = db.r_agregado_gapgo(intervalo, stop_pct, target_pct, solo_primera_hora=solo_hora)
        con_rvol = [t for t in trades if t.get('rvol_30') is not None]

        if trades:
            n = len(trades)
            total_r = sum(t['resultado_r'] for t in trades)
            wins = sum(1 for t in trades if t['resultado_r'] > 0)
            r_esp = total_r / n
            r_esp_neto = r_esp - COSTE_R
            ratio = target_pct / stop_pct

            alto = [t for t in con_rvol if t['rvol_30'] > 1.5]
            bajo = [t for t in con_rvol if t['rvol_30'] <= 1.5]

            def stats_r(grupo):
                if not grupo:
                    return None
                ng = len(grupo)
                tr = sum(t['resultado_r'] for t in grupo)
                w = sum(1 for t in grupo if t['resultado_r'] > 0)
                return {'n': ng, 'total': tr, 'esp': tr/ng, 'win': w/ng*100}

            s_alto = stats_r(alto)
            s_bajo = stats_r(bajo)

            def col_r(nombre, s, color):
                if not s:
                    return f'<div class="seg-col"><div class="seg-titulo" style="color:{color}">{nombre}</div><div style="color:#666;">Sin datos</div></div>'
                esp_neto = s['esp'] - COSTE_R
                signo = 'pos' if esp_neto > 0 else 'neg'
                return f"""
                <div class="seg-col">
                    <div class="seg-titulo" style="color:{color}">{nombre}</div>
                    <div class="seg-big {signo}">{esp_neto:+.3f}R</div>
                    <div class="seg-sub">R NETO · {s['n']} trades</div>
                    <div class="seg-row">Win rate: <b>{s['win']:.0f}%</b></div>
                    <div class="seg-row">R total: <b class="{signo}">{s['total']:+.1f}R</b></div>
                </div>"""

            edge_r = ""
            if s_alto and s_bajo:
                dif = s_alto['esp'] - s_bajo['esp']
                cedge = '#26a69a' if dif > 0 else '#ef5350'
                edge_r = f"""
                <div class="edge-box" style="border-color:{cedge}">
                    <b style="color:{cedge}">📊 ¿El RVOL mejora el R?</b><br>
                    RVOL alto da <b class="{'pos' if dif>0 else 'neg'}">{dif:+.3f}R</b> más por trade que RVOL bajo.
                    {'✓ El RVOL es un filtro útil aquí.' if dif > 0.02 else '✗ El RVOL apenas aporta con estos parámetros.'}
                </div>"""

            signo_g = 'pos' if r_esp > 0 else 'neg'
            etiqueta_hora = ' · filtro 9:30-10:00 activo' if solo_hora else ''
            panel = f"""
            <div class="segmentacion" style="border-color:{'#26a69a' if r_esp>0 else '#ef5350'};">
                <div class="seg-header">💰 RESULTADO GLOBAL · Gap & Go · {n} trades{etiqueta_hora}</div>
                <div style="display:flex; gap:40px; align-items:baseline; margin-bottom:10px;">
                    <div>
                        <div class="seg-big {signo_g}" style="font-size:48px;">{r_esp:+.3f}R</div>
                        <div class="seg-sub">R bruto por trade · ratio {ratio:.1f}:1</div>
                    </div>
                    <div>
                        <div class="seg-big {'pos' if r_esp_neto>0 else 'neg'}" style="font-size:48px;">{r_esp_neto:+.3f}R</div>
                        <div class="seg-sub">R NETO (tras coste {COSTE_R}R)</div>
                    </div>
                    <div>
                        <div style="font-size:24px;">{wins/n*100:.0f}%</div>
                        <div class="seg-sub">win rate</div>
                    </div>
                </div>
                <div style="font-size:13px; color:{'#26a69a' if r_esp>0 else '#ef5350'};">
                    → {'GANA dinero a largo plazo' if r_esp_neto > 0 else 'PIERDE dinero a largo plazo'}
                </div>
            </div>

            <div class="segmentacion">
                <div class="seg-header">🔍 SEGMENTACIÓN POR RVOL 30min (corte 1.5x)</div>
                <div class="seg-cols">
                    {col_r('RVOL ALTO (>1.5x)', s_alto, '#26a69a')}
                    {col_r('RVOL BAJO (≤1.5x)', s_bajo, '#888')}
                </div>
                {edge_r}
            </div>"""
        else:
            panel = '<p style="color:#666;">No hay trades para estos parámetros.</p>'

        controles_html = f"""
        <div class="controles">
            <form method="GET" action="/backtest">
                <input type="hidden" name="setup" value="gapgo">
                <div class="ctrl-row">
                    <div>
                        <label>STOP (%)</label>
                        <input type="number" name="stop" value="{stop_pct}" step="0.5" min="0.5">
                    </div>
                    <div>
                        <label>TARGET (%)</label>
                        <input type="number" name="target" value="{target_pct}" step="0.5" min="0.5">
                    </div>
                    <button type="submit">Calcular</button>
                </div>
                <label style="display:block; margin-top:14px; font-size:13px; color:#b2b5be;">
                    <input type="checkbox" name="hora_alta" value="1" {"checked" if solo_hora else ""}>
                    Solo primera media hora (9:30-10:00) — el filtro validado como clave del edge
                </label>
            </form>
        </div>
        <div class="controles" style="border-color:#2962ff;">
            <div style="font-size:13px; color:#b2b5be; margin-bottom:12px;">
                🔄 <b>Barrido automático:</b> prueba todas las combinaciones (stop 2-7%, target 0.5-7%)
                y muestra las 5 mejores. <span style="color:#ff9800;">⚠ Tarda ~1 minuto.</span>
            </div>
            <form method="GET" action="/backtest">
                <input type="hidden" name="setup" value="gapgo">
                <input type="hidden" name="barrido" value="1">
                <label style="display:inline-block; margin-right:15px;">
                    <input type="checkbox" name="rvol_alto" value="1" checked> Solo RVOL alto (>1.5x)
                </label>
                <label style="display:inline-block; margin-right:15px;">
                    <input type="checkbox" name="hora_alta" value="1" {"checked" if solo_hora else ""}>
                    Solo primera media hora (9:30-10:00)
                </label>
                <button type="submit">🚀 Lanzar barrido</button>
            </form>
        </div>"""

    # ══════════════════════════════════════════════════════════════
    #  FIRST RED DAY (SHORT)
    # ══════════════════════════════════════════════════════════════
    elif setup == 'frd':
        titulo_sub = 'Mide si el First Red Day (short) gana dinero · Sobreextensión + primer día rojo'
        primera_vez = 'min_verdes' not in request.args
        min_verdes = int(request.args.get('min_verdes', 2))
        tipo_rojo = request.args.get('tipo_rojo', 'ambas')
        vol_decreciente = True if primera_vez else (request.args.get('vol_decreciente') == '1')
        sobreext_min = float(request.args.get('sobreext_min', 30))
        entrada_frd = request.args.get('entrada_frd', 'pierde_open')
        stop_pct = float(request.args.get('stop', 3.0))
        target_pct = float(request.args.get('target', 6.0))

        if request.args.get('barrido') == '1':
            top = db.barrido_r_first_red_day(min_verdes, tipo_rojo, vol_decreciente, sobreext_min,
                                              entrada_frd, stop_min=2.0, stop_max=7.0, target_max=10.0, paso=0.5)[:5]
            filas_b = ""
            for i, r in enumerate(top, 1):
                r_neto = r['r_esperado'] - COSTE_R
                signo = 'pos' if r_neto > 0 else 'neg'
                filas_b += f"""
                <tr>
                    <td>{i}</td>
                    <td>{r['stop']}%</td>
                    <td>{r['target']}%</td>
                    <td>{r['ratio']}:1</td>
                    <td>{r['r_esperado']:+.3f}R</td>
                    <td class="{signo}"><b>{r_neto:+.3f}R</b></td>
                    <td>{r['win_rate']}%</td>
                    <td>{r['n']}</td>
                    <td><a href="/backtest?setup=frd&stop={r['stop']}&target={r['target']}&min_verdes={min_verdes}&tipo_rojo={tipo_rojo}&vol_decreciente={'1' if vol_decreciente else '0'}&sobreext_min={sobreext_min}&entrada_frd={entrada_frd}" style="color:#2962ff;">ver detalle →</a></td>
                </tr>"""
            bloque_barrido = f"""
            <div class="segmentacion" style="border-color:#ff9800; max-width:900px;">
                <div class="seg-header" style="color:#ff9800;">🏆 TOP 5 STOP/TARGET (resto de filtros fijos)</div>
                <table>
                    <tr><th>#</th><th>Stop</th><th>Target</th><th>Ratio</th><th>R bruto</th><th>R neto</th><th>Win rate</th><th>Trades</th><th></th></tr>
                    {filas_b}
                </table>
            </div>"""

        trades = db.r_agregado_first_red_day(min_verdes, tipo_rojo, vol_decreciente, sobreext_min,
                                              entrada_frd, stop_pct, target_pct)
        if trades:
            n = len(trades)
            total_r = sum(t['resultado_r'] for t in trades)
            wins = sum(1 for t in trades if t['resultado_r'] > 0)
            r_esp = total_r / n
            r_esp_neto = r_esp - COSTE_R
            ratio = target_pct / stop_pct
            signo_g = 'pos' if r_esp > 0 else 'neg'
            panel = f"""
            <div class="segmentacion" style="border-color:{'#26a69a' if r_esp>0 else '#ef5350'};">
                <div class="seg-header">💰 RESULTADO GLOBAL · First Red Day SHORT · {n} trades</div>
                <div style="display:flex; gap:40px; align-items:baseline; margin-bottom:10px;">
                    <div>
                        <div class="seg-big {signo_g}" style="font-size:48px;">{r_esp:+.3f}R</div>
                        <div class="seg-sub">R bruto por trade · ratio {ratio:.1f}:1</div>
                    </div>
                    <div>
                        <div class="seg-big {'pos' if r_esp_neto>0 else 'neg'}" style="font-size:48px;">{r_esp_neto:+.3f}R</div>
                        <div class="seg-sub">R NETO (tras coste {COSTE_R}R)</div>
                    </div>
                    <div>
                        <div style="font-size:24px;">{wins/n*100:.0f}%</div>
                        <div class="seg-sub">win rate</div>
                    </div>
                </div>
                <div style="font-size:13px; color:{'#26a69a' if r_esp_neto>0 else '#ef5350'};">
                    → {'GANA dinero tras costes' if r_esp_neto > 0 else 'PIERDE dinero tras costes'}
                </div>
            </div>"""
        else:
            panel = '<p style="color:#666;">No hay señales de First Red Day con estos filtros (prueba a bajar la sobreextensión mínima).</p>'

        def opt(val, actual, txt):
            return f'<option value="{val}" {"selected" if val==actual else ""}>{txt}</option>'

        controles_html = f"""
        <div class="controles" style="max-width:900px;">
            <form method="GET" action="/backtest">
                <input type="hidden" name="setup" value="frd">
                <div class="ctrl-row" style="flex-wrap:wrap; gap:16px;">
                    <div>
                        <label>DÍAS VERDES PREVIOS</label>
                        <select name="min_verdes" style="background:#0a0a0a;color:#00ff00;border:1px solid #00ff00;padding:8px;border-radius:4px;">
                            {opt(1, min_verdes, '1')}{opt(2, min_verdes, '2')}{opt(3, min_verdes, '3')}
                        </select>
                    </div>
                    <div>
                        <label>TIPO DE ROJO</label>
                        <select name="tipo_rojo" style="background:#0a0a0a;color:#00ff00;border:1px solid #00ff00;padding:8px;border-radius:4px;">
                            {opt('apertura', tipo_rojo, 'Cierra bajo apertura')}
                            {opt('cierre_ant', tipo_rojo, 'Cierra bajo cierre anterior')}
                            {opt('ambas', tipo_rojo, 'Ambas')}
                        </select>
                    </div>
                    <div>
                        <label>SOBREEXT. MÍN (%)</label>
                        <input type="number" name="sobreext_min" value="{sobreext_min}" step="5" style="width:90px;">
                    </div>
                    <div>
                        <label>ENTRADA</label>
                        <select name="entrada_frd" style="background:#0a0a0a;color:#00ff00;border:1px solid #00ff00;padding:8px;border-radius:4px;">
                            {opt('pierde_open', entrada_frd, 'Pierde el open (D+1)')}
                            {opt('dia_siguiente', entrada_frd, 'Apertura D+1')}
                            {opt('pierde_vwap', entrada_frd, 'Pierde VWAP (D+1)')}
                        </select>
                    </div>
                    <div>
                        <label>STOP (%)</label>
                        <input type="number" name="stop" value="{stop_pct}" step="0.5" style="width:80px;">
                    </div>
                    <div>
                        <label>TARGET (%)</label>
                        <input type="number" name="target" value="{target_pct}" step="0.5" style="width:80px;">
                    </div>
                    <div style="align-self:flex-end;">
                        <button type="submit">Calcular</button>
                    </div>
                </div>
                <label style="display:block; margin-top:14px; font-size:13px; color:#b2b5be;">
                    <input type="checkbox" name="vol_decreciente" value="1" {"checked" if vol_decreciente else ""}>
                    Exigir volumen decreciente vs el día anterior
                </label>
            </form>
        </div>
        <div class="controles" style="border-color:#ff9800; max-width:900px;">
            <div style="font-size:13px; color:#b2b5be; margin-bottom:12px;">
                🔄 <b>Barrido automático:</b> prueba stop/target manteniendo el resto de filtros fijos.
                <span style="color:#ff9800;">⚠ Puede tardar.</span>
            </div>
            <form method="GET" action="/backtest">
                <input type="hidden" name="setup" value="frd">
                <input type="hidden" name="barrido" value="1">
                <input type="hidden" name="min_verdes" value="{min_verdes}">
                <input type="hidden" name="tipo_rojo" value="{tipo_rojo}">
                <input type="hidden" name="vol_decreciente" value="{'1' if vol_decreciente else '0'}">
                <input type="hidden" name="sobreext_min" value="{sobreext_min}">
                <input type="hidden" name="entrada_frd" value="{entrada_frd}">
                <button type="submit">🚀 Lanzar barrido</button>
            </form>
        </div>"""

    # ══════════════════════════════════════════════════════════════
    #  OVEREXTENDED GAP DOWN (SHORT)
    # ══════════════════════════════════════════════════════════════
    elif setup == 'overext':
        titulo_sub = 'Mide si el Overextended Gap Down (short) gana dinero · Sobreextensión + gap down'
        gap_min = float(request.args.get('gap_min', 2.0))
        dias_sob = int(request.args.get('dias_sob', 2))
        sobreext_min = float(request.args.get('sobreext_min_ov', 50))
        entrada_ov = request.args.get('entrada_ov', 'rebote_resist')
        stop_pct = float(request.args.get('stop', 3.0))
        target_pct = float(request.args.get('target', 6.0))

        if request.args.get('barrido') == '1':
            top = db.barrido_r_overext_gap_down(gap_min, dias_sob, sobreext_min, entrada_ov,
                                                 stop_min=2.0, stop_max=7.0, target_max=10.0, paso=0.5)[:5]
            filas_b = ""
            for i, r in enumerate(top, 1):
                r_neto = r['r_esperado'] - COSTE_R
                signo = 'pos' if r_neto > 0 else 'neg'
                filas_b += f"""
                <tr>
                    <td>{i}</td>
                    <td>{r['stop']}%</td>
                    <td>{r['target']}%</td>
                    <td>{r['ratio']}:1</td>
                    <td>{r['r_esperado']:+.3f}R</td>
                    <td class="{signo}"><b>{r_neto:+.3f}R</b></td>
                    <td>{r['win_rate']}%</td>
                    <td>{r['n']}</td>
                    <td><a href="/backtest?setup=overext&stop={r['stop']}&target={r['target']}&gap_min={gap_min}&dias_sob={dias_sob}&sobreext_min_ov={sobreext_min}&entrada_ov={entrada_ov}" style="color:#2962ff;">ver detalle →</a></td>
                </tr>"""
            bloque_barrido = f"""
            <div class="segmentacion" style="border-color:#ff9800; max-width:900px;">
                <div class="seg-header" style="color:#ff9800;">🏆 TOP 5 STOP/TARGET (resto de filtros fijos)</div>
                <table>
                    <tr><th>#</th><th>Stop</th><th>Target</th><th>Ratio</th><th>R bruto</th><th>R neto</th><th>Win rate</th><th>Trades</th><th></th></tr>
                    {filas_b}
                </table>
            </div>"""

        trades = db.r_agregado_overext_gap_down(gap_min, dias_sob, sobreext_min, entrada_ov, stop_pct, target_pct)
        if trades:
            n = len(trades)
            total_r = sum(t['resultado_r'] for t in trades)
            wins = sum(1 for t in trades if t['resultado_r'] > 0)
            r_esp = total_r / n
            r_esp_neto = r_esp - COSTE_R
            ratio = target_pct / stop_pct
            signo_g = 'pos' if r_esp > 0 else 'neg'
            panel = f"""
            <div class="segmentacion" style="border-color:{'#26a69a' if r_esp>0 else '#ef5350'};">
                <div class="seg-header">💰 RESULTADO GLOBAL · Overextended Gap Down SHORT · {n} trades</div>
                <div style="display:flex; gap:40px; align-items:baseline; margin-bottom:10px;">
                    <div>
                        <div class="seg-big {signo_g}" style="font-size:48px;">{r_esp:+.3f}R</div>
                        <div class="seg-sub">R bruto por trade · ratio {ratio:.1f}:1</div>
                    </div>
                    <div>
                        <div class="seg-big {'pos' if r_esp_neto>0 else 'neg'}" style="font-size:48px;">{r_esp_neto:+.3f}R</div>
                        <div class="seg-sub">R NETO (tras coste {COSTE_R}R)</div>
                    </div>
                    <div>
                        <div style="font-size:24px;">{wins/n*100:.0f}%</div>
                        <div class="seg-sub">win rate</div>
                    </div>
                </div>
                <div style="font-size:13px; color:{'#26a69a' if r_esp_neto>0 else '#ef5350'};">
                    → {'GANA dinero tras costes' if r_esp_neto > 0 else 'PIERDE dinero tras costes'}
                </div>
            </div>"""
        else:
            panel = '<p style="color:#666;">No hay señales de Overextended Gap Down con estos filtros.</p>'

        def opt2(val, actual, txt):
            return f'<option value="{val}" {"selected" if str(val)==str(actual) else ""}>{txt}</option>'

        controles_html = f"""
        <div class="controles" style="max-width:900px;">
            <form method="GET" action="/backtest">
                <input type="hidden" name="setup" value="overext">
                <div class="ctrl-row" style="flex-wrap:wrap; gap:16px;">
                    <div>
                        <label>GAP MÍN (%)</label>
                        <input type="number" name="gap_min" value="{gap_min}" step="0.5" style="width:80px;">
                    </div>
                    <div>
                        <label>DÍAS SOBREEXT.</label>
                        <select name="dias_sob" style="background:#0a0a0a;color:#00ff00;border:1px solid #00ff00;padding:8px;border-radius:4px;">
                            {opt2(2, dias_sob, '2')}{opt2(3, dias_sob, '3')}
                        </select>
                    </div>
                    <div>
                        <label>SOBREEXT. MÍN (%)</label>
                        <input type="number" name="sobreext_min_ov" value="{sobreext_min}" step="5" style="width:90px;">
                    </div>
                    <div>
                        <label>ENTRADA</label>
                        <select name="entrada_ov" style="background:#0a0a0a;color:#00ff00;border:1px solid #00ff00;padding:8px;border-radius:4px;">
                            {opt2('rebote_resist', entrada_ov, 'Rebote a resistencia')}
                            {opt2('pierde_open', entrada_ov, 'Pierde el open')}
                        </select>
                    </div>
                    <div>
                        <label>STOP (%)</label>
                        <input type="number" name="stop" value="{stop_pct}" step="0.5" style="width:80px;">
                    </div>
                    <div>
                        <label>TARGET (%)</label>
                        <input type="number" name="target" value="{target_pct}" step="0.5" style="width:80px;">
                    </div>
                    <div style="align-self:flex-end;">
                        <button type="submit">Calcular</button>
                    </div>
                </div>
            </form>
        </div>
        <div class="controles" style="border-color:#ff9800; max-width:900px;">
            <div style="font-size:13px; color:#b2b5be; margin-bottom:12px;">
                🔄 <b>Barrido automático:</b> prueba stop/target manteniendo el resto de filtros fijos.
                <span style="color:#ff9800;">⚠ Puede tardar.</span>
            </div>
            <form method="GET" action="/backtest">
                <input type="hidden" name="setup" value="overext">
                <input type="hidden" name="barrido" value="1">
                <input type="hidden" name="gap_min" value="{gap_min}">
                <input type="hidden" name="dias_sob" value="{dias_sob}">
                <input type="hidden" name="sobreext_min_ov" value="{sobreext_min}">
                <input type="hidden" name="entrada_ov" value="{entrada_ov}">
                <button type="submit">🚀 Lanzar barrido</button>
            </form>
        </div>"""

    # ══════════════════════════════════════════════════════════════
    #  VWAP BOUNCE (LONG)
    # ══════════════════════════════════════════════════════════════
    elif setup == 'vwap':
        titulo_sub = 'Mide si el VWAP Bounce (long) gana dinero · Rebote en VWAP con cierre por encima'
        stop_pct = float(request.args.get('stop', 2.0))
        target_pct = float(request.args.get('target', 4.0))

        if request.args.get('barrido') == '1':
            top = db.barrido_r_vwap_bounce('5m', stop_min=1.0, stop_max=5.0, target_max=10.0, paso=0.5)[:5]
            filas_b = ""
            for i, r in enumerate(top, 1):
                r_neto = r['r_esperado'] - COSTE_R
                signo = 'pos' if r_neto > 0 else 'neg'
                filas_b += f"""
                <tr>
                    <td>{i}</td>
                    <td>{r['stop']}%</td>
                    <td>{r['target']}%</td>
                    <td>{r['ratio']}:1</td>
                    <td>{r['r_esperado']:+.3f}R</td>
                    <td class="{signo}"><b>{r_neto:+.3f}R</b></td>
                    <td>{r['win_rate']}%</td>
                    <td>{r['n']}</td>
                    <td><a href="/backtest?setup=vwap&stop={r['stop']}&target={r['target']}" style="color:#2962ff;">ver detalle →</a></td>
                </tr>"""
            bloque_barrido = f"""
            <div class="segmentacion" style="border-color:#ff9800; max-width:900px;">
                <div class="seg-header" style="color:#ff9800;">🏆 TOP 5 STOP/TARGET</div>
                <table>
                    <tr><th>#</th><th>Stop</th><th>Target</th><th>Ratio</th><th>R bruto</th><th>R neto</th><th>Win rate</th><th>Trades</th><th></th></tr>
                    {filas_b}
                </table>
            </div>"""

        trades = db.r_agregado_vwap_bounce('5m', stop_pct, target_pct)
        if trades:
            n = len(trades)
            total_r = sum(t['resultado_r'] for t in trades)
            wins = sum(1 for t in trades if t['resultado_r'] > 0)
            r_esp = total_r / n
            r_esp_neto = r_esp - COSTE_R
            ratio = target_pct / stop_pct
            signo_g = 'pos' if r_esp > 0 else 'neg'
            panel = f"""
            <div class="segmentacion" style="border-color:{'#26a69a' if r_esp>0 else '#ef5350'};">
                <div class="seg-header">💰 RESULTADO GLOBAL · VWAP Bounce LONG · {n} trades</div>
                <div style="display:flex; gap:40px; align-items:baseline; margin-bottom:10px;">
                    <div>
                        <div class="seg-big {signo_g}" style="font-size:48px;">{r_esp:+.3f}R</div>
                        <div class="seg-sub">R bruto por trade · ratio {ratio:.1f}:1</div>
                    </div>
                    <div>
                        <div class="seg-big {'pos' if r_esp_neto>0 else 'neg'}" style="font-size:48px;">{r_esp_neto:+.3f}R</div>
                        <div class="seg-sub">R NETO (tras coste {COSTE_R}R)</div>
                    </div>
                    <div>
                        <div style="font-size:24px;">{wins/n*100:.0f}%</div>
                        <div class="seg-sub">win rate</div>
                    </div>
                </div>
                <div style="font-size:13px; color:{'#26a69a' if r_esp_neto>0 else '#ef5350'};">
                    → {'GANA dinero tras costes' if r_esp_neto > 0 else 'PIERDE dinero tras costes'}
                </div>
            </div>"""
        else:
            panel = '<p style="color:#666;">No hay rebotes de VWAP detectados.</p>'

        controles_html = f"""
        <div class="controles">
            <form method="GET" action="/backtest">
                <input type="hidden" name="setup" value="vwap">
                <div class="ctrl-row">
                    <div>
                        <label>STOP (%)</label>
                        <input type="number" name="stop" value="{stop_pct}" step="0.5" min="0.5">
                    </div>
                    <div>
                        <label>TARGET (%)</label>
                        <input type="number" name="target" value="{target_pct}" step="0.5" min="0.5">
                    </div>
                    <button type="submit">Calcular</button>
                </div>
            </form>
        </div>
        <div class="controles" style="border-color:#ff9800;">
            <div style="font-size:13px; color:#b2b5be; margin-bottom:12px;">
                🔄 <b>Barrido automático:</b> prueba stop/target (1-5% / 0.5-10%).
                <span style="color:#ff9800;">⚠ Puede tardar.</span>
            </div>
            <form method="GET" action="/backtest">
                <input type="hidden" name="setup" value="vwap">
                <input type="hidden" name="barrido" value="1">
                <button type="submit">🚀 Lanzar barrido</button>
            </form>
        </div>"""

    # ══════════════════════════════════════════════════════════════
    #  RECICLAJE (LONG)
    # ══════════════════════════════════════════════════════════════
    elif setup == 'reciclaje':
        titulo_sub = 'Mide si el Reciclaje (long, scalping) gana dinero · Micro-impulsos en 1 minuto'
        stop_pct = float(request.args.get('stop', 1.0))
        target_pct = float(request.args.get('target', 2.0))
        umbral = float(request.args.get('umbral', 1.0))

        if request.args.get('barrido') == '1':
            top = db.barrido_r_reciclaje(stop_min=0.5, stop_max=3.0, target_max=6.0, paso=0.5, umbral=umbral)[:5]
            filas_b = ""
            for i, r in enumerate(top, 1):
                r_neto = r['r_esperado'] - COSTE_R
                signo = 'pos' if r_neto > 0 else 'neg'
                filas_b += f"""
                <tr>
                    <td>{i}</td>
                    <td>{r['stop']}%</td>
                    <td>{r['target']}%</td>
                    <td>{r['ratio']}:1</td>
                    <td>{r['r_esperado']:+.3f}R</td>
                    <td class="{signo}"><b>{r_neto:+.3f}R</b></td>
                    <td>{r['win_rate']}%</td>
                    <td>{r['n']}</td>
                    <td><a href="/backtest?setup=reciclaje&stop={r['stop']}&target={r['target']}&umbral={umbral}" style="color:#2962ff;">ver detalle →</a></td>
                </tr>"""
            bloque_barrido = f"""
            <div class="segmentacion" style="border-color:#ff9800; max-width:900px;">
                <div class="seg-header" style="color:#ff9800;">🏆 TOP 5 STOP/TARGET (scalping)</div>
                <table>
                    <tr><th>#</th><th>Stop</th><th>Target</th><th>Ratio</th><th>R bruto</th><th>R neto</th><th>Win rate</th><th>Trades</th><th></th></tr>
                    {filas_b}
                </table>
            </div>"""

        trades = db.r_agregado_reciclaje(stop_pct, target_pct, umbral)
        if trades:
            n = len(trades)
            total_r = sum(t['resultado_r'] for t in trades)
            wins = sum(1 for t in trades if t['resultado_r'] > 0)
            r_esp = total_r / n
            r_esp_neto = r_esp - COSTE_R
            ratio = target_pct / stop_pct
            signo_g = 'pos' if r_esp > 0 else 'neg'
            panel = f"""
            <div class="segmentacion" style="border-color:{'#26a69a' if r_esp>0 else '#ef5350'};">
                <div class="seg-header">💰 RESULTADO GLOBAL · Reciclaje LONG · {n} micro-trades</div>
                <div style="display:flex; gap:40px; align-items:baseline; margin-bottom:10px;">
                    <div>
                        <div class="seg-big {signo_g}" style="font-size:48px;">{r_esp:+.3f}R</div>
                        <div class="seg-sub">R bruto por trade · ratio {ratio:.1f}:1</div>
                    </div>
                    <div>
                        <div class="seg-big {'pos' if r_esp_neto>0 else 'neg'}" style="font-size:48px;">{r_esp_neto:+.3f}R</div>
                        <div class="seg-sub">R NETO (tras coste {COSTE_R}R)</div>
                    </div>
                    <div>
                        <div style="font-size:24px;">{wins/n*100:.0f}%</div>
                        <div class="seg-sub">win rate</div>
                    </div>
                </div>
                <div style="font-size:13px; color:{'#26a69a' if r_esp_neto>0 else '#ef5350'};">
                    → {'GANA dinero tras costes' if r_esp_neto > 0 else 'PIERDE dinero tras costes'}
                </div>
                <div style="font-size:11px; color:#666; margin-top:10px;">
                    ⚠ Coste {COSTE_R}R fijo puede pesar mucho en scalping — con tantas operaciones,
                    el coste real por trade (comisión + slippage) probablemente sea distinto. Interpreta con cautela.
                </div>
            </div>"""
        else:
            panel = '<p style="color:#666;">No hay micro-impulsos detectados con este umbral.</p>'

        controles_html = f"""
        <div class="controles">
            <form method="GET" action="/backtest">
                <input type="hidden" name="setup" value="reciclaje">
                <div class="ctrl-row">
                    <div>
                        <label>STOP (%)</label>
                        <input type="number" name="stop" value="{stop_pct}" step="0.25" min="0.25">
                    </div>
                    <div>
                        <label>TARGET (%)</label>
                        <input type="number" name="target" value="{target_pct}" step="0.25" min="0.25">
                    </div>
                    <div>
                        <label>UMBRAL IMPULSO (%)</label>
                        <input type="number" name="umbral" value="{umbral}" step="0.25" min="0.25">
                    </div>
                    <button type="submit">Calcular</button>
                </div>
            </form>
        </div>
        <div class="controles" style="border-color:#ff9800;">
            <div style="font-size:13px; color:#b2b5be; margin-bottom:12px;">
                🔄 <b>Barrido automático:</b> prueba stop/target pequeños (0.5-3% / 0.5-6%), scalping.
                <span style="color:#ff9800;">⚠ Puede tardar, hay muchas señales por ticker.</span>
            </div>
            <form method="GET" action="/backtest">
                <input type="hidden" name="setup" value="reciclaje">
                <input type="hidden" name="barrido" value="1">
                <input type="hidden" name="umbral" value="{umbral}">
                <button type="submit">🚀 Lanzar barrido</button>
            </form>
        </div>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Backtest R - DDDreaM</title>
        <style>
            body {{ font-family:'Segoe UI',Arial; background:#0d0d0d; color:#00ff00; padding:25px; }}
            h1 {{ margin:0 0 5px 0; }}
            .sub {{ color:#888; margin-bottom:20px; font-size:13px; }}
            .tabs {{ display:flex; gap:10px; margin-bottom:22px; flex-wrap:wrap; }}
            .tab {{ color:#888; border:1px solid #333; padding:8px 18px; border-radius:4px;
                    font-size:13px; text-decoration:none; }}
            .tab:hover {{ border-color:#00ff00; color:#00ff00; }}
            .tab.active {{ color:#00ff00; border-color:#00ff00; font-weight:bold; }}
            .controles {{ background:#141414; border:1px solid #1f5f1f; border-radius:8px;
                          padding:20px; margin-bottom:20px; }}
            .controles label {{ font-size:11px; color:#888; letter-spacing:1px; display:block; margin-bottom:5px; }}
            .controles input, .controles select {{ background:#0a0a0a; color:#00ff00; border:1px solid #00ff00;
                                padding:8px; border-radius:4px; font-size:14px; }}
            .controles button {{ background:#00ff00; color:#000; border:none; padding:9px 20px;
                                 border-radius:4px; cursor:pointer; font-weight:bold; }}
            .ctrl-row {{ display:flex; gap:25px; align-items:flex-end; }}
            .segmentacion {{ background:#141414; border:1px solid #2962ff; border-radius:8px;
                             padding:22px; margin-bottom:25px; max-width:700px; }}
            .seg-header {{ color:#2962ff; font-size:12px; letter-spacing:1px; margin-bottom:18px; }}
            .seg-cols {{ display:flex; gap:40px; }}
            .seg-col {{ flex:1; }}
            .seg-titulo {{ font-weight:bold; margin-bottom:10px; font-size:13px; }}
            .seg-big {{ font-size:38px; font-weight:bold; line-height:1; }}
            .seg-sub {{ font-size:11px; color:#888; margin:6px 0 14px 0; }}
            .seg-row {{ font-size:13px; margin-bottom:5px; color:#b2b5be; }}
            .edge-box {{ margin-top:20px; padding:14px; border:1px solid; border-radius:6px;
                        background:#0a0a0a; font-size:13px; }}
            table {{ border-collapse:collapse; width:100%; }}
            th, td {{ border:1px solid #1f3f1f; padding:8px 11px; text-align:left; font-size:13px; }}
            th {{ background:#0a0a0a; color:#888; letter-spacing:1px; font-size:11px; }}
            .pos {{ color:#26a69a; }}
            .neg {{ color:#ef5350; }}
            a.volver {{ color:#888; text-decoration:none; font-size:13px; }}
        </style>
    </head>
    <body>
        <h1>💰 Backtest R</h1>
        <div class="sub">{titulo_sub}</div>

        <div class="tabs">{tabs_html}</div>

        {controles_html}
        {bloque_barrido}
        {panel}

        <br><a href="/agregado" class="volver">← Vista agregada</a> &nbsp;·&nbsp;
        <a href="/scanner" class="volver">Scanner</a> &nbsp;·&nbsp;
        <a href="/" class="volver">🏠 Menú principal</a>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    app.run(debug=True, port=5000)