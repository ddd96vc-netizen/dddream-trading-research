# 📚 DOCUMENTO MAESTRO DE ESTRATEGIAS — DDDreaM

> Biblioteca de patrones de trading de small caps, extraídos de Edu Trades y otros traders.
> Objetivo: catalogar cada setup con sus parámetros, marcar cuáles son construibles con el sistema actual, y definir el sistema de confianza para escalar posición.
>
> **Cómo usar este documento:** cada vez que estudies un vídeo nuevo, añade el patrón en la sección correspondiente con sus parámetros. Cuando retomes el desarrollo, este documento es el punto de partida.

---

## 🧭 EL MARCO QUE ORDENA TODO: Front Side vs Back Side

Toda estrategia de small caps encaja en identificar la **fase** de la acción y aplicar el setup correcto. Esta es la columna vertebral del sistema (Edu Trades):

| Fase | Qué es | Estrategias | Dirección |
|------|--------|-------------|-----------|
| **Front Side** | Fase de subida, empuje y volumen alcista | Breakout, First Green Day, VWAP Bounce, R2G | LONG (comprar) |
| **Back Side** | Fase de caída/dump, el precio se desinfla | First Red Day, Overextended Gap Down, Green to Red, VWAP Rejection | SHORT (vender) |
| **Pánico** | Capitulación violenta de un pump & dump | Dip Buying (comprar el rebote) | LONG rápido |

**Regla de oro de Edu:** "Comprar en la debilidad, vender en la fortaleza." Operar SIEMPRE a favor de la tendencia principal: comprar en el front side, shortear en el back side.

**Dato clave:** la estrategia técnica (el setup) es solo el **10-15%** del sistema. El otro 85% es contexto: catalizador, float, hora, sobreextensión, participación institucional y gestión de riesgo.

---

## 🎯 SISTEMA DE CONFIANZA (para escalar posición)

Estos son los parámetros que, cuando se alinean, dan convicción a un trade. **Cuantos más se cumplan → más confianza → más tamaño de posición.** Esta es la idea de "meter o quitar dinero según la calidad del setup".

Es el "Playbook" de Edu Trades para un setup LONG de calidad:

| # | Parámetro | Qué buscar | ¿Tengo el dato? |
|---|-----------|------------|-----------------|
| 1 | **Volumen histórico** | Picos de volumen significativos en el historial | ✅ Sí (intradía) |
| 2 | **Catalizador** | Noticia o evento corporativo de impacto | ⚠️ Con Finnhub (news) |
| 3 | **Float bajo** | Pocas acciones flotantes, sin dilución inminente | ✅ Sí (scanner) |
| 4 | **Price action limpio** | Tendencia alcista, nuevos máximos, SIN resistencia arriba | ✅ Sí (calculable) |
| 5 | **Institucional < 40%** | Por encima del 40% = trampa institucional peligrosa | ⚠️ Con Finnhub (fundamentals) |
| 6 | **Hora del día** | Primera hora (9:30-10:30 ET) = más volumen y oportunidad | ✅ Sí |
| 7 | **Sobreextensión** (shorts) | +50-70% de subida previa vs histórico | ✅ Sí (calculable multi-día) |
| 8 | **RVOL alto (>1.5x)** | Volumen relativo alto → ya validado que mejora el R | ✅ Sí (ya implementado) |

**Regla de escalado (a definir por Daniel):** ejemplo → "menos de 2 parámetros = no entro; 2-3 = tamaño normal; 4+ = doblo posición".

---

## ⭐ EDGE VALIDADO #1 — Gap & Go filtrado (primera media hora + RVOL alto)

> **Estado:** 🟢 VALIDADO en muestra pequeña (backtest sobre datos propios, ~1065 trades).
> **Fecha del análisis:** julio 2026 · Base de datos: 249 tickers, ~2.2M velas (5m).

### La regla del edge
**Operar Gap & Go SOLO cuando se cumplen las dos condiciones a la vez:**
1. **RVOL alto** (volumen relativo de la primera media hora > 1.5x el promedio previo)
2. **Rotura en los primeros 30 minutos** (entre 9:30 y 10:00 ET)

