# Validación del clon

Última ejecución: 2026-11-24 20:46:09 · partes: tablero, ad, matriz · clon: `visor` · original: `_original`

Modo de vectores: clon: baai/bge-m3 · original: baai/bge-m3

Emparejamiento siempre por clave: artículos del tablero por (cod, num), con los índices g traducidos a (cod, num); antes/después por (cod, id BL:); matriz por `a`. **G1** = determinista, debe calzar exacto; **G2** = similitud con umbral; **Estructura** = chequeos internos del clon (entre paréntesis, el resultado del mismo chequeo sobre el original; «= original» si el original tampoco lo cumple); **info** = solo diagnóstico.

| Parte | Validada | PASA | NO PASA | Estado |
|---|---|---|---|---|
| Tablero · tablero_datos.js | 2026-11-24 20:46:09 | 49 | 2 | **NO PASA** |
| Antes/después · antes_despues.js | 2026-11-24 20:46:09 | 12 | 7 | **NO PASA** |
| Matriz RITP · matriz/datos_RITP.js | 2026-11-24 20:46:09 | 15 | 0 | PASA |

<!-- seccion:tablero pasa=49 nopasa=2 fecha=2026-11-24 20:46:09 -->
## Tablero · tablero_datos.js

Validado el 2026-11-24 20:46:09 · clon: `visor/tablero_datos.js` · original: `_original/tablero_datos.js` · **49 PASA · 2 NO PASA** · 8 informativos

