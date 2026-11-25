# ESPEC: contrato del clon «Bases de Licitación · cinco concesiones»

Este archivo es la especificación que comparten los agentes. La sacamos por ingeniería inversa del artefacto publicado (https://claude.ai/artifact/UNaGuu1GPAcwyVHBTUMmTF). Sus 13 archivos están en `_original/` y tienen el mismo sha256 que los publicados.

## 0. Rutas y entradas

| Qué | Ruta (relativa a `clon-bases-licitacion/`) |
|---|---|
| Original (referencia de solo lectura) | `_original/` |
| Datos de entrada | `entrada/data/<ID>/` (ver abajo) |
| Módulo de citas | `entrada/grafo/numerales.py`, con `citas()`, `clave_numero()`, `orden_numero()`, `RE_CITA` |
| Utilidades comunes | `scripts/comun.py` (lo mantiene el orquestador: **no lo edites**; si te falta algo, ponlo en tu script) |
| Validación | `scripts/validar.py [tablero|ad|matriz|todo]` → `VALIDACION.md` |
| Salida | `visor/tablero_datos.js`, `visor/antes_despues.js`, `visor/matriz/datos_RITP.js` |

**Por qué `entrada/`.** Es una exportación (`git archive`) de `arbol-de-nodos` en el commit `4e5f9d5^`, es decir, como estaba el 24/11 antes de las 15:26. El original se generó el 2026-11-24 a las 10:04. Más tarde ese mismo día se reemplazó el árbol de RITP, así que hoy `arbol-de-nodos/data/RITP` ya no es el árbol que usó el original. Las otras cuatro concesiones no cambiaron.

### Árbol que corresponde a cada concesión

`comun.version_reciente()` elige, por `generado`, la versión más reciente entre la carpeta base y `versiones/*`:

| ID | Árbol elegido | Actos | Notas |
|---|---|---|---|
| CN | base (11-19 00:36) | 76 | |
| LOA | `versiones/version-2` (11-18 18:25) | 13 | Coincide con los 13 actos del original. La v2 **no** trae `fragmentos/`, así que se usan los de la base. Ojo: en la v2 el acto D01 se divide en A1 (Bases) y A2 (resolución) |
| RITP | `versiones/2026-11-11` (11-11 13:05) | 17 | 290 nodos `articulo`; el `n` de AD es 289. Tiene `EMBEDDINGS_RITP.npz` y `CHUNKS_RITP.jsonl` (bge-m3, en la carpeta base) |
| AVO | base | 31 | |
| PCNP-2 | base | 38 | |

### Esquema de `nodos_versionados.json` (`mt-nodos-v1`)

Campos de primer nivel: `{generado, concesion:{id,nombre}, actos:[{id,tipo,numero,fecha,nombre,documento,paginas}], raices, nodos:[...]}`.

**Nodo.** Todos tienen `{id, tipo, titulo, ruta, hijos[], padre}`. Algunos tienen además `numero`, `agregado_por`/`eliminado_por` (un dict de acto), `fragmento`, `ajeno`, `tabla` y `versiones[]`.

**Tipos de nodo:**
- `raiz`, `portada` (BL:0), `parte` (BL:1, BL:A1), `capitulo` (BL:1.8);
- `articulo` (BL:1.8.5; un sub-artículo BL:1.8.5.1 tiene como padre un artículo);
- `inciso` (BL:1.8.5-i2), `inciso_eliminado` (-eN), `instruccion` (-insN), `aclaracion` (-aN);
- `acto_posterior` y `formalidad` (su id es el del fragmento);
- `tabla` (TABLA:…), `tema` (TEMA:…), `ficha`.

**Versión:** `{texto, vigente, fecha_desde, fecha_hasta, acto:{id,tipo,numero,fecha,nombre}, documento, paginas, lineas, fuente, relacion, operacion, reemplazado_por, orden, cuenta}`.

- **`relacion`:** original, modificacion, eliminado, aclara, instruccion, acto_posterior, tabla, formalidad, ficha.
- **`operacion`:** null, reemplaza_texto, reemplaza_parrafo, reemplaza_articulo, agrega_texto, agrega_parrafo, agrega_articulo, elimina_texto, elimina.
- **Orden de las versiones:** `orden` descendente, es decir, la más nueva primero. La vigente, si existe, es `versiones[0]`.
- **Acto de las Bases:** el de `tipo == "bases licitacion"`.
- **Texto de un artículo:** no está en el nodo `articulo`; está en sus incisos.

### Otras entradas

- **`actos.csv`:** separador `;`, codificación `utf-8-sig`, columnas `acto;documento;pag_inicio;pag_fin;tipo;numero;fecha;origen;titulo`.
- **`fragmentos/<DOC>.json`:** `{documento, fragmentos:[{id, acto, lineas, pags, refs:["1.8.3.2",…], verbo, ajeno, consulta?}]}`. **`refs` son las citas que hacen los actos.**

### Regla de citas del grafo publicado (`arbol-de-nodos/grafo/armar_grafo.py`, `aristas_citas`, l. 253–286)

- **Artículo → artículo:** por cada `inciso` con id `BL:…`, se aplica `citas(texto vigente[:1500])`. Cada coincidencia pasa por `clave_numero` y se lleva a su artículo. Las autocitas se descartan.
- **Acto → artículo:** desde `fragment.refs`. Si no hay fragmentos, se aplica la misma regex al texto vigente de `acto_posterior`, `instruccion`, `aclaracion` y `formalidad`.
- Se deduplica por (origen, destino, tipo).
- **Es solo un punto de partida.** El original pudo contar distinto: por ejemplo `sw` (el peso) indica que cuenta repeticiones. Deduce la regla que reproduzca el original.

## 1. `tablero_datos.js` → `window.TAB`

**Formato del archivo:** `window.TAB = ` + `json.dumps(obj, ensure_ascii=False, separators=(",",":"))` + `";\n"`. Usa `comun.escribir_js`.

**Orden de concesiones:** `CN, LOA, RITP, AVO, PCNP-2` (índice `ci`). Un índice de acto `k` apunta a `TAB.conc[ci].actos`, y `k = 0` son las Bases.

### Campos de primer nivel

- `generado`: `"YYYY-MM-DD HH:MM"`.
- **`conc[ci]`:** `{cod, nombre, largo, color, adj, actos:[[nombre,"YYYY-MM-DD",tipo]]}`.
  - Los nombres, el largo y los colores son constantes y están en `comun.CONC`.
  - `actos` va ordenado por fecha.
  - `tipo` va en minúsculas, sin tildes y sin número. Valores: bases licitacion, circular aclaratoria, decreto adjudicacion, publicacion diario oficial, convenio complementario, resolucion, puesta en servicio, reglamento servicio, decreto supremo, recepcion ofertas, oferta economica, precalificacion, compradores bases, llamado licitacion, otro.
  - El primer acto es `["Bases licitacion","1999-07-01","bases licitacion"]`.
  - `adj` es el índice del acto «decreto adjudicacion».
  - Valores del original: CN adj=7 (76 actos), LOA 12 (13), RITP 6 (17), AVO 26 (31), PCNP-2 10 (38).

### `arts`: 22 listas paralelas de largo N = 641

Las filas van ordenadas por `c` y después por el orden del artículo. Filas por concesión: CN 120, LOA 115, RITP 164, AVO 119, PCNP-2 123.

Una fila es un artículo de nivel x.y.z, con sus sub-artículos plegados. Hay 17 filas x.y.z.w, en RITP 2.3.2.x.

| Clave | Tipo | Significado |
|---|---|---|
| `c` | int | Índice de concesión |
| `id` | str | `"BL:1.2.1"` |
| `num` | str | `"1.2.1"` |
| `t` | str | Título. Los agregados llevan `"[artículo agregado]"` |
| `parte` | str | Administrativas (443) / Técnicas (170) / Económicas (28) |
| `x`, `y` | float, 4 decimales | Posición 2D en el espacio de contenido común a las 5 concesiones, con máx \|coord\| = 1 |
| `pr` | float, 5 decimales | PageRank en la red de citas vigente; suma 1 dentro de cada concesión |
| `pr0` | float | PageRank en las Bases originales; vale 0.0 si el artículo es nuevo |
| `sale` | list[g], ascendente | Artículos que cita, dentro de la misma concesión y sin autocitas |
| `sw` | list[int] | Paralela a `sale`: peso (cuántas citas) |
| `entra` | list[g] | La inversa exacta de `sale` (1964 aristas) |
| `ci` | int | Suma de los `sw` que apuntan a g |
| `cs` | [[subnum, n]] | Cómo se reparten las citas recibidas entre sus sub-artículos. Ordenado por n descendente y **cortado a los 6 primeros** |
| `ca` | [[k, n]] | Citas que recibe desde actos (k ≥ 1), ordenado por k |
| `h` | [[k, [[tipo, inciso, texto≤220]]]] | Historia de cambios ordenada por k. Ver abajo |
| `sub` | list[str] | Números de los sub-artículos plegados |
| `nueva` | list[g] | Subconjunto de `sale`: las citas que aparecen por primera vez en un acto posterior |
| `nuevo` | 0/1 | Artículo agregado por un acto posterior. Hay 5: CN 1.7.21 y 1.9.11; RITP 1.3.3 y 2.3.2.17; PCNP-2 1.12.8 |
| `ct` | [[g, φ]], ≤ 4 | El más parecido en cada una de las otras concesiones, con φ ≥ 0.5 (2 decimales), uno por concesión y ordenado por concesión |
| `base` | int | Índice en `bases` |
| `cm` | int 0–9 | Comunidad |

**Tipos de `h`, con sus conteos:** reemplaza_parrafo 496, reemplaza_texto 458, reemplaza_articulo 314, agrega 295, agrega_parrafo 116, agrega_articulo 79, elimina 22, agrega_texto 16, elimina_texto 6.
- El `inciso` es texto libre, por ejemplo `"1.2.2 ¶21"`, `"Tabla de la pág. 3"` o `"Cuadro: Resumen Inversiones Adicionales"`.

### `bases` y `comunidades`

- **`bases`:** listas paralelas de largo 235. `{m:[[g…]], t:[str], x:[…], y:[…]}`.
  - `m` tiene a lo más un artículo por concesión, ordenado por concesión. Cada g aparece una sola vez. Las bases van ordenadas por el g de su primer miembro.
  - Tamaños: 102 de tamaño 1, 22 de 2, 18 de 3, 24 de 4 y 69 de 5.
  - `x` e `y` son el promedio de sus miembros.
  - `t` es el título más frecuente entre los miembros.
  - Se infiere que salen de mejores pares recíprocos y una agrupación.
- **`comunidades`:** 10 elementos `{n, t, conc, ej:[2–4 títulos]}`.
  - Son Louvain sobre la similitud de contenido, las mismas para las 5 concesiones.
  - Nombres del original: Construcción y conservación (145), Ingeniería y diseño (123), Plazos y extinción (95), Ofertas y garantías (72), Tarifas e inversiones (64), Medio ambiente (63), Multas y expropiaciones (38), Prevención de riesgos (16, conc = 4), Pagos entre el MOP y la sociedad (15), Seguros (10).

## 2. `antes_despues.js` → `window.ANTES_DESPUES`

Estructura: `{generado, k:8, concesiones:{COD:{n, arts:{"BL:<num>": ART}}}}`.

- **`n`:** total de unidades de artículo de la concesión, contando cada sub-artículo. Valores: CN 307, LOA 357, RITP 289, AVO 403, PCNP-2 391.
- **`arts`:** solo las unidades que cambiaron o son nuevas, con claves en orden natural. Entradas: CN 126, LOA 194, RITP 75, AVO 93, PCNP-2 56.

**Campos de `ART`:**
- **`phi`:** coseno entre el antes y el después (3 decimales); es null si y solo si la unidad es nueva.
- **`w`:** [palabras antes, palabras después].
- **`inc`:** [incisos agregados, incisos eliminados].
- **`v0` / `v1`:** los 8 [id, cos] más parecidos dentro de la concesión, en el original y en el vigente (sin contarse a sí mismo). `v0` es `[]` si la unidad es nueva.
- **`cs` / `ce`:** citas nuevas que hace o que recibe, como [[id, k]].
- **`d`:** diff por palabras, una lista de `[op, texto]` con op −1, 0 o 1.
  - El contexto sin cambios se acorta con «…».
  - Un segmento de más de 120 palabras queda como `[op, primeras_120, n_omitidas]`.
  - Puede ser `[]` o `[[0,"…"]]`.
- **`nuevo`:** `1`; la clave solo aparece si vale 1.
- **`dudoso`:** `1`; la clave solo aparece si vale 1. Marca un texto más corto que podría deberse a una extracción incompleta.

## 3. `matriz/datos_RITP.js`

Formato: dos líneas, `window.MATRIZ = window.MATRIZ || {};` y `window.MATRIZ["RITP"] = {...};`.

Campos: `{concesion, modelo:"baai/bge-m3", arts:[169 {a,t,p,f,x}], hoja_a_fila:[169], Z:[168 [a,b,dist]], cortes:{"4".."16":{lab,kw,rep,coh,corte}}, S:[169*169 int]}`.

- **`arts`:** van en orden de hoja del dendrograma.
  - `a` es el número (x, x.y o x.y.z, y también A1–A4 y 3).
  - `p` es Administrativas, Técnicas, Económicas o Anexos.
  - `f` es cuántos fragmentos se promediaron.
  - `x` es el texto, de 420 caracteres como máximo.
- **`S`:** coseno × 1000 en orden de fila. Es simétrica y su diagonal vale 1000.
- **`Z`:** Ward al estilo de scipy, sin la columna de conteo, sobre los índices originales. Distancia = √(2 − 2·cos) entre promedios normalizados.
- **`cortes[K]`:**
  - `lab`: grupos contiguos en orden de fila.
  - `kw`: 6 términos tf-idf por grupo.
  - `rep`: las 3 filas con mayor similitud media dentro del grupo.
  - `coh`: la similitud media entre pares del grupo.
  - `corte`: el punto medio entre `Z[-K][2]` y `Z[-K+1][2]`.
- Los nombres de los 12 temas (`RES`) están escritos a mano en `matriz/index.html`. El clon agrega `nombre` (una lista por corte) generado automáticamente.

## 4. Validación (`scripts/validar.py`)

**Emparejamiento.** Por `(cod, num)` y por id `BL:`, nunca por índice. Los índices `g` se traducen a `(cod, num)`.

**Grupo 1, deterministas: tienen que calzar exactos.**
- `conc`.
- El conjunto de artículos con `t`, `parte`, `sub` y `nuevo`.
- `sale`, `sw`, `entra`, `ci`, `cs`, `nueva` y `ca`.
- `h`.
- `pr` y `pr0`, con una tolerancia de 1e-4.
- En AD: `n`, las claves, `w`, `inc`, `cs`, `ce`, `d`, `nuevo` y `dudoso`.
- En la matriz: las unidades y sus `a`, `t`, `p`, `f` y `x`.

**Grupo 2, similitud: se valida con métricas de acuerdo.**
- Spearman de φ en `ct`, coincidencia de los pares `ct`, ARI de `bases`, ARI de `cm`.
- Solape del top-8 de `v0`/`v1`, Spearman de `phi`.
- Spearman de `S`, ARI de `cortes["12"].lab`.

## 5. Frontend

El frontend se reescribe a partir de `_original/` usando ingeniería inversa: hay que leer `tablero.js`, `matriz/index.html`, `nav.js` y los CSS.

**Qué se conserva (es la interfaz que usan los datos y los demás archivos):**
- los mismos ids del DOM;
- el mismo estado en el hash (`#c=COD&f=lic|con&t=…&m=actos&l=no&co=…&v=cambios|todo&art=COD/num`);
- las mismas vistas, el mismo contrato de datos y la misma API de plotagents: `plotagents.render(el, spec)` devuelve `{update, destroy, svg}`.

**Qué se puede cambiar:** el código, que se escribe nuevo. No copies archivos. También se pueden corregir defectos conocidos:
- los colores de «parte» del CSS no son los del JS;
- hay código muerto en las ramas `S.conc < 0`.

`plotagents.js` y `logos/` ya están copiados en `visor/`.