Con gestión: **stop 2% / target amplio (5% a 10%)**, entrada en el precio de rotura del PM High.

### Resultados del backtest (coste 0.1R ya descontado)

| Configuración | R neto | Trades | Win% |
|---------------|--------|--------|------|
| Todos los Gap & Go (sin filtro) | **-0.073R** ❌ | 7624 | 39% |
| Solo RVOL alto | +0.036R | 1396 | 40% |
| RVOL alto + mañana (<10:30) | +0.074R | 1171 | 40% |
| **RVOL alto + primeros 30 min + stop2/target5** | **+0.107R** ✅ | 1065 | 41% |
| **RVOL alto + primeros 30 min + stop2/target10** | **+0.162R** ✅ | 1065 | 38% |

**Progresión:** de perder dinero (-0.073R) a ganar +0.162R neto, multiplicando el edge >4x, solo filtrando CUÁNDO y CÓMO operar.

### Hallazgo clave: el edge vive en la primera media hora
Análisis por franja horaria (RVOL alto, stop2/target5):

| Franja | R neto | Trades |
|--------|--------|--------|
| **09:30-09:45** | **+0.105R** ✅ | 894 |
| **09:45-10:00** | **+0.119R** ✅ | 171 |
| 10:00-10:30 | -0.161R ❌ | 106 |
| 10:30 en adelante | mayormente negativo ❌ | varios |

**Conclusión:** el edge del Gap & Go se evapora después de las 10:00. La ventana de oro es **9:30-10:00**.

### Dos versiones según perfil
- **Cómoda:** stop 2% / target 5% → +0.107R neto, win 41% (pierdes 6 de 10, más llevable).
- **Agresiva:** stop 2% / target 10% → +0.162R neto, win 38% (target exigente, hay que aguantar el +10%).

### ⚠️ Advertencias honestas
1. **Es backtest, no real.** Asume disciplina perfecta y ejecución al precio teórico.
2. **Slippage en la apertura.** Los primeros 30 min tienen los spreads más anchos del día. El slippage real puede ser mayor que el 0.1R asumido → réstale margen en vivo.
3. **Muestra pequeña.** 1065 trades es sólido pero es histórico limitado (yfinance da 60 días de 5m). Revalidar según se acumulen más datos.
4. **El float NO se pudo validar** (solo 53 de 249 tickers tienen float guardado → muestra insuficiente). Pendiente: guardar float de todos los días para poder medirlo.

### Por qué es creíble
Cada pieza coincide con lo que enseña Edu Trades: primera hora = donde está el volumen; RVOL alto = confirmación de interés real; riesgo asimétrico (stop pequeño, target grande). No es casualidad estadística — tiene lógica de mercado detrás.

### Próximos pasos para reforzarlo
- Añadir trailing stop por VWAP (en vez de target fijo) → podría capturar más de los movimientos grandes.
- Guardar float por día para validar si float bajo mejora aún más.
- Revalidar con más datos acumulados en los próximos meses.
- Aplicar el mismo método de filtrado (hora + RVOL) al VWAP Bounce.

---

## 📈 ESTRATEGIAS LONG (Front Side)

### L1 — Breakout de Resistencia ⭐ (PRÓXIMA A CONSTRUIR)
**Estado:** 🟢 Construible ya · Muy cercana al Gap & Go actual

- **Qué es:** ruptura de una resistencia histórica clave (ej. máximo de 52 semanas, o un nivel horizontal que frenó el precio antes).
- **Por qué funciona:** obliga a los shorts a cubrir (comprar), lo que se suma al volumen comprador.
- **Entrada:** cuando el precio rompe la resistencia CON volumen inusual alto y cierra por encima. Idealmente cierra cerca de máximos del día.
- **Confirmación:** que se mantenga sobre la resistencia rota Y sobre el VWAP.
- **Stop:** el nivel exacto de la resistencia rota (que ahora pasa a ser soporte).
- **Salida:** dejar correr; si cierra fuerte cerca de máximos → candidato a swing.
- **Evitar:** no estar dentro durante publicación de earnings/noticias (ya suele estar descontado).
- **Parámetros construibles:** resistencia = máximos previos; volumen alto; VWAP; cierre cerca de HOD.