| Grupo | Campo | Resultado | Umbral | Estado |
|---|---|---|---|---|
| Estructura | claves y tipos en todos los niveles | iguales | iguales | PASA |
| Estructura | conc en orden CN, LOA, RITP, AVO, PCNP-2 | ok · original: ok | sin casos | PASA |
| Estructura | conc.actos: bases primero, orden por fecha, adj coherente | ok · original: ok | sin casos | PASA |
| Estructura | arts: 22 listas paralelas del mismo largo | ok · original: ok | sin casos | PASA |
| Estructura | arts.id = 'BL:' + num | ok · original: ok | sin casos | PASA |
| Estructura | claves (cod, num) únicas | ok · original: ok | sin casos | PASA |
| Estructura | filas ordenadas por c y por número | ok · original: ok | sin casos | PASA |
| Estructura | sale ascendente, sin autocitas, misma concesión; sw paralela | ok · original: ok | sin casos | PASA |
| Estructura | entra = inversa exacta de sale | ok · original: ok | sin casos | PASA |
| Estructura | nueva ⊆ sale | ok · original: ok | sin casos | PASA |
| Estructura | ci = suma de sw entrantes | ok · original: ok | sin casos | PASA |
| Estructura | cs ≤ 6 y ordenado por n descendente | ok · original: ok | sin casos | PASA |
| Estructura | ca ordenado por k, 1 ≤ k < nº actos | ok · original: ok | sin casos | PASA |
| Estructura | h ordenado por k; tipo conocido; texto ≤ 220 | ok · original: ok | sin casos | PASA |
| Estructura | sub son sub-números del artículo | ok · original: ok | sin casos | PASA |
| Estructura | pr y pr0 suman 1 por concesión (±1e-3); pr0 = 0 si nuevo | ok · original: ok | sin casos | PASA |
| Estructura | ct ≤ 4, uno por otra concesión, ordenado, φ ≥ 0,5 | ok · original: ok | sin casos | PASA |
| Estructura | x, y con máx \|coord\| = 1 | ok · original: ok | sin casos | PASA |
| Estructura | bases: paralelas, cada g una vez, ≤1 por concesión, orden, base[g] coherente, x/y, t (normalizado) | ok · original: ok | sin casos | PASA |
| Estructura | comunidades: n y conc coherentes con cm; 2–4 ejemplos | ok · original: ok | sin casos | PASA |
| G1 | conc: concesiones presentes | 100 % (5/5) | 100 % | PASA |
| G1 | conc.nombre | 100 % (5/5) | 100 % | PASA |
| G1 | conc.largo | 100 % (5/5) | 100 % | PASA |
| G1 | conc.color | 100 % (5/5) | 100 % | PASA |
| G1 | conc.adj | 100 % (5/5) | 100 % | PASA |
| G1 | conc.actos (lista completa) | 100 % (5/5) | 100 % | PASA |
| G1 | conc.actos (elemento a elemento) | 100 % (175/175) | 100 % | PASA |
| info | generado | original 2026-11-24 10:04 · clon 2026-11-24 20:44 | — | info |
| G1 | artículos (cod, num): comunes / unión | 100 % (641/641) | 100 % | PASA |
| G1 | arts.t | 100 % (641/641) | 100 % | PASA |
| G1 | arts.parte | 100 % (641/641) | 100 % | PASA |
| G1 | arts.sub | 100 % (641/641) | 100 % | PASA |
| G1 | arts.nuevo | 100 % (641/641) | 100 % | PASA |
| G1 | arts.sale (como (cod, num)) | 100 % (641/641) | 100 % | PASA |
| G1 | arts.entra (como (cod, num)) | 100 % (641/641) | 100 % | PASA |
| G1 | arts.nueva (como (cod, num)) | 100 % (641/641) | 100 % | PASA |
| G1 | arts.sw (destino → peso) | 100 % (641/641) | 100 % | PASA |
| G1 | arts.ci | 100 % (641/641) | 100 % | PASA |
| G1 | arts.cs | 100 % (641/641) | 100 % | PASA |
| info | arts.cs (sin orden de empates) | 100 % (641/641) | — | info |
| G1 | arts.ca | 100 % (641/641) | 100 % | PASA |
| G1 | arts.h (exacto: acto → ediciones) | 100 % (641/641) | 100 % | PASA |
| G1 | arts.h: conjunto de actos k | 100 % (641/641) | 100 % | PASA |
| G1 | arts.h: nº de ediciones por (artículo, k) | 100 % (537/537) | 100 % | PASA |
| G1 | arts.h: tipo (ediciones alineadas) | 100 % (1802/1802) | 100 % | PASA |
| G1 | arts.h: inciso (ediciones alineadas) | 100 % (1802/1802) | 100 % | PASA |
| G1 | arts.h: texto (ediciones alineadas) | 100 % (1802/1802) | 100 % | PASA |
| G1 | arts.pr (tolerancia 1e-4) | 100 % (641/641) | 100 % | PASA |
| info | arts.pr: dif. máx. · Spearman | 0.00e+00 · ρ = 1.0000 | — | info |
| G1 | arts.pr0 (tolerancia 1e-4) | 100 % (641/641) | 100 % | PASA |
| info | arts.pr0: dif. máx. · Spearman | 0.00e+00 · ρ = 1.0000 | — | info |
| G2 | ct: coincidencia de pares (Jaccard) | 78.25 % (1641/2097) · recall 84.0 % · precisión 91.9 % | ≥ 85 % | **NO PASA** |
| G2 | ct: Spearman de φ en pares comunes | 0.9010 (n=1641) | ≥ 0.8 | PASA |
| G2 | bases: ARI (etiqueta = índice de base) | 0.8962 (n=641) | ≥ 0.8 | PASA |
| info | bases idénticas (mismos miembros) | 75.74 % (178/235) · bases: original 235, clon 235 · t igual en 167/178 | — | info |
| info | bases: tamaños | original {1: 102, 2: 22, 3: 18, 4: 24, 5: 69} · clon {1: 96, 2: 29, 3: 22, 4: 19, 5: 69} | — | info |
| G2 | cm: ARI de comunidades | 0.4259 (n=641) | ≥ 0.6 | **NO PASA** |
| info | comunidades | original: Construcción y conservación (145), Ingeniería y diseño (123), Plazos y extinción (95), Ofertas y garantías (72), Tarifas e inversiones (64), Medio ambiente (63), Multas y expropiaciones (38), Prevención de riesgos (16), Pagos entre el MOP y la sociedad (15), Seguros (10) · clon: Autocontrol y autorización (114), Proyectos y ingeniería (109), Sustentable y mínimo (63), Subsidio y tramo (61), Ofertas y apertura (61), Cobro y tarifario (61), Pagos y garantías (57), Suscripción y subcontratos (54), Prevención y accidentes (51), Costos y contrato (10) | — | info |
| info | x/y: correlación de distancias por pares (Pearson) | 0.2723 (n=641) | — | info |

