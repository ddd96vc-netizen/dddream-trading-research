# DDDreaM — Guía Conceptual del Proyecto
### Qué construí, por qué, y qué aprendí

> Este documento no explica líneas de código, explica **ideas**. La meta es que
> cuando abras los archivos, ya entiendas el porqué de cada pieza — y que puedas
> contarle a alguien "lo que hice fue esto, y lo hice por esto".

---

## 1. ¿Qué es DDDreaM y qué problema resuelve?

DDDreaM es un sistema personal para investigar estrategias de **day trading de small caps** (acciones de empresas pequeñas, muy volátiles). Existen herramientas comerciales caras que hacen esto (tipo Flash Research), y la idea fue **construir una versión propia y gratuita** que hiciera lo esencial: encontrar acciones que se mueven, guardar su historial, y sobre todo **medir con rigor si una estrategia gana dinero o no**, en vez de operar por corazonadas.

La pregunta central que responde el sistema es: *"De todas las ideas de trading que he escuchado en YouTube, ¿cuáles funcionan de verdad con datos, y cuáles son solo humo?"*

---

## 2. Las decisiones técnicas, y por qué cada una

**Python** — el lenguaje. Elegido porque es el estándar para análisis de datos y trading, con librerías gratuitas para todo lo que hacía falta.

**SQLite (la base de datos)** — Aquí hay una decisión importante. Al principio los datos podrían guardarse en archivos sueltos (CSV, JSON), pero eso se vuelve un caos cuando tienes cientos de acciones con miles de velas cada una. Una **base de datos** te deja consultar, filtrar y cruzar datos de forma ordenada y rápida. Se eligió **SQLite** en concreto (en vez de algo más grande como PostgreSQL) porque es **un solo archivo, sin servidor, sin instalación** — perfecto para un proyecto personal en un ordenador. Todo tu proyecto vive en un archivo `dddream.db`.

**La arquitectura de datos — el concepto clave.** El sistema separa dos cosas que la gente suele confundir:
- **`scanner_results`**: la "ficha" de cada acción — precio, float, volumen, RVOL, etc. Una foto de sus características.
- **`intraday_data`**: las **velas** minuto a minuto — el historial de cómo se movió el precio durante el día.

Son dos pasos distintos: primero *escaneas* (encuentras qué acciones mirar y sus fichas), y luego *descargas las velas* de esas acciones. Separarlos hace el sistema más robusto — si falla la descarga de velas de una acción, no se cae todo lo demás.

**Flask (la web local)** — Para no trabajar solo con la terminal, se montó una pequeña web que corre en tu propio ordenador. Sirve para lo visual: ver gráficos, subir fotos de los tickers de X, revisar datos. **Decisión consciente del final del proyecto:** las *pruebas* de estrategias se hacen mejor con **scripts sueltos** (más rápido, sin levantar la web), y la web se reserva para lo que de verdad necesita pantalla.

**Las fuentes de datos gratuitas** (esto es el corazón del sistema):
- **yfinance** (Yahoo Finance) — da las velas de precio/volumen. Fiable, gratis, es la columna vertebral. Su límite: solo guarda ~60 días de velas de 5 minutos por descarga.
- **Finviz (screener)** — da las "fichas" (float, short float, RVOL, institucional). Peculiaridad que descubrimos: su consulta *individual* por acción está rota, pero la consulta *en lote* (todas de golpe) sí funciona.
- **Finnhub** — da noticias/catalizadores. Gratis, aunque con cobertura floja en las acciones más pequeñas.
- **SEC EDGAR** — la web oficial del regulador de EE.UU. Gratis, con API pública. Da los *filings* (documentos oficiales) para detectar dilución.

---

## 3. Los conceptos de trading que hay que dominar

**Small caps y por qué se mueven tanto.** Son empresas pequeñas, muchas veces con pérdidas, y con **poco "float"** (pocas acciones disponibles para comprar/vender). Con pocas acciones en circulación, cualquier oleada de compra o venta mueve el precio de forma brutal — de ahí los movimientos de +50% o +200% en un día. Ese es el terreno donde estos traders operan.