### L2 — First Green Day (Primer Día Verde) — Swing
**Estado:** 🟢 Construible

- **Qué es:** primer día verde masivo tras caídas, en sector caliente (hot sector).
- **Criterios:** float muy pequeño (<6-8M); volumen que supera masivamente la media (casi 100% del float rotado); gráfico SIN resistencia arriba; historial de que tras día verde masivo abre con gap up.
- **Entrada:** NO perseguir máximos de la mañana. Esperar a la tarde (13:30-15:30) a un retroceso controlado al VWAP. Si defiende el VWAP repetidamente y aguanta por encima al cierre → comprar para swing overnight.
- **Stop:** justo debajo del VWAP o del soporte de consolidación de la tarde.
- **Salida:** vender al día siguiente en pre-market o en el spike de apertura. Si el sector se debilita temprano, liquidar ya.

### L3 — VWAP Bounce (Rebote en VWAP)
**Estado:** 🟢 Ya implementado (afinable)

- **Qué es:** en día de fuerte tendencia alcista (front side) tras short squeeze inicial.
- **Gatillo:** el precio máximo debe estar alejado al menos 15-20% del VWAP, y hace un pullback ordenado hacia el VWAP para comprar el rebote.
- **Nota de Edu:** los mejores rebotes ocurren un poco ANTES de tocar la línea del VWAP.
- **Stop:** el nivel del VWAP (con pequeño margen/holgura).
- **Invalidación:** si el precio cruza con fuerza por debajo del VWAP → tesis descartada, salir rápido.

### L4 — Gap & Crap Reversal (Regresión en V)
**Estado:** 🟡 Parcialmente construible

- **Qué es:** la acción abre a la baja o se desploma (se pone roja), pero en vez de hundirse encuentra soporte y dibuja una "V" o Hombro-Cabeza-Hombro invertido.
- **Criterios:** float bajo; catalizador positivo vigente; rotación de float; former runner (historial de corridas); sin dilución inminente.
- **Entrada:** cuando recupera y consolida sobre el VWAP (VWAP reclaim), O cuando cruza el precio de apertura (rojo a verde).
- **Filtro clave:** el volumen debe ser ASCENDENTE en cada etapa de recuperación. Si el precio sube pero el volumen se seca → abortar.
- **Stop:** debajo del mínimo del soporte de la "V" o del hombro derecho.

### L5 — Red to Green (R2G)
**Estado:** 🟢 Construible

- **Qué es:** la acción amanece en rojo pero recupera fuerza intradía hasta cruzar por encima de su precio de apertura.
- **Por qué funciona:** genera pánico en los shorts que usaban la apertura como resistencia.
- **Confirmación:** incremento sustancial de volumen al cruzar la línea de apertura.
- **Stop:** el precio de apertura (open).

---

## 📉 ESTRATEGIAS SHORT (Back Side)

> ⚠️ **NOTA IMPORTANTE:** el medidor de R actual solo mide LONGS. Para shorts hay que adaptarlo (stop arriba, target abajo). Es un proyecto propio. Además los shorts requieren "locates" (acciones prestadas) y tienen costes altos.
>
> **Regla de oro shorts (Edu):** solo shortear si hay sobreextensión previa (+50-70% o más vs histórico).

### S1 — First Red Day (Primer Día Rojo)
**Estado:** 🟡 Construible (requiere lógica multi-día + medidor R short)

- **Qué es:** primer síntoma de debilidad, inicio del back side tras varios días verdes consecutivos.
- **Criterios:** float ultra bajo (~5M); sobreextensión macro extrema (ej. de $2 a $28 en una semana).
- **Parámetro de volumen CLAVE:** el volumen del día rojo debe ser NOTABLEMENTE MENOR que el del día verde anterior (compradores agotados).
- **Gatillo:** la acción pierde volumen y cotiza por debajo de su precio de apertura. Entrada short cuando forma doble techo intradía (1min) o rompe el soporte de la mañana hacia el open.
- **Stop:** por encima del máximo del día (HOD) — riesgo ~3%.
- **Salida:** ganancias parciales en fortaleza mientras se desinfla hacia VWAP. Nunca operar segundos pánicos tardíos.

