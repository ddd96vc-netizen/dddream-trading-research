"""
SHORTABLE + RELLENAR HUECOS — script aparte de la rutina diaria, para
correr solo esta parte cuando haga falta. Diseñado para ser RESUMIBLE:
si se corta a mitad (por un corte de conexión con IBKR), puedes volver
a correrlo y solo procesa lo que falta, no repite lo ya guardado.
Requiere IB Gateway abierto y conectado.
"""
import sqlite3
from ib_async import IB, Stock

DB = 'database/dddream.db'   # <-- ajusta la ruta si hace falta
PUERTO_IB = 4002
LIMITE_HUECOS = 20   # cuántos tickers de intradía rellenar por corrida

def conectar():
    return sqlite3.connect(DB)

# ══════════════════════════════════════════════════════════════
#  FASE 1 — SHORTABLE (se salta los que ya tienen dato guardado)
# ══════════════════════════════════════════════════════════════
print("=" * 70)
print("FASE 1/2 — Disponibilidad para corto (shortable)")
print("=" * 70)
try:
    conn = conectar(); c = conn.cursor()
    try:
        c.execute('ALTER TABLE scanner_results ADD COLUMN shortable_shares REAL')
    except Exception:
        pass
    conn.commit()
    # Solo los que TODAVÍA no tienen el dato -- así es resumible
    c.execute('''SELECT DISTINCT symbol FROM scanner_results
                 WHERE shortable_shares IS NULL''')
    simbolos_short = [r[0] for r in c.fetchall()]
    conn.close()

    print(f"  {len(simbolos_short)} tickers pendientes (los ya guardados se saltan)")

    if simbolos_short:
        ib = IB()
        ib.connect('127.0.0.1', PUERTO_IB, clientId=22)
        ib.reqMarketDataType(3)

        guardados = 0
        for i, sym in enumerate(simbolos_short, 1):
            try:
                contrato = Stock(sym, 'SMART', 'USD')
                ib.qualifyContracts(contrato)
                ticker_data = ib.reqMktData(contrato, genericTickList='236')
                ib.sleep(1.2)
                shares = ticker_data.shortableShares
                if shares is not None:
                    conn = conectar(); c = conn.cursor()
                    c.execute('UPDATE scanner_results SET shortable_shares=? WHERE symbol=?', (shares, sym))
                    conn.commit(); conn.close()
                    guardados += 1
                    print(f"  [{i}/{len(simbolos_short)}] {sym}: {shares} acciones")
                else:
                    print(f"  [{i}/{len(simbolos_short)}] {sym}: sin dato")
                ib.cancelMktData(contrato)
            except BaseException as e:
                print(f"  [{i}/{len(simbolos_short)}] {sym}: saltado ({e})")
                continue

        ib.disconnect()
        print(f"\n  ✓ {guardados}/{len(simbolos_short)} nuevos guardados en esta corrida")
    else:
        print("  ✓ No hay pendientes, todos los tickers ya tienen shortable guardado")
except BaseException as e:
    print(f"✗ FASE 1 falló: {e}")
    print("  (no pasa nada, vuelve a correr este script y sigue desde donde quedó)")

# ══════════════════════════════════════════════════════════════
#  FASE 2 — RELLENAR HUECOS DE INTRADÍA (naturalmente resumible:
#  solo busca tickers que AÚN no tienen ninguna vela guardada)
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("FASE 2/2 — Rellenar huecos de intradía")
print("=" * 70)
try:
    conn = conectar(); c = conn.cursor()
    c.execute('''SELECT DISTINCT symbol FROM scanner_results
                 WHERE symbol NOT IN (SELECT DISTINCT symbol FROM intraday_data)''')
    simbolos_sin_datos = [r[0] for r in c.fetchall()]
    conn.close()

    print(f"  {len(simbolos_sin_datos)} tickers sin intradía, procesando hasta {LIMITE_HUECOS} esta vez")

    if simbolos_sin_datos:
        ib = IB()
        ib.connect('127.0.0.1', PUERTO_IB, clientId=23)
        ib.reqMarketDataType(3)

        for sym in simbolos_sin_datos[:LIMITE_HUECOS]:
            try:
                contrato = Stock(sym, 'SMART', 'USD')
                ib.qualifyContracts(contrato)
                fecha_fin = ''
                conn = conectar(); c = conn.cursor()
                total_guardadas = 0
                for _ in range(15):
                    try:
                        barras = ib.reqHistoricalData(contrato, endDateTime=fecha_fin, durationStr='2 D',
                                                        barSizeSetting='5 mins', whatToShow='TRADES', useRTH=False)
                    except BaseException as e:
                        print(f"    ({sym}: trozo falló, {e})")
                        break
                    if not barras:
                        break
                    for b in barras:
                        dt_str = b.date.strftime('%Y-%m-%d %H:%M:%S%z')
                        dt_str = dt_str[:-2] + ':' + dt_str[-2:]
                        c.execute('''INSERT OR IGNORE INTO intraday_data
                            (symbol, datetime, interval, open, high, low, close, volume, sesion)
                            VALUES (?,?,?,?,?,?,?,?,?)''',
                            (sym, dt_str, '5m', b.open, b.high, b.low, b.close, b.volume, 'regular'))
                        total_guardadas += 1
                    fecha_fin = barras[0].date.strftime('%Y%m%d %H:%M:%S')
                    ib.sleep(1.2)
                conn.commit(); conn.close()
                print(f"  ✓ {sym}: {total_guardadas} velas guardadas")
            except BaseException as e:
                print(f"  ✗ {sym}: saltado ({e})")
                continue

        ib.disconnect()
        print("\n  ✓ Fase 2 completada para esta tanda")
    else:
        print("  ✓ No hay tickers pendientes de rellenar")
except BaseException as e:
    print(f"✗ FASE 2 falló: {e}")
    print("  (no pasa nada, vuelve a correr este script y sigue desde donde quedó)")

print("\n" + "=" * 70)
print("COMPLETADO — si algo falló arriba, solo vuelve a correr este mismo")
print("script: lo ya guardado se salta solo, no se repite trabajo.")
print("=" * 70)