**Las métricas clave (qué significan y por qué importan):**
- **Float** — cuántas acciones hay realmente disponibles. Cuanto más bajo, más explosivo el movimiento.
- **RVOL (Relative Volume)** — el volumen de hoy comparado con lo normal. Un RVOL alto significa "hoy hay algo pasando aquí, mucha gente operando".
- **Short Float** — qué porcentaje de las acciones está vendido en corto (apostando a la baja). Alto puede significar potencial de "short squeeze".
- **Institutional Ownership** — cuánto de la empresa está en manos de grandes fondos. **Bajo es bueno para el trader minorista** (más margen de movimiento, menos control institucional).
- **VWAP** — el precio promedio ponderado por volumen del día. Funciona como un "imán" y una línea de referencia clave: por encima = fuerza, por debajo = debilidad.
- **Gap** — la diferencia entre el cierre de ayer y la apertura de hoy. Un gap grande al alza es la señal de arranque de muchas estrategias.

**Las 5 estrategias, explicadas por su lógica:**

1. **Gap & Go (largo)** — La acción abre con un gap fuerte al alza y rompe el máximo del premarket. La lógica: si hay fuerza real, seguirá subiendo tras romper ese nivel. *Se opera en la primera media hora, que es cuando hay más volumen.*

2. **First Red Day (corto)** — Después de varios días verdes subiendo como loca (sobreextensión), aparece el **primer día rojo**: la primera señal de que los compradores se agotaron. Se opera a la baja al día siguiente. La lógica: el pump no dura para siempre, y el primer día de debilidad suele ser el comienzo de la caída.

3. **Overextended Gap Down (corto)** — Tras una subida enorme, la acción abre a la baja (gap down). Se opera el rebote hacia la resistencia. La lógica: el "backside" (la parte de atrás del movimiento) donde el precio se desinfla.

4. **VWAP Bounce (largo)** — El precio toca el VWAP desde arriba y rebota. La lógica: el VWAP como soporte dinámico.

5. **Reciclaje** — *Este resultó ser un concepto mal entendido.* No es una estrategia de entrada, es una **técnica de gestión** de una posición que va perdiendo (promediar y soltar en rebotes). Requiere leer la cinta en vivo (Level 2), algo que no teníamos.

---

## 4. La metodología de validación — LO MÁS IMPORTANTE

Esto es lo que separa este proyecto de "seguir corazonadas". Cada estrategia se sometió al mismo examen riguroso.

**Medir en "R" (múltiplos de riesgo).** En vez de medir en dólares o en porcentaje, se mide en **R**: cuántas veces tu riesgo ganaste o perdiste. Si arriesgas $100 (tu stop) y ganas $200, eso es +2R. ¿Por qué es la forma correcta? Porque hace comparables todas las estrategias sin importar el precio de la acción ni cuánto dinero pongas. Un edge de "+0.3R por trade" significa que, en promedio, ganas 0.3 veces tu riesgo cada vez que operas — y eso se puede proyectar a cualquier tamaño de cuenta.

**Qué es un backtest y sus límites.** Un backtest simula la estrategia sobre datos históricos: "si hubiera operado esto en cada señal de los últimos meses, ¿habría ganado?". Es poderosísimo, pero tiene un límite honesto: **el pasado no garantiza el futuro**, y el backtest ejecuta perfecto (sin miedo, sin dudar, sin errores humanos), cosa que en la vida real no pasa.

**El sesgo de "mirar el futuro" (lookahead) — la trampa más traicionera.** Este concepto es oro. Ocurre cuando, sin darte cuenta, tu código usa información que en la vida real todavía no existiría en ese momento. Ejemplo real que nos pasó **dos veces**: detectábamos un "impulso" mirando velas *futuras* para confirmar que el precio subía, y luego fingíamos haber comprado *antes* de esa subida — o sea, comprando con la certeza de algo que aún no había pasado. Eso infla los resultados de forma brutal (llegamos a ver +1.7R falsos). **La regla de oro que salió de esto: cualquier resultado demasiado bueno, sospéchalo y revisa primero si hay lookahead.**

**El coste por trade.** Cada operación real cuesta: spread (diferencia compra/venta), slippage (el precio que consigues no es el que ves), comisiones. Empezamos restando 0.1R por trade como estimación, pero fuimos honestos en que **para small caps volátiles el coste real es más cercano a 0.3R** — y algunas estrategias que parecían rentables con 0.1R se vuelven negativas con 0.3R. Esa honestidad es la que evita ilusiones.