**Artículos por concesión** (emparejados por (cod, num))

| Concesión | Original | Clon | Comunes | Faltan en el clon | Sobran en el clon |
|---|---|---|---|---|---|
| CN | 120 | 120 | 120 | 0 | 0 |
| LOA | 115 | 115 | 115 | 0 | 0 |
| RITP | 164 | 164 | 164 | 0 | 0 |
| AVO | 119 | 119 | 119 | 0 | 0 |
| PCNP-2 | 123 | 123 | 123 | 0 | 0 |

### Ejemplos de diferencias (hasta 5 por campo)

**ct: coincidencia de pares (Jaccard)**

- solo original: `AVO 1.10.5` → `RITP 1.10.6` φ=0.6
- solo original: `AVO 1.10.8` → `RITP 1.9.12` φ=0.96
- solo original: `AVO 1.11.2` → `RITP 1.13.1` φ=0.67
- solo original: `AVO 1.12.1` → `RITP 1.14.7` φ=0.54
- solo original: `AVO 1.12.2` → `CN 1.11.1` φ=0.56

**bases: ARI (etiqueta = índice de base)**

- base solo en original: ['CN 1.10.6']
- base solo en original: ['RITP 1.10.9']
- base solo en original: ['CN 1.12.3', 'LOA 1.14.1', 'PCNP-2 1.15.4', 'RITP 1.16.2']
- base solo en original: ['AVO 1.8.2', 'CN 1.7.4', 'LOA 1.8.2', 'PCNP-2 1.8.2']
- base solo en original: ['RITP 2.10.1']

<!-- /seccion:tablero -->

<!-- seccion:ad pasa=12 nopasa=7 fecha=2026-11-24 20:46:09 -->
## Antes/después · antes_despues.js

Validado el 2026-11-24 20:46:09 · clon: `visor/antes_despues.js` · original: `_original/antes_despues.js` · **12 PASA · 7 NO PASA** · 5 informativos

| Grupo | Campo | Resultado | Umbral | Estado |
|---|---|---|---|---|
| Estructura | claves y tipos en todos los niveles | iguales | iguales | PASA |
| Estructura | k = 8 y concesiones = las 5 | ok · original: ok | sin casos | PASA |
| Estructura | claves 'BL:' en orden natural; entradas ≤ n | ok · original: ok | sin casos | PASA |
| Estructura | phi null ⇔ nuevo; v0 = [] si nuevo; v0/v1 ≤ 8 sin sí mismo; d, w, inc bien formados | ok · original: ok | sin casos | PASA |
| G1 | k | 100 % (1/1) | 100 % | PASA |
| G1 | concesiones presentes | 100 % (5/5) | 100 % | PASA |
| G1 | n por concesión | 100 % (5/5) | 100 % | PASA |
| info | generado | original 2026-11-24 10:06 · clon 2026-11-24 20:46 | — | info |
| G1 | claves (cod, id): comunes / unión | 90.45 % (540/597) | 100 % | **NO PASA** |
| G1 | w | 82.59 % (446/540) | 100 % | **NO PASA** |
| G1 | inc | 98.52 % (532/540) | 100 % | **NO PASA** |
| G1 | cs | 100 % (540/540) | 100 % | PASA |
| G1 | ce | 100 % (540/540) | 100 % | PASA |
| G1 | d | 89.26 % (482/540) | 100 % | **NO PASA** |
| G1 | nuevo | 100 % (540/540) | 100 % | PASA |
| G1 | dudoso | 98.15 % (530/540) | 100 % | **NO PASA** |
| info | cs (como conjunto) | 100 % (540/540) | — | info |
| info | ce (como conjunto) | 100 % (540/540) | — | info |
| info | d: similitud por palabras de los diffs distintos | media 0.877 · mín 0.000 (n=58) | — | info |
| G2 | phi: Spearman | 0.9300 (n=521) | ≥ 0.8 | PASA |
| info | phi: \|Δ\| ≤ 0,01 | 83.11 % (433/521) | — | info |
| G1 | phi null (unidad nueva) | 100 % (540/540) | 100 % | PASA |
| G2 | v0: solape medio del top-8 | 59.4 % (n=521) | ≥ 60 % | **NO PASA** |
| G2 | v1: solape medio del top-8 | 59.5 % (n=540) | ≥ 60 % | **NO PASA** |

