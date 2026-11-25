"""Figura de las redes de comunidades con el mapa del tablero del clon, en estilo de paper (skill figuras-paper).

    python scripts/figura_redes_clon.py      # → MT v4/figuras_paper/fig_02_redes_comunidades_clon.{pdf,png,svg,txt}

Replica exactamente el mapa del tablero (visor/index.html, vista «Las Bases», color por comunidad): la posición, el radio
y el color de cada punto se leen del SVG que dibuja plotagents en Edge/Chrome sin ventana. Comunidades, nombres, citas
y cambios salen de visor/tablero_datos.js y visor/antes_despues.js (datos del clon). La fila b agrega los enlaces que
crean o destruyen las modificaciones, con la misma regla que tablero.js.
"""
import importlib.util
import math
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\fcoer\.claude\skills\figuras-paper")
sys.path.insert(0, str(AQUI))
import estilo_paper as ep  # noqa: E402
import comun  # noqa: E402


def modulo(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, AQUI / archivo)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


F = modulo("figuras", "figuras.py")
X = modulo("exportar", "exportar_graficos.py")
ep.aplicar()

SALIDA = AQUI.parents[1] / "figuras_paper"
T = comun.leer_js(comun.VISOR / "tablero_datos.js")
AD = comun.leer_js(comun.VISOR / "antes_despues.js")
A, CONC, COM = T["arts"], T["conc"], T["comunidades"]
NC = len(CONC)
GS = [[g for g in range(len(A["c"])) if A["c"][g] == ci] for ci in range(NC)]
MODIF = {g for g in range(len(A["c"])) if A["h"][g]}
# misma paleta que el tablero (COLOR_COM de tablero.js), por índice de comunidad
COLOR_COM = ["#3b47b5", "#e0a030", "#2aa876", "#d0385e", "#8a55d3", "#1f9bd1", "#e07a5f", "#6b8e23", "#c2459b", "#7a7f99"]
ANCHO_SVG = 879.0
# enlaces de contenido finos y con huecos amplios, para que no se confundan con la flecha continua de cita nueva.
# Patrones en puntos absolutos (sin escalar por el grosor de la línea).
mpl.rcParams["lines.scale_dashes"] = False
LW_CONT = .3
DASH_ACERCA = (0, (2.4, 2.0))     # verde discontinua
DASH_ALEJA = (0, (.5, 1.6))       # roja punteada


def posiciones() -> dict[int, tuple[float, float, float]]:
    """g → (cx, cy, r) leídos del SVG del mapa del tablero, concesión por concesión."""
    nav = X.navegador()
    index = (comun.VISOR / "index.html").resolve().as_uri()
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for ci, c in enumerate(CONC):
            print(f"  [{100 * ci // NC:3d} %] mapa de {c['cod']}", flush=True)
            dom = subprocess.run([nav, "--headless=new", "--disable-gpu", f"--user-data-dir={tmp}", "--window-size=1400,3000",
                                  "--virtual-time-budget=9000", "--dump-dom", f"{index}#c={c['cod']}"],
                                 capture_output=True, timeout=180).stdout.decode("utf-8", "replace")
            svg = X.svgs_de(dom)["mapa"]
            for m in re.finditer(r"<circle[^>]*>", svg):
                el = m.group(0)
                g = re.search(r'data-node="(-?\d+)"', el)
                if not g or int(g.group(1)) < 0:
                    continue
                cx, cy, r = (float(re.search(rf'\b{k}="([\d.]+)"', el).group(1)) for k in ("cx", "cy", "r"))
                out[int(g.group(1))] = (cx, cy, r)
    return out


def curva(ax, p, q, **kw):
    ax.add_patch(FancyArrowPatch(p, q, connectionstyle="arc3,rad=.18", shrinkA=1.5, shrinkB=2, mutation_scale=4.5, **kw))


