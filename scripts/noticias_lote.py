"""
NOTICIAS EN LOTE — trae noticias de Finnhub para TODOS tus tickers de
golpe, para poder analizar después si el catalizador mejora el R de tus
edges. Respeta el límite gratis de Finnhub (~60 llamadas/minuto).
Corre esto UNA VEZ antes de catalizador_gapgo.py.
"""
import sqlite3
import requests
import time
import os
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
from datetime import timezone
from zoneinfo import ZoneInfo

load_dotenv()
DB = 'dddream.db'   # <-- ajusta la ruta si hace falta
API_KEY = os.getenv('FINNHUB_API_KEY')
DIAS_ATRAS = 60
PAUSA_ENTRE_LLAMADAS = 1.1   # segundos, para no pasarte de 60/min

def conectar():
    return sqlite3.connect(DB)

if not API_KEY:
    print("✗ No hay FINNHUB_API_KEY en tu .env — revisa que exista y tenga el valor.")
    raise SystemExit

conn = conectar(); c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM intraday_data')
simbolos = [r[0] for r in c.fetchall()]
conn.close()

print(f"Consultando noticias de Finnhub para {len(simbolos)} tickers...")
print(f"(tardará ~{len(simbolos) * PAUSA_ENTRE_LLAMADAS / 60:.1f} minutos por el límite de la API gratis)\n")

hoy = date.today()
desde = hoy - timedelta(days=DIAS_ATRAS)

total_guardadas = 0
tickers_con_noticias = 0

conn = conectar(); c = conn.cursor()
try:
    c.execute('ALTER TABLE noticias ADD COLUMN hora TEXT')
except Exception:
    pass
conn.commit(); conn.close()
for i, symbol in enumerate(simbolos, 1):
    url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={desde}&to={hoy}&token={API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        print(f"  ✗ [{i}/{len(simbolos)}] {symbol}: error {e}")
        time.sleep(PAUSA_ENTRE_LLAMADAS)
        continue

    if not isinstance(data, list):
        print(f"  ⚠ [{i}/{len(simbolos)}] {symbol}: respuesta inesperada ({data})")
        time.sleep(PAUSA_ENTRE_LLAMADAS)
        continue

    conn = conectar(); c = conn.cursor()
    guardadas_ticker = 0
    for item in data:
        ts = item.get('datetime')
        if not ts:
            continue
        dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
        dt_et = dt_utc.astimezone(ZoneInfo('America/New_York'))
        fecha_noticia = dt_et.strftime('%Y-%m-%d')
        hora_noticia = dt_et.strftime('%H:%M')
        headline = (item.get('headline') or '').strip()
        if not headline:
            continue
        resumen = (item.get('summary') or '').strip()
        fuente = item.get('source', '')
        link = item.get('url', '')
        try:
            c.execute('''INSERT OR IGNORE INTO noticias
                (symbol, fecha, hora, headline, resumen, fuente, url, fecha_registro)
                VALUES (?,?,?,?,?,?,?,?)''',
                (symbol, fecha_noticia, hora_noticia, headline, resumen, fuente, link, str(date.today())))
            if c.rowcount > 0:
                guardadas_ticker += 1
        except Exception:
            pass
    conn.commit()
    conn.close()

    if guardadas_ticker > 0:
        tickers_con_noticias += 1
    total_guardadas += guardadas_ticker
    print(f"  [{i}/{len(simbolos)}] {symbol}: {len(data)} noticias encontradas, {guardadas_ticker} nuevas guardadas")

    time.sleep(PAUSA_ENTRE_LLAMADAS)

print(f"\n✓ Completado: {total_guardadas} noticias guardadas en total")
print(f"  {tickers_con_noticias} de {len(simbolos)} tickers tienen al menos una noticia")
print("\nAhora corre catalizador_gapgo.py para ver si mejora el R.")