**Entradas por concesión** (emparejadas por (cod, id BL:))

| Concesión | n orig. | n clon | Entradas orig. | Entradas clon | Comunes | Faltan en el clon | Sobran en el clon |
|---|---|---|---|---|---|---|---|
| CN | 307 | 307 | 126 | 134 | 125 | 1: BL:1.9.6 | 9: BL:1.11.7, BL:1.11.7.3, BL:2.2.2, BL:2.2.2.1, BL:2.2.2.5 … |
| LOA | 357 | 357 | 194 | 203 | 192 | 2: BL:2.2.2.3, BL:2.7.1.1 | 11: BL:1.8.8, BL:1.8.8.2, BL:1.11.2, BL:1.12.1, BL:1.12.2.1 … |
| RITP | 289 | 289 | 75 | 80 | 75 | 0 | 5: BL:1.8.3, BL:1.8.4, BL:1.16.1, BL:2.2.2, BL:2.6.1 |
| AVO | 403 | 403 | 93 | 108 | 93 | 0 | 15: BL:1.7.6, BL:1.8.6, BL:1.8.8, BL:1.12.1, BL:1.12.2.1 … |
| PCNP-2 | 391 | 391 | 56 | 68 | 55 | 1: BL:1.8.10.2.1 | 13: BL:1.7.6, BL:1.8.1, BL:1.11.2, BL:2.2.2, BL:2.3.1 … |

### Ejemplos de diferencias (hasta 5 por campo)

**w**

- `CN BL:1.4.5` — original: [2723, 2767] · clon: [2742, 2785]
- `CN BL:1.7.4` — original: [673, 855] · clon: [673, 931]
- `CN BL:1.7.13` — original: [2280, 2330] · clon: [2625, 2752]
- `CN BL:1.7.13.1` — original: [2061, 2112] · clon: [2406, 2534]
- `CN BL:1.8.1.3` — original: [641, 685] · clon: [723, 767]

**inc**

- `LOA BL:2.3.1.8` — original: [8, 0] · clon: [7, 0]
- `LOA BL:2.3.1.8.1` — original: [7, 0] · clon: [6, 0]
- `LOA BL:2.4.5` — original: [45, 0] · clon: [1, 0]
- `RITP BL:1.8.5` — original: [2, 2] · clon: [0, 1]
- `RITP BL:1.8.17` — original: [7, 0] · clon: [2, 0]

**d**

