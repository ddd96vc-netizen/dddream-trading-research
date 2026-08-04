# 🔬 Investigación — validación de estrategias

Todos los scripts que se corrieron sobre `dddream.db` para buscar y validar
edges de trading. Cada uno es independiente, reproducible, y lee directo de
la base de datos (no necesitan internet, salvo los que dicen explícitamente
que usan IBKR o Finnhub).

## Cómo correrlos

1. Copia el script que quieras a la misma carpeta que tu `dddream.db`.
2. Ajusta la variable `DB = 'dddream.db'` al inicio si tu ruta es distinta.
3. Ejecuta con `python nombre_del_script.py`.

Ningún script de esta carpeta modifica la base de datos (excepto los que
lo dicen explícitamente, como los de limpieza en `scripts/`).

---

## El resultado final, primero

| Estrategia | Dirección | R neto (coste real medido) | Veredicto |
|---|---|---|---|
| **First Red Day** | SHORT | **+0.135R** | ✅ Confirmada, sobrevive todo |
| Gap & Go | LONG | -0.100R (con spread real) | ❌ El coste se come el edge |
| Overextended Gap Down | SHORT | -0.442R (con spread real) | ❌ El coste se come el edge |
| Green to Red | SHORT | negativo, dos formas de medirlo | ❌ Descartada |
| VWAP Rejection | SHORT | negativo | ❌ Descartada |
| VWAP Bounce | LONG | negativo, 139.516 señales | ❌ Descartada |
| Reciclaje (como entrada) | LONG | negativo tras corregir un bug | ❌ Descartada |
| Reciclaje (como gestión) | — | empeora el resultado | ❌ Descartada |

El detalle completo, con todos los números, está en
[`docs/ESTRATEGIAS_DDDreaM.md`](../docs/ESTRATEGIAS_DDDreaM.md).

---

## El recorrido, carpeta por carpeta

### 📁 `gap_and_go/` — la primera validada, la que enseñó el método

- **`analisis_st.py`** — resultado de tres pasadas de refinamiento (filtros →
  hora exacta → stop/target). Encontró el edge base: RVOL alto + primera
  media hora + stop 2%/target 10%.
- **`catalizador_gapgo_afinado.py`** — prueba si un catalizador de noticias
  mejora el edge. Clave: solo cuenta si la noticia se publicó **antes** de
  la entrada (la primera versión, sin ese matiz, confundía causa con
  consecuencia — el ticker se movía y LUEGO salían noticias sobre el
  movimiento).
- **`validar_float.py`** — prueba si el float bajo mejora el resultado.
- **`gap_and_crap.py`** / **`gap_and_crap_short.py`** — dos intentos de
  capturar la reversión ("Gap and Crap") tras un Gap & Go fallido. Ambos
  descartados con datos.

### 📁 `first_red_day/` — la que sobrevivió, con su lección incluida

- **`first_red_day_v1_CON_BUG.py`** — ⚠️ conservado a propósito, sin
  corregir. La primera versión tenía un bug de lookahead bias que daba
  +0.670R falso. Se conserva como evidencia del proceso de detección.
- **`frd_realista.py`** — el arreglo: la entrada se mueve al día siguiente
  (D+1) al rojo ya confirmado, usando solo información genuinamente pasada.
- **`barrido_frd.py`** — el barrido completo de 108 combinaciones que
  confirmó qué parámetros importan de verdad.

Después de esto, First Red Day pasó por optimización de parámetros,
validación fuera de muestra dos veces, y medición de coste real (ver
`validacion_final/`) — siendo la única en sobrevivir todo el proceso.

### 📁 `overextended_gap_down/` — casi lo logra, el coste la mata

- **`overext_gapdown.py`** — el barrido base: acción sobreextendida que
  abre con gap down, se shortea el rebote hacia la resistencia previa.
- **`overext_volumen_test.py`** — prueba un filtro de volumen más específico
  (rebote débil + rechazo con pico de volumen). Parecía mejorar el resultado
  en una primera pasada (+0.322R), pero **no se sostuvo al dividir los datos
  en dos mitades** — confirmó que era ruido de muestra pequeña, no un edge
  real. Se descartó el filtro con la misma disciplina que salvó el proyecto
  varias veces.