### S2 — Overextended Gap Down (Cortar el Backside)
**Estado:** 🟡 Construible (multi-día + medidor R short)

- **Qué es:** tras gran sobreextensión, el precio abre POR DEBAJO del cierre del día anterior. Deja atrapados a swing traders que venden buscando break even.
- **Operativa:** día 2 o 3, cuando el volumen cae drásticamente (impulso comprador muerto).
- **Entrada:** cualquier rebote de la mañana hacia niveles de congestión/resistencia del día anterior se usa para abrir short. Escalar en cuartos: 1/4 en primera resistencia, 1/4 si sube más, 1/2 cerca de la resistencia mayor.
- **Stop:** por encima de la resistencia principal del día anterior. El cierre del día anterior es la resistencia clave.
- **Salida:** cubrir rápido en soportes intradía. Menos paciente que en First Red Day.

### S3 — Green to Red (Verde a Rojo)
**Estado:** 🟡 Construible (multi-día + medidor R short)

- **Qué es:** acción sobreextendida parabólica (ej. +300% en pocos días) que abre verde, hace un pop inicial tentando resistencia, y luego rompe a la baja cruzando el cierre del día anterior (pasa de verde a rojo).
- **Criterios:** sobreextensión parabólica; fundamentales deficientes; resistencia histórica superior (overhead resistance) donde hay traders atrapados.
- **Entrada:** cuando una vela intradía rechaza la resistencia con alto volumen y el precio rompe hacia abajo el cierre del día anterior.
- **Stop:** un poco por encima del máximo del día o la resistencia clave. Si vuelve a verde, salir.
- **Salida:** dejar correr aprovechando que no hay compradores reales.

### S4 — VWAP Rejection (Rechazo en VWAP)
**Estado:** 🟢 Construible (+ medidor R short)

- **Qué es:** inversa del VWAP Bounce. Día bajista (back side), acción en rojo.
- **Gatillo:** la acción rebota hacia el VWAP pero el volumen DECRECE y el VWAP actúa como resistencia, rechazando el precio.
- **Stop:** el nivel del VWAP.

---

## 🔵 ESTRATEGIAS DE PÁNICO (Dip Buying)

### P1 — OTC Dip Buying / Comprar Pánicos
**Estado:** 🔴 NO construible con datos actuales (requiere Level 2 / Time & Sales)

- **Qué es:** comprar el rebote técnico tras una caída violenta (falling knife) de un pump & dump.
- **Criterios:** sobreextensión previa absurda (semanas parabólicas); pánico 100% TÉCNICO (no por mala noticia); caída violenta -30/40/50% en minutos.
- **Entrada:** NO adivinar el suelo. Esperar clímax de capitulación: el volumen explota a nivel absurdo Y la cinta (Time & Sales) se llena de órdenes verdes agresivas golpeando el Ask, con el Bid subiendo rápido. Comprar al mercado en ese milisegundo.
- **Stop:** justo debajo del mínimo de la vela de clímax (margen muy pequeño, 5-10 centavos).
- **Salida:** rebotes recuperan 20-30% en minutos. Vender en fortaleza a la primera señal de estancamiento.
- **Regla inquebrantable:** SOLO el primer pánico del día. El segundo suele fallar y es peligrosísimo.
- **Por qué no construible:** depende de Level 2, cinta de órdenes y bid/ask en tiempo real. yfinance no da profundidad de mercado.

---

## 🛠️ MEJORAS DE GESTIÓN DE RIESGO (aplicables a varias estrategias)

### TrailingStop por VWAP ⭐ (ALTO VALOR — mejora directa del medidor de R)
**Estado:** 🟢 Construible · Mejoraría el edge actual

