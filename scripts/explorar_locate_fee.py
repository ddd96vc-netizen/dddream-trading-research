"""
EXPLORADOR — disponibilidad para corto vs TASA DE PRÉSTAMO (%).
Ya sabemos que shortableShares funciona. Este script imprime TODO lo que
la API devuelve para un ticker, para ver si la tasa de préstamo en %
viene incluida ahí, o si hace falta consultarla en la web (IBorrowDesk
o el Securities Lending Dashboard de IBKR).
Requiere IB Gateway abierto y conectado.
"""
from ib_async import IB, Stock

PUERTO = 4002
TICKER = 'AGEN'   # <-- cambia por cualquier ticker de tu base

ib = IB()
ib.connect('127.0.0.1', PUERTO, clientId=60)
ib.reqMarketDataType(3)
print("✓ Conectado\n")

contrato = Stock(TICKER, 'SMART', 'USD')
ib.qualifyContracts(contrato)

# Pedimos el tick genérico 236 (shortable) -- lo que ya sabemos que funciona
ticker_data = ib.reqMktData(contrato, genericTickList='236')
ib.sleep(3)

print("=" * 60)
print(f"TODO lo que la API devuelve para {TICKER}")
print("=" * 60)
print(f"  shortableShares : {ticker_data.shortableShares}")
print(f"  shortable        : {ticker_data.shortable}")
print(f"  last              : {ticker_data.last}")
print(f"  bid / ask         : {ticker_data.bid} / {ticker_data.ask}")

print("\n--- Volcado completo del objeto ticker (por si hay algo más) ---")
for atributo in vars(ticker_data):
    valor = getattr(ticker_data, atributo)
    if valor not in (None, [], {}, float('nan')):
        try:
            if valor == valor:  # descarta nan
                print(f"  {atributo}: {valor}")
        except Exception:
            print(f"  {atributo}: {valor}")

ib.cancelMktData(contrato)
ib.disconnect()

print("\n" + "=" * 60)
print("Si no ves ningún campo con '%' o 'fee' o 'rate' arriba, confirma")
print("que la tasa de préstamo NO viene por esta vía -- usa IBorrowDesk")
print("(iborrowdesk.com) o el Securities Lending Dashboard de tu cuenta.")
print("=" * 60)