### 📁 `descartadas/` — con la misma evidencia rigurosa que las confirmadas

- **`green_to_red_destruccion.py`** / **`g2r_vwaprej.py`** — Green to Red y
  VWAP Rejection, incluyendo una segunda pasada de Green to Red probando la
  condición real de "destrucción del 50%" mencionada por un trader de
  referencia. Sigue sin funcionar.
- **`vwap_bounce_validacion.py`** — 139.516 señales, todas negativas. La
  muestra más grande de todo el proyecto, sin ambigüedad posible.
- **`reciclaje_primer_impulso.py`** — micro-impulsos intradía como señal de
  entrada. Mostró un resultado inicial espectacular (+0.78R a +1.77R) que
  resultó ser **otro bug de lookahead**: el código entraba en el precio
  base *antes* de la subida que usaba para detectar el impulso. Corregido,
  el resultado real es negativo.
- **`reciclaje_gestion_ticks_reales.py`** — la idea replanteada correctamente:
  no como entrada, sino como técnica de GESTIÓN de una posición ya abierta
  (según cómo la describen los traders de referencia). Probado con ticks
  reales de Interactive Brokers sobre las entradas ya validadas. Conclusión:
  añadir posición y soltar en el rebote **empeora** el resultado frente a
  simplemente mantener el plan original.

### 📁 `contexto/` — las capas que sí aportaron

- **`institucional_filtro.py`** — el filtro de participación institucional
  <40% mejora las tres estrategias confirmadas de forma consistente.
- **`comparativa_por_trader.py`** — compara el perfil (float, RVOL,
  institucional) de los tickers de traders de referencia contra la selección
  propia del scanner, usando el **día exacto** de cada operación (no "el
  dato más reciente", que puede venir de una fecha muy distinta y dar una
  imagen falsa — este fue otro matiz importante detectado a mitad de
  proyecto).
- **`perfil_traders_7_estrategias.py`** — cruza el perfil completo de esos
  traders (float + institucional + RVOL + cambio% del día) contra las 7
  estrategias, confirmadas y descartadas. Green to Red empeora de forma
  escalonada cuantas más condiciones del perfil cumple — la confirmación
  más limpia de que de verdad no tiene edge.

### 📁 `validacion_final/` — el cierre riguroso

- **`optimizador.py`** — búsqueda tipo StrategyQuant sobre parámetros y
  stop/target. Encontró combinaciones con resultados muy por encima de lo
  normal (+1.70R) — que resultaron ser un **sesgo mecánico**: stops
  artificialmente pequeños inflan el R de forma matemática sin que el coste
  real (spread) esté bien representado. Lección documentada, no solo el
  código.
- **`validacion_fuera_de_muestra_70_30.py`** y **`_60_40.py`** — la prueba
  definitiva: buscar los mejores parámetros SOLO en una parte de los datos,
  y confirmar que se sostienen en la otra parte, nunca vista. Corrido dos
  veces con splits distintos. First Red Day y Overextended Gap Down
  sobrevivieron esta prueba; luego el coste real terminó de decidir cuál de
  las dos era operable de verdad.
- **`diagnostico_y_revalidacion.py`** — caza un outlier sospechoso en Gap &
  Go (resultó ser ruido normal, no un bug) y reconfirma los números de First
  Red Day / Overextended con la base de datos ya crecida.

---

## La metodología, en una frase

Cada estrategia pasó por: **detección → filtros de contexto → optimización
→ validación fuera de muestra → coste de ejecución real**. Solo se dio algo
por confirmado cuando sobrevivió las cinco capas — no la primera que diera
un número positivo.

## Lección transversal

Se cazaron **dos bugs de lookahead bias** (First Red Day inicial, Reciclaje
inicial) y **un sesgo de sobreajuste** (el optimizador con stops
artificiales) — los tres dando resultados falsos "demasiado buenos para ser
verdad". La regla que salió de esto, aplicada de ahí en adelante a cualquier
resultado nuevo: **sospechar primero, confirmar después.**
