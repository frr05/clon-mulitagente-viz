"""Figura de las redes de comunidades por concesión, con estilo de paper (skill figuras-paper).

    python scripts/figura_redes_paper.py      # → MT v4/figuras_paper/fig_02_redes_comunidades.{pdf,png,svg,txt}

Replica el mapa del tablero con los datos del artefacto original (_original/*.js): zonas por comunidad, tamaño por
citas recibidas, y en la fila b los enlaces que crean o destruyen las modificaciones (misma regla que tablero.js).
Reutiliza zonas(), enlaces_cambios(), color_com() y aclarar() de figuras.py.
"""
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\fcoer\.claude\skills\figuras-paper")
import estilo_paper as ep  # noqa: E402

spec = importlib.util.spec_from_file_location("figuras", AQUI / "figuras.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
ep.aplicar()                       # después de importar figuras.py, que trae su propio estilo

SALIDA = AQUI.parents[1] / "figuras_paper"
A, CONC, COM, GS, NC, MODIF = F.A, F.CONC, F.COM, F.GS, F.NC, F.MODIF


def curva(ax, p, q, **kw):
    ax.add_patch(FancyArrowPatch(p, q, connectionstyle="arc3,rad=.22", shrinkA=1.5, shrinkB=2, mutation_scale=4.5, **kw))


def main():
    Q, _ = F.zonas()
    xs, ys = Q[:, 0], Q[:, 1]
    lim = (xs.min() - .04, xs.max() + .04), (ys.min() - .04, ys.max() + .04)
    ENL = F.enlaces_cambios()
    fig, ejes = ep.figura("doble", alto_mm=82, filas=2, columnas=NC, gridspec_kw={"wspace": .05, "hspace": .12})
    textos = []
    for ci in range(NC):
        gs = GS[ci]
        orden = sorted(gs, key=lambda g: -A["ci"][g])
        tam = np.array([1.2 + 2.6 * math.sqrt(A["ci"][g]) for g in orden])
        col = [F.color_com(A["cm"][g]) for g in orden]
        for fila, ax in enumerate(ejes[:, ci]):
            ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_aspect("equal")
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_linewidth(.4); s.set_color("#9a9a9a")
            alfa = .4 if fila == 0 else .1
            for g in gs:
                for h in A["sale"][g]:
                    if h not in A["nueva"][g]:
                        ax.plot([xs[g], xs[h]], [ys[g], ys[h]], color=F.color_com(A["cm"][g]), lw=.2, alpha=alfa, zorder=1)
            cols = col if fila == 0 else [c if g in MODIF else F.aclarar(c, .78) for g, c in zip(orden, col)]
            ax.scatter(xs[orden], ys[orden], s=tam, c=cols, edgecolors="white", linewidths=.2, zorder=2)
            if fila == 1:
                for a, b, tipo, sg in ENL[ci]:
                    p, q = (xs[a], ys[a]), (xs[b], ys[b])
                    if tipo == "cita":
                        curva(ax, p, q, arrowstyle="-|>", color=F.VERDE, lw=.7, zorder=4)
                    else:
                        curva(ax, p, q, arrowstyle="-", color=F.VERDE if sg > 0 else F.ROJO, lw=.5,
                              ls=(0, (2.5, 1.2)) if sg > 0 else (0, (.8, 1)), zorder=3)
        a0 = ejes[0, ci]
        a0.text(0, 1.10, CONC[ci]["nombre"], transform=a0.transAxes, fontweight="bold", fontsize=6.8, va="bottom")
        a0.text(0, 1.02, f"{len(gs)} artículos · {len(CONC[ci]['actos']) - 1} actos",
                transform=a0.transAxes, fontsize=5.6, color="#555555", va="bottom")
        mod = sum(1 for g in gs if g in MODIF)
        nc = sum(1 for e in ENL[ci] if e[2] == "cita")
        ac = sum(1 for e in ENL[ci] if e[2] == "contenido" and e[3] > 0)
        al = sum(1 for e in ENL[ci] if e[2] == "contenido" and e[3] < 0)
        ejes[1, ci].text(0, -.03, f"{mod} de {len(gs)} modificados ({round(100 * mod / len(gs))} %)\n"
                         f"+{nc} citas nuevas\n{ac} se acercan · {al} se alejan",
                         transform=ejes[1, ci].transAxes, fontsize=5.6, va="top", linespacing=1.3)
        textos.append((CONC[ci]["nombre"], mod, len(gs), nc, ac, al))
    for fila, rot in enumerate(("Bases licitadas", "Bases modificadas")):
        ejes[fila, 0].text(-.08, .5, rot, transform=ejes[fila, 0].transAxes, rotation=90, va="center", ha="center")
    ep.letras([ejes[0, 0], ejes[1, 0]], dx=-.17, dy=1.10)
    h = [Line2D([], [], marker="o", ls="", ms=3.6, mfc=F.color_com(i), mec="white", mew=.3, label=COM[i]["t"])
         for i in range(len(F.CAT))]
    otras = " y ".join(COM[i]["t"] for i in range(len(F.CAT), len(COM)))
    h += [Line2D([], [], marker="o", ls="", ms=3.6, mfc=F.OTRAS, mec="white", mew=.3, label=f"Otras ({otras})"),
          Line2D([], [], marker="o", ls="", ms=3.6, mfc=F.aclarar(F.CAT[0], .78), mec="white", label="Artículo no modificado (b)"),
          Line2D([], [], color=F.VERDE, lw=.9, marker=">", ms=2.8, label="Cita nueva"),
          Line2D([], [], color=F.VERDE, lw=.8, ls=(0, (2.5, 1.2)), label="El contenido se acerca"),
          Line2D([], [], color=F.ROJO, lw=.8, ls=(0, (.8, 1)), label="El contenido se aleja")]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(.5, -.20), ncol=4, fontsize=5.8, handletextpad=.3,
               columnspacing=1.2, handlelength=1.6, title="Comunidades temáticas (misma posición en todos los paneles; "
               "tamaño proporcional a √citas recibidas)", title_fontsize=6, alignment="left")
    pie = ("**Fig. 2 | Las cinco concesiones comparten las mismas comunidades temáticas, pero se modifican en lugares "
           "distintos.** **a**, Red de citas entre los artículos x.y.z de las Bases de Licitación originales de cada "
           "concesión. Cada punto es un artículo con sus sub-artículos; su color es la comunidad temática (Louvain sobre la "
           "similitud de contenido de los 641 artículos de las cinco concesiones), su tamaño es proporcional a la raíz de "
           "las citas que recibe y su zona es la misma en todos los paneles. Las líneas son citas entre artículos, del color "
           "de la comunidad que cita. **b**, Como en **a**, pero después de los actos posteriores (circulares aclaratorias, "
           "decretos y convenios): los artículos no modificados se muestran atenuados; las flechas verdes son citas que "
           "aparecen en un acto posterior; las líneas verdes discontinuas unen pares de artículos que pasan a estar entre los "
           "ocho más parecidos entre sí, y las rojas punteadas, pares que dejan de estarlo (margen de 0,02 en el coseno, "
           "neteado por par). Bajo cada panel: artículos modificados y conteo de enlaces. Las comunidades más pequeñas "
           "(Pagos entre el MOP y la sociedad, y Seguros) se agrupan en gris. Datos: tablero «Bases de Licitación · cinco "
           "concesiones», a partir de los árboles de nodos versionados de cada concesión.")
    rutas = ep.guardar(fig, SALIDA, "fig_02_redes_comunidades", pie=pie)
    for t in textos:
        print("  {}: {} de {} modificados · +{} citas · {} se acercan · {} se alejan".format(*t))
    print("  " + str(rutas[1]))


if __name__ == "__main__":
    main()
