# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es

Es un clon, hecho por ingeniería inversa, del artefacto «Bases de Licitación · cinco concesiones» (https://claude.ai/artifact/UNaGuu1GPAcwyVHBTUMmTF). Ese artefacto es un tablero estático sobre las Bases de Licitación de cinco concesiones viales: CN, LOA, RITP, AVO y PCNP-2.

El clon tiene dos partes:
- **Generador:** scripts en Python que rehacen los tres archivos de datos del artefacto a partir de los árboles de nodos.
- **Frontend:** reescrito desde cero, con el mismo comportamiento que el original.

Para saber si funciona, se mide si **entrega los mismos valores que el artefacto**, con `scripts/validar.py`. Todo el texto (UI, código, informes) va en español.

`ESPEC.md` es el contrato completo. Ahí están el esquema de cada campo de los tres `.js` y las reglas deducidas. Léelo antes de tocar un generador.

## Comandos

```bash
python scripts/generar.py                 # regenera los 3 .js y valida; log en ../armar_clon.log
python scripts/generar.py --sin-validar
python scripts/05_tablero.py              # → visor/tablero_datos.js (~15 s)
python scripts/06_antes_despues.py        # → visor/antes_despues.js
python scripts/07_matriz.py --vectores npz --salida visor/matriz/datos_RITP.js   # bge-m3 (el que pasa)
python scripts/07_matriz.py               # tf-idf + LSA → no pasa la validación; solo para comparar
python scripts/validar.py [tablero|ad|matriz|todo] [--detalle N] [--clon-dir RUTA] [--salida RUTA]
```

- **Sin build ni tests:** no hay build, ni linter, ni tests unitarios. La prueba es `validar.py`, que escribe `VALIDACION.md`. Con una sola parte, actualiza solo su sección del informe.
- **Revisar `validar.py`:** `python scripts/validar.py todo --clon-dir _original` tiene que dar 100 % / PASA en todo.
- **Abrir las páginas:** `visor/index.html` y `visor/matriz/index.html` se abren con doble clic, sin servidor.
- **Ver errores de JS:** no hay Node. Usa Chrome o Edge en modo headless:
  1. Copia `visor/` a una carpeta temporal.
  2. Agrega en `<head>` un `window.onerror` que escriba el error en un atributo de `<html>`.
  3. Corre `--dump-dom` y busca el atributo con grep.

  Usa un `--user-data-dir` propio: dos instancias en paralelo con el mismo perfil devuelven un DOM vacío.

## Arquitectura

**Entradas: `entrada/`, nunca `../arbol-de-nodos/` directo.**
- `entrada/` es un `git archive` de `arbol-de-nodos` en el commit `4e5f9d5^`. Así estaban los datos el 24/11 antes de las 15:26, y el original se generó ese día a las 10:04.
- Después de eso se reemplazó el árbol de RITP, así que con los datos actuales el clon no calzaría.
- `comun.version_reciente(cid)` elige el árbol con el `generado` más reciente entre la carpeta base y `versiones/*`. Para LOA elige `version-2` (sin `fragmentos/`, que se toman de la base). Para RITP elige `versiones/2026-11-11`.
- `entrada/grafo/numerales.py` aporta `citas()` y `clave_numero()`, y se importa desde `comun`.

**`scripts/comun.py` es la base compartida de los generadores:**
- carga de árboles, actos y fragmentos;
- `leer_js`/`original()` para leer los `.js` del original;
- `escribir_js` (formato `window.X = {json compacto};`);
- `vectores()` (tf-idf + LSA, o vectores ya calculados);
- `Avance`, que muestra % y tiempo restante.

**Los campos de cada `.js` se dividen en dos grupos (ESPEC §4):**
- **Grupo 1, deterministas.** Actos, artículos, citas (`sale`/`sw`/`entra`/`ci`/`cs`/`nueva`/`ca`), PageRank `pr`/`pr0`, historia `h`; en AD `w`, `inc`, `d`, `cs`, `ce`. **Tienen que calzar exacto con el original.** Si algo no calza, es una regla mal deducida.
- **Grupo 2, similitud.** `x`/`y`, `ct`, `bases`, comunidades `cm`, `phi`, `v0`/`v1`, y en la matriz `S`/`Z`/`cortes`. No pueden calzar exacto; se validan con métricas de acuerdo (Spearman, ARI, solape del top-8).
- Hoy el tablero y el antes/después usan tf-idf + LSA. La matriz usa los vectores bge-m3 de `entrada/data/RITP/EMBEDDINGS_RITP.npz`, que son los mismos que usó el original.

**Decisiones tomadas por el usuario. No las reviertas sin preguntarle:**
- **Similitud:** tf-idf para el tablero y el antes/después; bge-m3 solo para la matriz de RITP.
  - Se probó bge-m3 en AVO (24/11): `EMBEDDINGS_AVO.npz` está en `../Arbol-Rutas-`, generado con `python main.py embeddings --proyecto AVO`.
  - El antes/después de AVO calza **peor** con bge-m3 que con tf-idf: Spearman de phi 0,29 contra 0,86, y solape de vecinos 30 % contra 62 %. El original no tenía vectores de AVO, así que usó una similitud léxica.
  - Por eso no hay que vectorizar CN, LOA ni PCNP-2. Lo que falta de similitud (`ct`, `cm`) se afina con tf-idf.
  - Los chunks se dejan como están. Los de LOA salieron de un árbol más nuevo (23/11) que el del clon (18/11).
- **x/y del mapa:** cada comunidad del clon se empareja con una del original, por Hungarian sobre los artículos que comparten. Después se traslada a su centroide en el artefacto y se escala a su radio RMS. Es un uso deliberado de valores del original.
- **`estilo.css`:** los colores de «parte» se unificaron con los del JS, así que Económicas quedó en rojo.

**Frontend (`visor/`):**
- **Archivos:** `index.html`, `tablero.js`, `tablero.css`, `estilo.css`, `nav.js`, `nav.css` y `matriz/index.html` se reescribieron desde `_original/`.
- **Compatibilidad:** conservan los ids del DOM, el estado en el hash (`#c=COD&f=…&art=COD/num`) y el contrato de datos.
- **Gráficos:** `plotagents.js` es una librería MIT de terceros que se usa tal cual. Su API es `plotagents.render(el, spec)` y devuelve `{update, destroy, svg}`.
- **Orden de carga:** `tablero_datos.js`, `antes_despues.js`, `plotagents.js`, `tablero.js`, `nav.js`. Si falta un archivo de datos, la página entera queda en blanco.

**`_original/` es solo de lectura.** Son los 13 archivos del artefacto, con el mismo sha256 que la versión publicada. Sirve de referencia para la ingeniería inversa y para `validar.py`.