def main():
    P = posiciones()
    ENL = F.enlaces_cambios(A, CONC, AD)
    xs = np.array([P[g][0] for g in P]); ys = np.array([P[g][1] for g in P])
    lim = (xs.min() - 20, xs.max() + 20), (ys.max() + 20, ys.min() - 20)     # y invertido (SVG)
    fig, ejes = ep.figura("doble", alto_mm=62, filas=2, columnas=NC, gridspec_kw={"wspace": .05, "hspace": .2})
    # radio del SVG (px) → diámetro del marcador (pt): el panel mide ~ (183 mm / 5) de ancho para ANCHO_SVG px
    px_a_pt = (183 / 25.4 * 72 / NC * .93) / (lim[0][1] - lim[0][0])
    resumen = []
    for ci in range(NC):
        gs = [g for g in GS[ci] if g in P]
        orden = sorted(gs, key=lambda g: -P[g][2])
        x = np.array([P[g][0] for g in orden]); y = np.array([P[g][1] for g in orden])
        s = np.array([(2 * P[g][2] * px_a_pt) ** 2 for g in orden])
        col = [COLOR_COM[A["cm"][g] % len(COLOR_COM)] for g in orden]
        for fila, ax in enumerate(ejes[:, ci]):
            ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_aspect("equal")
            ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_linewidth(.4); sp.set_color("#9a9a9a")
            alfa = .32 if fila == 0 else .08
            for g in gs:
                for h in A["sale"][g]:
                    if h in P and h not in A["nueva"][g]:
                        curva(ax, P[g][:2], P[h][:2], arrowstyle="-", color=COLOR_COM[A["cm"][g] % 10], lw=.2,
                              alpha=alfa, zorder=1)
            cols = col if fila == 0 else [c if g in MODIF else F.aclarar(c, .78) for g, c in zip(orden, col)]
            ax.scatter(x, y, s=s, c=cols, edgecolors="white", linewidths=.2, zorder=2)
            if fila == 1:
                for a, b, tipo, sg in ENL[ci]:
                    if a not in P or b not in P:
                        continue
                    if tipo == "cita":
                        curva(ax, P[a][:2], P[b][:2], arrowstyle="-|>", color=F.VERDE, lw=.7, zorder=4)
                    else:
                        curva(ax, P[a][:2], P[b][:2], arrowstyle="-", color=F.VERDE if sg > 0 else F.ROJO, lw=LW_CONT,
                              ls=DASH_ACERCA if sg > 0 else DASH_ALEJA, zorder=3)
        if ci == 0 and "--rotulos" in sys.argv:   # nombres sobre el primer panel (opcional: en el ancho de paper se enciman)
            por = defaultdict(list)
            for g in gs:
                por[A["cm"][g]].append(P[g])
            for k, pts in por.items():
                px = np.median([p[0] for p in pts]); py = np.median([p[1] for p in pts])
                ejes[0, 0].text(px, py, COM[k]["t"], fontsize=3.6, fontweight="bold", color=COLOR_COM[k % 10],
                                ha="center", va="center", zorder=5,
                                bbox={"boxstyle": "round,pad=.12", "fc": "white", "ec": "none", "alpha": .75})
        a0 = ejes[0, ci]
        a0.text(0, 1.13, CONC[ci]["nombre"], transform=a0.transAxes, fontweight="bold", fontsize=6.8, va="bottom")
        a0.text(0, 1.02, f"{len(gs)} artículos · {len(CONC[ci]['actos']) - 1} actos", transform=a0.transAxes,
                fontsize=5.6, color="#555555", va="bottom")
        mod = sum(1 for g in gs if g in MODIF)
        nc = sum(1 for e in ENL[ci] if e[2] == "cita")
        ac = sum(1 for e in ENL[ci] if e[2] == "contenido" and e[3] > 0)
        al = sum(1 for e in ENL[ci] if e[2] == "contenido" and e[3] < 0)
        ejes[1, ci].text(0, -.03, f"{mod} de {len(gs)} modificados ({round(100 * mod / len(gs))} %)\n"
                         f"+{nc} citas nuevas\n{ac} se acercan · {al} se alejan",
                         transform=ejes[1, ci].transAxes, fontsize=5.6, va="top", linespacing=1.3)
        resumen.append((CONC[ci]["nombre"], mod, len(gs), nc, ac, al))
    for fila, rot in enumerate(("Bases licitadas", "Bases modificadas")):
        ejes[fila, 0].text(-.08, .5, rot, transform=ejes[fila, 0].transAxes, rotation=90, va="center", ha="center")
    ep.letras([ejes[0, 0], ejes[1, 0]], dx=-.17, dy=1.13)
    h = [Line2D([], [], marker="o", ls="", ms=3.6, mfc=COLOR_COM[i % 10], mec="white", mew=.3, label=f"{c['t']} ({c['n']})")
         for i, c in enumerate(COM)]
    h += [Line2D([], [], marker="o", ls="", ms=3.6, mfc=F.aclarar(COLOR_COM[0], .78), mec="white", label="Artículo no modificado (b)"),
          Line2D([], [], color=F.VERDE, lw=.9, marker=">", ms=2.8, label="Cita nueva"),
          Line2D([], [], color=F.VERDE, lw=LW_CONT, ls=DASH_ACERCA, label="El contenido se acerca"),
          Line2D([], [], color=F.ROJO, lw=LW_CONT, ls=DASH_ALEJA, label="El contenido se aleja")]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(.5, -.30), ncol=4, fontsize=5.8, handletextpad=.3,
               columnspacing=1.2, handlelength=1.6, title="Comunidades temáticas, entre paréntesis el número de artículos "
               "(misma posición en todos los paneles; tamaño según citas recibidas)", title_fontsize=6, alignment="left")
    pie = ("**Fig. 2 | Las cinco concesiones comparten las mismas comunidades temáticas, pero se modifican en lugares "
           "distintos.** **a**, Red de citas entre los artículos x.y.z de las Bases de Licitación originales de cada "
           "concesión, tal como la dibuja el mapa del tablero. Cada punto es un artículo con sus sub-artículos; su color es "
           "la comunidad temática (Louvain sobre la similitud tf-idf + LSA de los 641 artículos de las cinco concesiones, con "
           "nombres generados a partir de los títulos), su tamaño crece con las citas que recibe y cada comunidad ocupa la "
           "misma zona en todos los paneles. Las líneas son citas entre artículos, del color de la comunidad que cita. "
           "**b**, Como en **a**, pero después de los actos posteriores (circulares aclaratorias, decretos y convenios): los "
           "artículos no modificados se muestran atenuados; las flechas verdes son citas que aparecen en un acto posterior; "
           "las líneas verdes discontinuas unen pares de artículos que pasan a estar entre los ocho más parecidos entre sí, "
           "y las rojas punteadas, pares que dejan de estarlo (margen de 0,02 en el coseno, neteado por par). Bajo cada "
           "panel: artículos modificados y conteo de enlaces. Datos: clon del tablero «Bases de Licitación · cinco "
           "concesiones», generado desde los árboles de nodos versionados.")
    rutas = ep.guardar(fig, SALIDA, "fig_02_redes_comunidades_clon", pie=pie)
    for r in resumen:
        print("  {}: {} de {} modificados · +{} citas · {} se acercan · {} se alejan".format(*r))
    print(f"  [100 %] {rutas[1]}")


if __name__ == "__main__":
    main()
