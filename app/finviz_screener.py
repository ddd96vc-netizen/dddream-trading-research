"""
Lector propio del screener de Finviz -- reemplaza a finvizfinance.

POR QUE EXISTE
En octubre 2026 Finviz rediseñó la tabla del screener (ahora 'fv-table'
con atributos data-ticker / data-column-id). finvizfinance 1.5.0 (la
última versión publicada) ya no la reconoce y devuelve None sin dar
error: la rutina "se conectaba" pero guardaba 0 tickers desde el 16/10.

Además, este lector lee el ticker de data-ticker, así que ya no hace
falta el parche de la "letra inicial duplicada" (esa letra era el logo
de relleno que Finviz pinta delante del ticker, no un bug de pd.concat).

Devuelve un DataFrame con los MISMOS nombres de columna que usaba
finvizfinance ('Ticker', 'Price', 'Change', 'Float', 'Inst Own'...),
con los valores como texto tal cual los muestra Finviz ('10.69%',
'651.95M', '5,344,134'). OJO: los porcentajes vienen en PORCENTAJE
(10.69), no en fracción (0.1069) como los daba finvizfinance.
"""
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://finviz.com/screener.ashx"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"}

VISTAS = {'overview': 111, 'ownership': 131, 'technical': 171}

# data-column-id de Finviz -> nombre de columna que usaba finvizfinance
COLUMNAS = {
    'ticker': 'Ticker', 'company': 'Company', 'sector': 'Sector', 'industry': 'Industry',
    'country': 'Country', 'marketCap': 'Market Cap', 'PE': 'P/E', 'price': 'Price',
    'change': 'Change', 'volume': 'Volume', 'sharesOutstanding2': 'Outstanding',
    'sharesFloat': 'Float', 'insiderOwn': 'Insider Own', 'insiderTrans': 'Insider Trans',
    'instOwn': 'Inst Own', 'instTrans': 'Inst Trans', 'shortInterestShare': 'Short Float',
    'shortInterestRatio': 'Short Ratio', 'averageVolume': 'Avg Volume', 'beta': 'Beta',
    'averageTrueRange': 'ATR', 'sma20': 'SMA20', 'sma50': 'SMA50', 'sma200': 'SMA200',
    'high52w': '52W High', 'low52w': '52W Low', 'rsi': 'RSI', 'changeopen': 'from Open',
    'gap': 'Gap',
}

# Nombre de filtro (los mismos textos que aceptaba finvizfinance) -> prefijo de URL
FILTROS = {
    'Price': ('sh_price', {
        'Under $1': 'u1', 'Under $2': 'u2', 'Under $3': 'u3', 'Under $5': 'u5',
        'Under $10': 'u10', 'Under $20': 'u20', 'Over $1': 'o1', 'Over $2': 'o2',
        'Over $5': 'o5', '$1 to $5': '1to5', '$1 to $10': '1to10', '$1 to $20': '1to20',
        '$5 to $10': '5to10', '$5 to $20': '5to20', '$10 to $20': '10to20'}),
    'Change': ('ta_change', {**{f'Up {n}%': f'u{n}' for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20)},
                             **{f'Down {n}%': f'd{n}' for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20)},
                             'Up': 'u', 'Down': 'd'}),
    'Current Volume': ('sh_curvol', {
        'Over 50K': 'o50', 'Over 100K': 'o100', 'Over 200K': 'o200', 'Over 300K': 'o300',
        'Over 400K': 'o400', 'Over 500K': 'o500', 'Over 750K': 'o750', 'Over 1M': 'o1000',
        'Over 2M': 'o2000', 'Over 5M': 'o5000', 'Over 10M': 'o10000', 'Over 20M': 'o20000'}),
    'Market Cap.': ('cap', {
        'Mid ($2bln to $10bln)': 'mid', 'Small ($300mln to $2bln)': 'small',
        'Micro ($50mln to $300mln)': 'micro', 'Nano (under $50mln)': 'nano',
        '-Mid (under $10bln)': 'midunder', '-Small (under $2bln)': 'smallunder',
        '-Micro (under $300mln)': 'microunder'}),
}