- `CN BL:1.4.5` — original: …a obra, para su aprobación un documento que contenga en", 332], [1, "licitantes o grupos licitantes.”"], [0, "La presentación de este documento indicará los proyectos referenciales que quedan incluidos en la Oferta Técnica. No obstante, … f… · clon: …a obra, para su aprobación un documento que contenga en", 333], [1, "licitantes o grupos licitantes.”"], [0, "La presentación de este documento indicará los proyectos referenciales que quedan incluidos en la Oferta Técnica. No obstante, … f…
- `CN BL:1.7.4` — original: …ablecidas en estas bases y en la Resolución Ambiental de", 109], [0, "Se entenderá por Inspector Fiscal en la etapa de explotación a quien el DGOP le haya encargado fiscalizar …"]] · clon: …ablecidas en estas bases y en la Resolución Ambiental de", 185], [0, "Se entenderá por Inspector Fiscal en la etapa de explotación a quien el DGOP le haya encargado fiscalizar …"]]
- `CN BL:1.7.13` — original: [[0, "… la entrega del Reglamento de Servicio de la Obra \| Cada día \| 1.10.6 \| 20 \| …"], [-1, "1.11.3.2"], [1, "1.11.3.3"], [0, "\| 100 \| No entrega de la Boleta Bancaria de Garantía para la realización de nuevas inversiones. \| Cada D… · clon: [[0, "… deba realizar al Estado. \| Cada día \| Sin perjuicio del Cobro de las garantías establecidas en 1.7.1."], [-1, "1.11.3.2"], [1, "1.11.3.3"], [0, "\| 100 \| No entrega de la Boleta Bancaria de Garantía para la realización de nuevas …
- `CN BL:1.7.13.1` — original: [[0, "… la entrega del Reglamento de Servicio de la Obra \| Cada día \| 1.10.6 \| 20 \| …"], [-1, "1.11.3.2"], [1, "1.11.3.3"], [0, "\| 100 \| No entrega de la Boleta Bancaria de Garantía para la realización de nuevas inversiones. \| Cada D… · clon: [[0, "… deba realizar al Estado. \| Cada día \| Sin perjuicio del Cobro de las garantías establecidas en 1.7.1."], [-1, "1.11.3.2"], [1, "1.11.3.3"], [0, "\| 100 \| No entrega de la Boleta Bancaria de Garantía para la realización de nuevas …
- `CN BL:1.11.1` — original: …200 5 \| 1350 días de constituida la Sociedad Concesionaria \| …"], [1, "31.300"], [0, "En el caso de atraso en el pago de cualquiera de estas cantidades el MOP hará efectivas las garantías establecidas en 1.7.1, y sin perjuicio de lo dispu… · clon: …200 5 \| 1350 días de constituida la Sociedad Concesionaria \|"], [0, "31.300"], [-1, "…"], [0, "En el caso de atraso en el pago de cualquiera de estas cantidades el MOP hará efectivas las garantías establecidas en 1.7.1, y sin perjuicio de…

**dudoso**

- `CN BL:1.7.13.2` — original: 1 · clon: 0
- `CN BL:1.8.1` — original: 1 · clon: 0
- `CN BL:1.11.1` — original: 1 · clon: 0
- `CN BL:2.4.7` — original: 1 · clon: 0
- `LOA BL:1.14.2.1` — original: 1 · clon: 0

**v0: solape medio del top-8**

- `CN BL:1.2.2` solape 0.62 — solo original: ['BL:1.10.3', 'BL:1.3.4', 'BL:1.8.1.1'] · solo clon: ['BL:1.13.4', 'BL:1.4.4', 'BL:1.6.2']
- `CN BL:1.2.3` solape 0.62 — solo original: ['BL:2.3.1.2', 'BL:2.3.1.4', 'BL:2.3.2'] · solo clon: ['BL:1.7.10', 'BL:2.3.2.1', 'BL:2.3.3.1']
- `CN BL:1.3.1` solape 0.75 — solo original: ['BL:1.11.3.1', 'BL:1.11.7.3.4'] · solo clon: ['BL:1.11.4', 'BL:1.4.3']
- `CN BL:1.3.3` solape 0.50 — solo original: ['BL:1.7.10', 'BL:2.2.2.8', 'BL:2.3.1.1', 'BL:2.3.1.2'] · solo clon: ['BL:2.2.2.10', 'BL:2.2.2.11', 'BL:2.3.2.1', 'BL:2.3.2.2']
- `CN BL:1.3.4` solape 0.50 — solo original: ['BL:1.2.3', 'BL:1.3.3', 'BL:2.2.2.5', 'BL:2.2.2.5.2'] · solo clon: ['BL:1.7.9.2.3', 'BL:2.2.2.15', 'BL:2.2.3', 'BL:2.3.1.2']

**v1: solape medio del top-8**

- `CN BL:1.2.2` solape 0.50 — solo original: ['BL:1.10.3', 'BL:1.3.4', 'BL:1.7.21', 'BL:1.8.1.1'] · solo clon: ['BL:1.6.2', 'BL:1.9.9', 'BL:1.9.9.2', 'BL:1.9.9.3']
- `CN BL:1.2.3` solape 0.88 — solo original: ['BL:2.3.2'] · solo clon: ['BL:2.3.3.1']
- `CN BL:1.3.1` solape 0.75 — solo original: ['BL:1.11.9', 'BL:1.2.3'] · solo clon: ['BL:1.4.1', 'BL:1.4.3']
- `CN BL:1.3.3` solape 0.62 — solo original: ['BL:1.7.10', 'BL:2.2.2.8', 'BL:2.3.1.2'] · solo clon: ['BL:2.2.2.10', 'BL:2.2.2.11', 'BL:2.3.2.2']
- `CN BL:1.3.4` solape 0.62 — solo original: ['BL:1.7.21', 'BL:2.2.2.5', 'BL:2.2.2.5.2'] · solo clon: ['BL:2.2.1', 'BL:2.2.3', 'BL:2.3.1.2']

<!-- /seccion:ad -->

<!-- seccion:matriz pasa=15 nopasa=0 fecha=2026-11-24 20:46:09 -->
## Matriz RITP · matriz/datos_RITP.js

Validado el 2026-11-24 20:46:09 · clon: `visor/matriz/datos_RITP.js` · original: `_original/matriz/datos_RITP.js` · **15 PASA · 0 NO PASA** · 15 informativos

| Grupo | Campo | Resultado | Umbral | Estado |
|---|---|---|---|---|
| Estructura | claves y tipos en todos los niveles | iguales | iguales | PASA |
| Estructura | largos: arts = hoja_a_fila = n; Z = n−1 filas de 3; S = n² | ok · original: ok | sin casos | PASA |
| Estructura | hoja_a_fila es una permutación | ok · original: ok | sin casos | PASA |
| Estructura | unidades `a` únicas | ok · original: ok | sin casos | PASA |
| Estructura | S simétrica, entera, diagonal 1000 | ok · original: ok | sin casos | PASA |
| Estructura | x ≤ 420 caracteres; p conocido | ok · original: ok | sin casos | PASA |
| Estructura | cortes 4–16: lab contiguo con K grupos; kw 6; rep ≤ 3; coh; corte = punto medio | ok · original: ok | sin casos | PASA |
| G1 | concesion | 100 % (1/1) | 100 % | PASA |
| info | modelo (modo de vectores) | original baai/bge-m3 · clon baai/bge-m3 | — | info |
| info | cortes.*.nombre (agregado por el clon) | presente | — | info |
| G1 | unidades `a`: comunes / unión | 100 % (169/169) | 100 % | PASA |
| G1 | t | 100 % (169/169) | 100 % | PASA |
| G1 | p | 100 % (169/169) | 100 % | PASA |
| G1 | f | 100 % (169/169) | 100 % | PASA |
| G1 | x | 100 % (169/169) | 100 % | PASA |
| G2 | S: Spearman en pares de unidades comunes | 1.0000 (n=14196) · \|Δ\| medio 0.0 | ≥ 0.8 | PASA |
| info | cortes["4"].lab: ARI | 1.0000 (n=169) | — | info |
| info | cortes["5"].lab: ARI | 1.0000 (n=169) | — | info |
| info | cortes["6"].lab: ARI | 1.0000 (n=169) | — | info |
| info | cortes["7"].lab: ARI | 1.0000 (n=169) | — | info |
| info | cortes["8"].lab: ARI | 1.0000 (n=169) | — | info |
| info | cortes["9"].lab: ARI | 1.0000 (n=169) | — | info |
| info | cortes["10"].lab: ARI | 1.0000 (n=169) | — | info |
| info | cortes["11"].lab: ARI | 1.0000 (n=169) | — | info |
| G2 | cortes["12"].lab: ARI | 1.0000 (n=169) | ≥ 0.6 | PASA |
| info | cortes["13"].lab: ARI | 1.0000 (n=169) | — | info |
| info | cortes["14"].lab: ARI | 1.0000 (n=169) | — | info |
| info | cortes["15"].lab: ARI | 1.0000 (n=169) | — | info |
| info | cortes["16"].lab: ARI | 1.0000 (n=169) | — | info |
| info | orden de hojas: Spearman de la posición | 1.0000 (n=169) | — | info |

**Unidades:** original 169 · clon 169 · comunes 169 · faltan 0 · sobran 0

<!-- /seccion:matriz -->