**Por qué la muestra grande importa.** Con pocos datos, cualquier estrategia puede parecer buena por pura casualidad. Vimos en vivo cómo un edge se desinflaba de +0.036R a +0.011R al crecer la muestra — porque la verdad estadística aparece con volumen. Nunca des un edge por definitivo con muestra chica.

---

## 5. Los datos de contexto — filtros que sí aportaron

Más allá de la mecánica del gráfico, se probaron filtros de "contexto":

**Institucional < 40%** — Regla del trader Edu Trades. La probamos sobre las 3 estrategias confirmadas y **mejoró las tres de forma consistente** (en Gap & Go casi dobló el resultado). Confirmado: menos presencia institucional = más edge.

**Catalizador / noticias** — La idea: un Gap & Go con noticia real detrás rinde más. Al probarlo salió mejor... pero **aquí aplicamos una lección crítica sobre causa vs. causa-al-revés**: había que asegurarse de que la noticia se publicó **ANTES** de la hora de entrada. Si salió a las 2pm y entraste a las 9:35am, no te sirvió de nada — y además, los medios publican sobre las acciones que ya se movieron (la noticia es *consecuencia*, no *causa*). Al afinarlo bien (solo noticias premarket, antes de entrar), el filtro **se sostuvo** — es real y usable en vivo.

**SEC EDGAR (dilución)** — Detecta cuando una empresa emite acciones nuevas (dilución), una bandera roja. Lección importante aquí: el formulario **8-K es demasiado genérico** (las empresas lo presentan por todo, es ruido), mientras que **S-1, S-3, 424B4, 424B5 son específicos de ofertas de acciones** — esos sí son señal real. Aprender a separar la señal del ruido fue clave.

---

## 6. Los resultados — qué funcionó y qué no

**Se probaron 7 estrategias con el mismo rigor. El balance final:**

**✅ Confirmadas (4 combinaciones rentables):**
- First Red Day (corto) + institucional bajo → la más fuerte
- Overextended Gap Down (corto) + institucional bajo
- Gap & Go (largo) + noticia antes de entrar
- Gap & Go (largo) + institucional bajo → la más frágil ante costes reales

**❌ Descartadas (4), negativas con muestra grande:**
- Green to Red, VWAP Rejection, Reciclaje, VWAP Bounce

**El dato que da perspectiva:** de todo lo que se probó, **la mayoría no servía**. Y eso está perfectamente bien — el valor no está en que todo funcione, sino en **saber con certeza cuáles sí y cuáles no**, algo que la mayoría de la gente que opera nunca llega a medir.

**Sobre el dinero (con honestidad):** las estrategias confirmadas, ejecutadas con disciplina y con un riesgo moderado por operación, proyectan un rango que sería decente para empezar. Pero ese número es el **techo optimista**, no la expectativa — porque el backtest no mide tu psicología, ni el coste real de un bróker, ni los cambios de humor del mercado. La cifra realista para empezar es una fracción de esa proyección, mientras ganas experiencia de ejecución real.

---

## 7. Lo que aprendí (las meta-lecciones)

1. **Medir con rigor lo cambia todo.** La diferencia entre "creo que esto funciona" y "esto da +0.4R en 54 trades" es la diferencia entre apostar y decidir con datos.

2. **Desconfiar de los números bonitos.** Cazamos dos sesgos de lookahead precisamente porque un resultado "demasiado bueno" nos hizo sospechar. La honestidad intelectual vale más que un resultado impresionante.

3. **La mayoría de las ideas no sirven, y eso es información valiosa.** Descartar con certeza es tan útil como confirmar.

4. **Los datos gratuitos tienen límites reales.** Level 2, Time & Sales, y la cinta en vivo — lo que de verdad usan los traders experimentados para el timing fino — no se pueden backtestear barato. Eso se aprende operando en vivo, con la cuenta de un bróker.

5. **Construir tu propia herramienta te obliga a entender de verdad.** Cada decisión (qué base de datos, qué fuente, cómo medir) me hizo entender el problema mucho mejor que si usara una herramienta ya hecha.

---

*DDDreaM — un sistema construido pieza por pieza, con la disciplina de no creerse nada hasta medirlo.*