def _codigo_filtros(filters_dict):
    partes = []
    for nombre, valor in (filters_dict or {}).items():
        if valor in (None, '', 'Any'):
            continue
        if nombre not in FILTROS or valor not in FILTROS[nombre][1]:
            # Fallar fuerte: un filtro mal escrito NO debe aplicarse en silencio
            raise ValueError(f"Filtro de Finviz no soportado: {nombre!r} = {valor!r}")
        prefijo, opciones = FILTROS[nombre]
        partes.append(f"{prefijo}_{opciones[valor]}")
    return ",".join(partes)


def _pedir(params, reintentos=3):
    for intento in range(reintentos):
        resp = requests.get(URL, params=params, headers=HEADERS, timeout=20)
        if resp.status_code == 429:          # rate limit: esperar y reintentar
            time.sleep(5 * (intento + 1))
            continue
        resp.raise_for_status()
        return resp.text
    raise RuntimeError("Finviz sigue respondiendo 429 (demasiadas peticiones)")


def _leer_tabla(html):
    """Devuelve lista de dicts de una página, o None si no hay tabla."""
    tabla = BeautifulSoup(html, "html.parser").select_one(".screener_results")
    if tabla is None:
        return None
    filas = []
    for row in tabla.select('[role="row"]'):
        celdas = row.select('[data-column-id]')
        if not celdas or row.select_one('[role="columnheader"]'):
            continue
        fila = {}
        for c in celdas:
            col = COLUMNAS.get(c['data-column-id'])
            if col:
                fila[col] = c.get_text(strip=True)
        tk = row.select_one('[data-ticker]')
        if tk is not None:
            fila['Ticker'] = tk['data-ticker']      # el ticker exacto, sin letra de logo
        if fila.get('Ticker'):
            filas.append(fila)
    return filas


def screener(vista='overview', filters_dict=None, tickers=None, max_paginas=100, pausa=0.6):
    """
    vista: 'overview' | 'ownership' | 'technical'
    filters_dict: mismos textos que finvizfinance, ej {'Price': '$1 to $20'}
    tickers: lista opcional -- pide SOLO esos tickers (mucho más rápido que
             bajarse un rango entero de market cap para buscarlos ahí)
    Devuelve DataFrame (vacío si no hay resultados). Lanza excepción si
    Finviz cambia otra vez la página, para que no vuelva a fallar en silencio.
    """
    params = {'v': VISTAS[vista]}
    f = _codigo_filtros(filters_dict)
    if f:
        params['f'] = f

    if tickers:
        tickers = sorted({t.upper().strip() for t in tickers})
        bloques = [tickers[i:i + 20] for i in range(0, len(tickers), 20)]
        filas = []
        for b in bloques:
            filas.extend(_leer_tabla(_pedir({**params, 't': ",".join(b)})) or [])
            time.sleep(pausa)
        return pd.DataFrame(filas)

    filas, vistos = [], set()
    for pag in range(max_paginas):
        html = _pedir({**params, 'r': pag * 20 + 1})
        nuevas = _leer_tabla(html)
        if nuevas is None:
            if pag == 0 and 'screener' in html and 'Total' in html and '0 Total' not in html:
                raise RuntimeError("Finviz devolvió la página pero no se encontró la tabla "
                                   "'.screener_results' -- ¿cambiaron el diseño otra vez?")
            break
        nuevas = [r for r in nuevas if r['Ticker'] not in vistos]
        if not nuevas:
            break
        filas.extend(nuevas)
        vistos.update(r['Ticker'] for r in nuevas)
        if len(nuevas) < 20:
            break
        time.sleep(pausa)
    return pd.DataFrame(filas)
