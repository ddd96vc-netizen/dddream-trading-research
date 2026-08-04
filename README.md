# DDDreaM

Sistema personal de investigación y day trading de small caps en EE.UU. — construido
desde cero en Python, con la misma pregunta guiando cada decisión: **¿esto que
"funciona" en un backtest, de verdad funciona, o solo parece que funciona?**

De 7 estrategias exploradas con rigor, **1 sobrevivió** a validación fuera de
muestra, optimización, y el coste real de ejecución medido con datos de un
bróker real. Ese resultado, y el camino para llegar a él, es el proyecto.

## Qué es esto

Una herramienta tipo "Flash Research" hecha a medida: un scanner de small caps
volátiles, gráficos intradía con niveles clave, seguimiento de traders de
referencia, y — la parte central — un motor de backtesting propio para medir
si una idea de trading tiene ventaja estadística real antes de arriesgar
un euro.

## El hallazgo principal

**First Red Day** (venta en corto tras el primer día rojo de una acción
sobreextendida) es la única de las 7 estrategias probadas que sigue siendo
rentable después de:
- Validación fuera de muestra en **dos rondas independientes** (splits 70/30 y 60/40)
- Optimización de parámetros sin caer en sobreajuste (se detectó y descartó
  un sesgo de stops artificialmente ajustados)
- **Coste de ejecución real**, medido con el spread de mercado real vía la
  API de Interactive Brokers (no un coste estimado)

Resultado final: **+0.135R neto por operación**, con datos reales de mercado,
no una simulación optimista.

El recorrido completo — incluyendo dos bugs de lookahead bias que se cazaron
y corrigieron a tiempo — está documentado en [`docs/`](docs/) y en el detalle
de cada script en [`research/`](research/).

## Stack técnico

- **Python 3.11**, **Flask** (interfaz web)
- **SQLite** — toda la base de datos histórica y de investigación
- **yfinance**, **finvizfinance** — datos de mercado y fundamentales gratuitos
- **Finnhub API** — noticias y catalizadores con hora exacta
- **SEC EDGAR API** — alertas de dilución (ofertas de acciones)
- **Interactive Brokers API** (`ib_async`) — datos de mercado en vivo, spread
  real, disponibilidad para venta en corto, respaldo de histórico intradía
- **Plotly** — gráficos de velas interactivos

## Estructura del proyecto

```
app/              El sistema en sí: scanner web, base de datos, gráficos
scripts/          Rutina diaria y utilidades de mantenimiento de datos
research/         Los ~20 scripts de investigación que validaron (o descartaron)
                  cada estrategia -- organizados por tema, con su propio README
docs/             La guía conceptual del proyecto y el balance final de estrategias
sandbox/          Scripts circunstanciales de un solo uso (ver su README)
```

## Cómo correrlo

```bash
git clone <este-repo>
cd DDDreaM
pip install -r requirements.txt
cp .env.example .env   # y rellena tu FINNHUB_API_KEY
cd app
python app.py
```

La base de datos (`dddream.db`) no se incluye en el repositorio — se genera
sola la primera vez que corras `scripts/rutina_diaria.py`, que trae datos
reales de Finviz y yfinance.

## Lo que este proyecto demuestra

- Integración de **5 APIs externas** con manejo real de fallos, límites de
  peticiones, y reconexiones
- Diseño de base de datos con **migraciones seguras** (nunca rompe datos ya
  guardados al añadir columnas o tablas nuevas)
- **Dos bugs de lookahead bias cazados por cuenta propia** — el tipo de error
  que hace parecer rentable una estrategia que en la vida real no lo sería
- **Validación estadística seria**: fuera de muestra, detección de sobreajuste,
  coste de ejecución real en vez de estimado
- Limpieza de datos del mundo real: símbolos corruptos, huecos de histórico,
  fuentes que fallan a mitad de descarga

La lección de fondo, y la más valiosa: **la mayoría de las ideas de trading que
suenan bien no sobreviven a una medición honesta — y saber eso con certeza vale
más que cualquier número bonito sin verificar.**