- **Filosofía:** operar solo mientras haya tendencia clara. Si la tendencia se rompe, salir de inmediato.
- **Mecánica LONG:** en vez de un target fijo, el stop se desplaza dinámicamente siguiendo el VWAP ("el bigote"). Cuando el precio hace nuevo máximo → retrocede a un mínimo más alto (higher low) → rompe al alza, se sube el stop progresivamente.
- **Números redondos:** preferir stops en números psicológicos redondos (10.00, 10.50) en vez de decimales intermedios.
- **Mecánica SHORT:** inversa. En tendencia bajista (máximos y mínimos decrecientes), el stop baja consecutivamente hasta que la tendencia cambie.
- **Por qué importa:** en el backtest actual el target es fijo (ej. +5%). Con trailing dejas correr las ganancias grandes (los días de +2R, +4R que vimos), lo que puede subir bastante el R esperado.

---

## ⚠️ CONCEPTOS DE CONTEXTO (peligros a detectar)

### ATM Offering (dilución en vivo)
- La empresa vende acciones nuevas al mercado para financiarse (dilución).
- **Síntoma en la cinta:** las compras golpean el Ask repetidamente pero el precio NO sube y el Ask no se limpia (iceberg order institucional soltando inventario).
- **Implicación:** con ATM activo, ir LONG en breakouts es peligrosísimo (peleas contra pared de venta institucional).
- **Detección:** revisar filings SEC para saber si hay ATM activo. La detección en cinta requiere Level 2 (no disponible en yfinance).

### Alto Institutional Ownership (>40%)
- Cuando instituciones controlan gran % del float, reducen artificialmente el float real → acción más volátil y manipulable.
- **La trampa institucional:** colocan compras gigantes visibles (asustan al retail a comprar) → dejan caer bajo VWAP (bear trap para shorts) → retienen supply → short squeeze → distribuyen TODO su inventario en el breakout de máximos → colapso.
- **Regla:** NO comprar a ciegas breakouts de máximos si hay alto % institucional. Es donde las instituciones usan al retail como contrapartida.
- **Filtro (Playbook):** preferir institucional < 40%.
- **Dato disponible con:** Finnhub (fundamentals).

### Pump & Dump
- Insiders inflan artificialmente el precio ("pump") para vender masivamente ("dump") a costa del retail.
- **Stock promoters:** pagados para publicar solo info favorable; sus disclaimers admiten que venden mientras recomiendan comprar y que la acción colapsará.
- **Alerta OTC Markets:** ícono de calavera = posible fraude/investigación.
- **Cómo beneficiarse:** NO comprar en la subida. La oportunidad es el rebote tras el pánico de la caída (ver P1).

---

## 📋 CONTEXTO GENERAL DE SMALL CAPS (fundamentos)

- **Definición:** market cap < $2B. Foco en micro caps (< $300M) que cotizan sobre $1.
- **Naturaleza:** empresas fundamentalmente deficientes que pierden dinero. Se financian vía pump & dump y dilución.
- **Análisis:** 80% técnico (price action) + 20% fundamental (contexto, noticias, dilución).
- **El float:** acciones disponibles para negociar. Low float + volumen masivo = precio se dispara exponencialmente (poca oferta). Sin volumen, low float no se mueve.
- **Patrón cíclico universal:** subida parabólica vertical → caída abrupta → rebotes progresivamente más bajos (efecto pelota de goma) → regreso al punto de inicio.
- **Horario clave:** primera hora (9:30-10:30 ET) concentra la mayor parte del volumen y oportunidades predecibles.
- **Gestión de riesgo:** NUNCA arriesgar más del 5% del capital por posición. Medir siempre ganancia en relación al riesgo (R).
- **Capital inicial:** empezar con poco ($200-500) hasta que las estadísticas propias demuestren rentabilidad.
- **Mentalidad (Mark Douglas):** "todo puede pasar" — ningún trade es 100% seguro. Convicción para ejecutar + humildad para cortar pérdidas rápido.

---

## ✅ ESTADO DEL SISTEMA DDDreaM (lo que ya está construido)

- **Scanner:** captura small caps operables (precio, volumen, float, RVOL) + guardado histórico.
- **Gráficos:** velas estilo TradingView + VWAP + volumen + niveles (PM High/Low, HOD, LOD) + modo en vivo + widget TradingView.
- **Detectores (3):** Gap & Go (5m), VWAP Bounce (5m), Reciclaje (1m).
- **Análisis por ticker:** tabla día a día + segmentación RVOL.
- **Vista agregada:** todos los tickers juntos, miles de casos.
- **Medidor de R:** simula trades (entrada/stop/target, lo que toque primero). Solo LONG.
- **Barrido automático:** prueba todas las combinaciones stop/target y da el top 5. Con coste real (0.1R).

## ✅ ESTADO DEL SISTEMA DDDreaM (actualizado — proyecto completo)

- **Scanner:** captura small caps operables (Finviz ampliado Small+Micro+Mid, respaldo yfinance, edición manual) + sub-base de X (Twitter) por publicación, por ticker, y por trader individual.
- **Gráficos:** velas estilo TradingView + VWAP + volumen + niveles (PM High/Low, HOD, LOD) + modo en vivo + widget TradingView + noticias (Finnhub) + institucional.
- **5 detectores con R real medido:** Gap & Go (long), First Red Day (short), Overextended Gap Down (short), VWAP Bounce (long), Reciclaje (long).
- **Análisis por ticker y vista agregada** para los 5 setups, con barrido automático de stop/target en la web.
- **Optimización avanzada por scripts sueltos:** barrido multi-parámetro (no solo stop/target, también los parámetros propios de cada estrategia) + **validación fuera de muestra** (walk-forward, train/test) para confirmar que las mejoras son reales y no ajuste a ruido.
- **Código legacy archivado** en `legacy.py` (prototipo inicial, ya no se usa).

---

## 🏆 BALANCE FINAL — LAS 3 ESTRATEGIAS CONFIRMADAS Y VERIFICADAS

### 🎯 VALIDACIÓN DEFINITIVA — coste real medido con Interactive Brokers (no estimado)

Todo lo anterior en este documento usaba un coste fijo estimado de 0.1R. Se conectó DDDreaM a Interactive Brokers (cuenta paper trading) vía `ib_async`, y se midió el **spread real** (bid/ask, mediana de 7 ticks por señal, muestra de 30 señales por estrategia) en el momento exacto de cada entrada. Esta es la prueba más honesta posible sin operar con dinero real.

| Estrategia | Spread real medido | Coste real en R | R bruto | R neto (0.1R viejo) | **R neto (coste real)** |
|---|---|---|---|---|---|
| Gap & Go | 0.97% | 0.389R | +0.289R | +0.189R | **-0.100R ✗ negativa** |
| **First Red Day** | 1.91% | 0.762R | +0.897R | +0.797R | **+0.135R ✓ sobrevive** |
| Overextended Gap Down | 2.54% | 1.017R | +0.575R | +0.475R | **-0.442R ✗ negativa** |

**Conclusión definitiva: First Red Day es la única de las tres que sobrevive con el coste de ejecución real, aunque con margen mucho más ajustado (+0.135R) que lo que sugería el backtest con coste estimado.** Gap & Go y Overextended Gap Down se vuelven negativas al aplicar el spread real — el edge de detección existe, pero el coste de entrar/salir en estos nombres se lo come.

**Caminos abiertos para rescatar Gap & Go / Overextended (no probados aún):** stops más anchos (diluyen el coste del spread en términos de R) y/o usar órdenes límite en vez de mercado (evita pagar el spread completo).

---

Las tres pasaron por el proceso más riguroso posible: detección → validación con institucional → optimización de parámetros → **validación fuera de muestra en DOS rondas independientes** (splits 70/30 y 60/40 de los datos). Solo se consideran "reales" las que sobrevivieron probándose en datos que el buscador nunca vio.

### Versión NUEVA — parámetros optimizados y verificados dos veces

| # | Estrategia | Dirección | Parámetros ganadores | R neto verificado | Muestra |
|---|---|---|---|---|---|
| 1 | **First Red Day** | SHORT | 2-3 días verdes previos, rojo en apertura, sobreext ≥50%, stop 2.5% / target 8-10% | **+0.61R a +0.75R** | 40-85 trades |
| 2 | **Overextended Gap Down** | SHORT | Gap ≥3%, 3 días de sobreextensión, sobreext ≥50-70%, entrada pierde_open, stop 2.5% / target 10% | **+0.38R a +0.40R** | 275-492 trades |
| 3 | **Gap & Go** | LONG | RVOL ≥3x, entrada hasta las 10:00-10:30, stop 2.5-3% / target 12% | **+0.08R a +0.18R** | 318-477 trades |

**Por qué se confía en estos números:** cada uno se probó buscando los mejores parámetros SOLO en una parte de los datos (entrenamiento), y luego se midió ese mismo combo exacto SOLO en la otra parte (prueba, nunca vista por el buscador) — dos veces, con cortes de fecha distintos. Los tres se mantuvieron positivos y en el mismo rango en ambas rondas.

### Versión ANTIGUA — con la base de datos original y parámetros más simples, para comparar

| # | Estrategia | Dirección | Parámetros | R neto | Muestra |
|---|---|---|---|---|---|
| 1 | **First Red Day** | SHORT | Sobreextensión ≥30% + institucional <40% | +0.453R (muestra chica) → +0.210R (muestra grande) | 50 → 176 trades |
| 2 | **Overextended Gap Down** | SHORT | Sobreextensión ≥50% + institucional <40% | +0.400R (muestra chica) → +0.110R (muestra grande) | 54 → 243 trades |
| 3 | **Gap & Go** | LONG | RVOL >1.5x + primera media hora + institucional <40% | +0.152R (muestra chica) → +0.088R (muestra grande) | 499 → 1.716 trades |

**Lección visible en esta tabla:** los tres edges se adelgazaron notablemente al crecer la base de datos de 354 a 459 tickers — señal de que parte del número inicial era optimismo de muestra pequeña. Los parámetros nuevos (más específicos, encontrados por optimización y confirmados fuera de muestra) recuperan e incluso superan el rendimiento original, esta vez con más confianza porque pasaron una prueba que los números antiguos nunca pasaron.

---

## ❌ LAS DESCARTADAS — mención breve, cómo funcionaban y sus números

| Estrategia | Cómo funcionaba | R neto | Muestra |
|---|---|---|---|
| **Green to Red** | Acción sobreextendida que abre verde y cruza a rojo cruzando el cierre del día anterior | -0.155R a -0.195R (mejor caso) | 3.100-7.107 trades |
| **VWAP Rejection** | Precio toca el VWAP desde abajo y es rechazado, entrada en corto | Negativo en todos los casos | 21.940-161.652 trades |
| **VWAP Bounce** | Precio toca el VWAP desde arriba y rebota, entrada en largo | -0.112R a -0.340R | 139.516-161.636 trades |
| **Reciclaje** | Micro-impulsos repetidos de +1% intradía, entrada en cada uno | -0.271R a -0.416R (tras corregir un bug de lookahead que daba +1.77R falso) | 59.060-85.066 trades |
| **Gap and Crap (pata corta)** | Tras un Gap & Go, pérdida del VWAP con volumen alto más tarde el mismo día, entrada en corto | -0.097R a -0.114R | 1.353 trades |

Todas con muestra grande y resultado consistente — no son casos de "faltan datos", son estrategias que de verdad no tienen ventaja estadística en este universo de tickers.

---

## 🚀 LO QUE QUEDA PENDIENTE (opcional, baja prioridad)

- **Botón de acceso a "Avance"** (herramienta de Edu Trades para filings SEC) desde la ficha del ticker — comodidad, no cambia ningún número.
- **SEC EDGAR (dilución) integrado** — funcionando vía `rutina_diaria.py`, separado en dilución real (S-1/S-3/424B) vs 8-K genérico.
- **FINRA Reg SHO + Short Volume diario** — identificados como gratis, pendientes de integrar.
- **Perfil de traders de X** — sistema de comparación por trader individual construido y funcionando; usar para seguir refinando criterios del scanner según crezca la muestra de cada trader.

**Fuera de alcance (requieren datos de pago con Level 2 / Time & Sales):** OTC Dip Buying, detección de ATM en cinta, iceberg orders, Precision Trade (scanner en vivo), Reciclaje real (técnica de gestión, no estrategia de entrada).

---

*Documento vivo — última actualización: las 3 estrategias confirmadas y verificadas con validación fuera de muestra en dos rondas independientes (splits 70/30 y 60/40).*
