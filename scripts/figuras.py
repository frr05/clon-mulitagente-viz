"""Figuras académicas (PDF vectorial + PNG 300 dpi) con los datos del artefacto original.

    python scripts/figuras.py            # → figuras/fig_XX_*.pdf|png

Datos: _original/tablero_datos.js (window.TAB) y _original/antes_despues.js. Colores: paleta de referencia del
skill dataviz (categórica en orden fijo; secuencial azul; divergente azul–rojo con punto medio gris).
"""
import math
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

SALIDA = comun.RAIZ.parent / "figuras_bases_licitacion"   # carpeta aparte, fuera del clon (MT v4/)
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
OTRAS = "#a3a29c"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIV = ["#1c5cab", "#6da7ec", "#f0efec", "#ec8a85", "#c0302f"]
TINTA, TINTA2, LINEA = "#0b0b0b", "#52514e", "#d9d8d3"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "axes.titlesize": 9.5, "axes.titleweight": "bold",
    "axes.labelsize": 8.5, "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA, "xtick.color": TINTA2,
    "ytick.color": TINTA2, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": .6,
    "xtick.major.width": .6, "ytick.major.width": .6, "legend.frameon": False, "legend.fontsize": 8,
    "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": .04, "pdf.fonttype": 42,
})
ANCHO = 6.3  # pulgadas (16 cm, una columna de la memoria)

# ------------------------------------------------------------------ datos
T = comun.original("tablero_datos.js")
AD = comun.original("antes_despues.js")
A, CONC, COM = T["arts"], T["conc"], T["comunidades"]
N = len(A["c"])
NC = len(CONC)
GS = [[g for g in range(N) if A["c"][g] == ci] for ci in range(NC)]
NOM = [c["nombre"] for c in CONC]
NOM2 = [n.replace(" ", "\n", 1).replace("–", "–\n", 1) if len(n) > 12 else n for n in NOM]   # cabeceras en 2 líneas


def fecha(s):
    return date.fromisoformat(s)


def fase(ci, k):
    act, adj = CONC[ci]["actos"], CONC[ci]["adj"]
    if k >= adj:
        return "con"
    if "publicacion diario oficial" in act[k][2] and act[k][1] == act[adj][1]:
        return "con"
    return "lic"


# un «cambio» = un acto que modifica un artículo; una «edición» = cada inciso tocado por ese acto
CAMBIOS = []
for g in range(N):
    ci = A["c"][g]
    for k, eds in A["h"][g]:
        # años respecto de la adjudicación (la fecha de las Bases falta en algunas concesiones, p. ej. AVO)
        fa, fk = fecha(CONC[ci]["actos"][CONC[ci]["adj"]][1]), fecha(CONC[ci]["actos"][k][1])
        CAMBIOS.append({"g": g, "ci": ci, "k": k, "ed": len(eds), "fase": fase(ci, k),
                        "anios": (fk - fa).days / 365.25})
MODIF = {g for g in range(N) if A["h"][g]}


def color_com(i):
    return CAT[i] if i < len(CAT) else OTRAS


def guardar(fig, nombre):
    SALIDA.mkdir(exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(SALIDA / f"{nombre}.{ext}")
    plt.close(fig)
    print("  ", nombre)


def leyenda_comunidades(fig, y=0.0, ncol=5):
    h = [Line2D([], [], marker="o", ls="", ms=5.5, mfc=color_com(i), mec="white", mew=.6,
                label=COM[i]["t"]) for i in range(len(CAT))]
    otras = " y ".join(COM[i]["t"] for i in range(len(CAT), len(COM)))
    h.append(Line2D([], [], marker="o", ls="", ms=5.5, mfc=OTRAS, mec="white", mew=.6, label=f"Otras ({otras})"))
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(.5, y), ncol=ncol, handletextpad=.2,
               columnspacing=1.0, fontsize=7.2)


# ------------------------------------------------------------------ figura 1: redes por concesión
def zonas(iter_: int = 400):
    """Como el tablero: cada comunidad ocupa una zona fija (la misma en las cinco concesiones). El centro parte de la
    mediana de la comunidad en el espacio de contenido; las zonas se separan sin solaparse y cada artículo conserva
    su dirección desde el centro, con la distancia escalada al radio de la zona."""
    P = np.c_[A["x"], A["y"]]
    cm = np.array(A["cm"])
    K = len(COM)
    cen = np.array([np.median(P[cm == i], axis=0) for i in range(K)])
    rad = np.array([.16 * math.sqrt(max(np.bincount(A["c"], weights=(cm == i))) / 40) + .05 for i in range(K)])
    for _ in range(iter_):
        for i in range(K):
            for j in range(i + 1, K):
                d = cen[j] - cen[i]; dist = np.linalg.norm(d) or 1e-6
                falta = rad[i] + rad[j] + .03 - dist
                if falta > 0:
                    cen[i] -= d / dist * falta / 2; cen[j] += d / dist * falta / 2
    Q = np.zeros_like(P)
    for i in range(K):
        m = cm == i
        off = P[m] - np.median(P[m], axis=0)
        r = np.linalg.norm(off, axis=1)
        esc = rad[i] / (np.quantile(r, .9) or 1)
        Q[m] = cen[i] + off * esc
    return Q, cen


VERDE, ROJO = "#0f8a4f", "#c0302f"   # enlaces que crea (verde) o destruye (rojo) una modificación
DELTA = 0.02


def enlaces_cambios(A=A, CONC=CONC, AD=AD):
    """Igual que ENLACES en tablero.js: citas nuevas (AD.cs) y pares que entran/salen del top-8 de parecido
    (v0 → v1, con margen DELTA), neteados por par. → {ci: [(a, b, tipo, signo)]}. Por defecto, datos del original."""
    pos = {}
    for g in range(len(A["c"])):
        pos[(A["c"][g], A["num"][g])] = g
        for s in A["sub"][g]:
            pos[(A["c"][g], s)] = g

    def g_de(ci, id_):
        num = id_.split(":", 1)[-1]
        while (ci, num) not in pos and "." in num:
            num = num.rsplit(".", 1)[0]
        return pos.get((ci, num))

    out = {}
    for ci, c in enumerate(CONC):
        neto, citas = defaultdict(int), {}
        for id_, a in AD["concesiones"][c["cod"]]["arts"].items():
            ga = g_de(ci, id_)
            if ga is None:
                continue
            for b, _k in a.get("cs") or []:
                gb = g_de(ci, b)
                if gb is not None and gb != ga:
                    citas.setdefault((ga, gb), (ga, gb, "cita", 1))
            m0, m1 = dict(map(tuple, a.get("v0") or [])), dict(map(tuple, a.get("v1") or []))
            if not m0 or not m1:
                continue
            min0, min1 = min(m0.values()), min(m1.values())
            for lista, otra, mn, sg in ((m0, m1, min1, -1), (m1, m0, min0, +1)):
                for b, p in lista.items():
                    if b not in otra and p >= mn + DELTA:
                        gb = g_de(ci, b)
                        if gb is not None and gb != ga:
                            neto[tuple(sorted((ga, gb)))] += sg
        out[ci] = list(citas.values()) + [(a, b, "contenido", int(np.sign(v))) for (a, b), v in neto.items() if v]
    return out


def aclarar(hexcol, f):
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(int(v + (255 - v) * f) for v in (r, g, b))


def curva(ax, p, q, **kw):
    from matplotlib.patches import FancyArrowPatch
    ax.add_patch(FancyArrowPatch(p, q, connectionstyle="arc3,rad=.22", shrinkA=2, shrinkB=3, mutation_scale=7, **kw))


def fig_redes():
    from matplotlib.patches import FancyArrowPatch  # noqa: F401
    Q, _ = zonas()
    xs, ys = Q[:, 0], Q[:, 1]
    lim = (xs.min() - .05, xs.max() + .05), (ys.min() - .05, ys.max() + .05)
    ENL = enlaces_cambios()
    fig, ejes = plt.subplots(2, NC, figsize=(ANCHO * 1.6, 4.9))
    for ci in range(NC):
        gs = GS[ci]
        orden = sorted(gs, key=lambda g: -A["ci"][g])
        tam = np.array([5 + 7 * math.sqrt(A["ci"][g]) for g in orden])
        col = [color_com(A["cm"][g]) for g in orden]
        for fila, ax in enumerate(ejes[:, ci]):
            ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_aspect("equal")
            ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(True); s.set_color(LINEA); s.set_linewidth(.6)
            base_alpha = .45 if fila == 0 else .12
            for g in gs:   # citas de las Bases, del color de la comunidad que cita
                for h in A["sale"][g]:
                    if h in A["nueva"][g]:
                        continue
                    ax.plot([xs[g], xs[h]], [ys[g], ys[h]], color=color_com(A["cm"][g]), lw=.3, alpha=base_alpha, zorder=1)
            if fila == 0:
                ax.scatter(xs[orden], ys[orden], s=tam, c=col, edgecolors="white", linewidths=.35, zorder=2)
            else:
                cols = [c if g in MODIF else aclarar(c, .75) for g, c in zip(orden, col)]
                ax.scatter(xs[orden], ys[orden], s=tam, c=cols, edgecolors="white", linewidths=.35, zorder=2)
                for a, b, tipo, sg in ENL[ci]:
                    p, q = (xs[a], ys[a]), (xs[b], ys[b])
                    if tipo == "cita":
                        curva(ax, p, q, arrowstyle="-|>", color=VERDE, lw=1.0, zorder=4)
                    else:
                        curva(ax, p, q, arrowstyle="-", color=VERDE if sg > 0 else ROJO, lw=.75,
                              ls=(0, (3, 1.5)) if sg > 0 else (0, (1, 1.2)), zorder=3)
        a0 = ejes[0, ci]
        n_act = len(CONC[ci]["actos"]) - 1
        a0.set_title(NOM[ci], loc="left", pad=12, fontsize=9)
        a0.text(0, 1.012, f"{len(gs)} artículos · {n_act} actos", transform=a0.transAxes,
                fontsize=6.8, color=TINTA2, va="bottom")
        mod = sum(1 for g in gs if g in MODIF)
        nc = sum(1 for e in ENL[ci] if e[2] == "cita")
        ac = sum(1 for e in ENL[ci] if e[2] == "contenido" and e[3] > 0)
        al = sum(1 for e in ENL[ci] if e[2] == "contenido" and e[3] < 0)
        ejes[1, ci].text(0, -.03, f"{mod} de {len(gs)} modificados ({100 * mod / len(gs):.0f} %)\n"
                         f"+{nc} citas nuevas\n{ac} se acercan · {al} se alejan",
                         transform=ejes[1, ci].transAxes, fontsize=6.8, color=TINTA, va="top", linespacing=1.35)
    for fila, (letra, rot) in enumerate((("a", "Bases licitadas"), ("b", "Bases modificadas"))):
        ejes[fila, 0].text(-.13, .5, rot, transform=ejes[fila, 0].transAxes, rotation=90, va="center", ha="center", fontsize=9)
        ejes[fila, 0].text(-.16, 1.12 if fila == 0 else 1.0, letra, transform=ejes[fila, 0].transAxes,
                           fontsize=12, fontweight="bold", va="bottom")
    # leyenda: comunidades + codificación de la fila b
    h = [Line2D([], [], marker="o", ls="", ms=5.5, mfc=color_com(i), mec="white", mew=.5, label=COM[i]["t"])
         for i in range(len(CAT))]
    otras = " y ".join(COM[i]["t"] for i in range(len(CAT), len(COM)))
    h.append(Line2D([], [], marker="o", ls="", ms=5.5, mfc=OTRAS, mec="white", mew=.5, label=f"Otras ({otras})"))
    h += [Line2D([], [], marker="o", ls="", ms=5.5, mfc=aclarar(CAT[0], .75), mec="white", label="Artículo no modificado (b)"),
          Line2D([], [], color=VERDE, lw=1.2, marker=">", ms=4, label="Cita nueva"),
          Line2D([], [], color=VERDE, lw=1, ls=(0, (3, 1.5)), label="El contenido se acerca"),
          Line2D([], [], color=ROJO, lw=1, ls=(0, (1, 1.2)), label="El contenido se aleja")]
    fig.legend(handles=h, loc="lower center", bbox_to_anchor=(.5, -.17), ncol=4, fontsize=7, handletextpad=.3,
               columnspacing=1.1, title="Comunidades temáticas (misma posición en todos los paneles; tamaño = citas recibidas)",
               title_fontsize=7.5, alignment="left")
    fig.subplots_adjust(wspace=.06, hspace=.14)
    guardar(fig, "fig_01_redes_comunidades")


# ------------------------------------------------------------------ figura 2: composición por comunidad
def fig_composicion():
    M = np.array([[sum(1 for g in GS[ci] if A["cm"][g] == i) / len(GS[ci]) for ci in range(NC)]
                  for i in range(len(COM))])
    fig, ax = plt.subplots(figsize=(ANCHO, 3.6))
    cmap = LinearSegmentedColormap.from_list("seq", ["#f7f9fd"] + SEQ)
    im = ax.imshow(M, cmap=cmap, vmin=0, vmax=M.max(), aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            ax.text(j, i, f"{100 * v:.0f} %" if v > 0 else "—", ha="center", va="center", fontsize=7.5,
                    color="white" if v > .55 * M.max() else TINTA)
    ax.set_xticks(range(NC), NOM2)
    ax.set_yticks(range(len(COM)), [f"{c['t']}  (n={c['n']})" for c in COM])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.xaxis.tick_top()
    ax.set_xticks(np.arange(-.5, NC), minor=True); ax.set_yticks(np.arange(-.5, len(COM)), minor=True)
    ax.grid(which="minor", color="white", lw=2); ax.tick_params(which="minor", length=0)
    cb = fig.colorbar(im, ax=ax, fraction=.03, pad=.02, format=lambda v, _: f"{100 * v:.0f} %")
    cb.outline.set_visible(False); cb.ax.tick_params(labelsize=7)
    cb.set_label("Porcentaje de los artículos de la concesión", fontsize=7.5)
    guardar(fig, "fig_02_composicion_comunidades")


# ------------------------------------------------------------------ figura 3: dónde se modifica más
def fig_modificacion():
    R = np.full((len(COM), NC), np.nan)
    for ci in range(NC):
        tasa = sum(1 for g in GS[ci] if g in MODIF) / len(GS[ci])
        for i in range(len(COM)):
            gs = [g for g in GS[ci] if A["cm"][g] == i]
            if len(gs) >= 3 and tasa > 0:
                R[i, ci] = (sum(1 for g in gs if g in MODIF) / len(gs)) / tasa
    L = np.log2(R)
    fig, ax = plt.subplots(figsize=(ANCHO, 3.6))
    cmap = LinearSegmentedColormap.from_list("div", DIV)
    cmap.set_bad("white")
    im = ax.imshow(np.ma.masked_invalid(L), cmap=cmap, norm=TwoSlopeNorm(0, -1.5, 1.5), aspect="auto")
    for i in range(R.shape[0]):
        for j in range(R.shape[1]):
            ax.text(j, i, "n<3" if np.isnan(R[i, j]) else f"{R[i, j]:.1f}×".replace(".", ","), ha="center",
                    va="center", fontsize=7.5, color=TINTA2 if np.isnan(R[i, j]) else
                    ("white" if abs(L[i, j]) > 1.1 else TINTA))
    ax.set_xticks(range(NC), NOM2); ax.xaxis.tick_top()
    ax.set_yticks(range(len(COM)), [c["t"] for c in COM])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks(np.arange(-.5, NC), minor=True); ax.set_yticks(np.arange(-.5, len(COM)), minor=True)
    ax.grid(which="minor", color="white", lw=2); ax.tick_params(which="minor", length=0)
    cb = fig.colorbar(im, ax=ax, fraction=.03, pad=.02, ticks=[-1.5, -1, 0, 1, 1.5],
                      format=lambda v, _: f"{2 ** v:.2g}×".replace(".", ","))
    cb.outline.set_visible(False); cb.ax.tick_params(labelsize=7)
    cb.set_label("Tasa de modificación relativa (escala log₂)", fontsize=7.5)
    fig.text(.0, -.02, "Tasa relativa = (% de artículos modificados en la comunidad) ÷ (% modificado en toda la concesión). "
             "1× = igual al promedio de la concesión; celdas con menos de 3 artículos en blanco.",
             fontsize=7, color=TINTA2)
    guardar(fig, "fig_03_modificacion_por_comunidad")


# ------------------------------------------------------------------ figura 4: concentración de citas
def fig_lorenz():
    fig, ax = plt.subplots(figsize=(ANCHO * .62, 3.4))
    ax.plot([0, 1], [0, 1], ls=(0, (3, 3)), color=OTRAS, lw=1)
    ax.text(.62, .55, "reparto parejo", rotation=38, color=TINTA2, fontsize=7)
    for ci in range(NC):
        v = np.sort([A["ci"][g] for g in GS[ci]])[::-1].astype(float)
        cum = np.concatenate([[0], np.cumsum(v) / v.sum()])
        x = np.linspace(0, 1, len(cum))
        vs = np.sort(v)
        n = len(vs)
        gini = (2 * np.sum((np.arange(1, n + 1)) * vs) / (n * vs.sum())) - (n + 1) / n
        ax.plot(x, cum, color=CAT[ci], lw=1.8, label=f"{NOM[ci]} (Gini {gini:.2f})".replace(".", ","))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.01)
    ax.xaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f} %"); ax.yaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f} %")
    ax.set_xlabel("Artículos, del más citado al menos citado")
    ax.set_ylabel("Citas recibidas acumuladas")
    ax.grid(color=LINEA, lw=.5); ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=7)
    guardar(fig, "fig_04_concentracion_citas")


# ------------------------------------------------------------------ figura 5: plantilla común
def fig_plantilla():
    tramos = ["En las otras cuatro", "En tres", "En dos", "En una", "Propio"]
    colores = [SEQ[6], SEQ[4], SEQ[3], SEQ[2], CAT[1]]
    M = np.zeros((NC, 5))
    for ci in range(NC):
        for g in GS[ci]:
            otras = {A["c"][h] for h in T["bases"]["m"][A["base"][g]] if h != g}
            M[ci, 4 - len(otras)] += 1
        M[ci] /= len(GS[ci])
    fig, ax = plt.subplots(figsize=(ANCHO, 2.3))
    izq = np.zeros(NC)
    for j, (t, col) in enumerate(zip(tramos, colores)):
        ax.barh(range(NC), M[:, j], left=izq, color=col, edgecolor="white", lw=1.5, height=.62, label=t)
        for ci in range(NC):
            if M[ci, j] >= .06:
                ax.text(izq[ci] + M[ci, j] / 2, ci, f"{100 * M[ci, j]:.0f}", ha="center", va="center", fontsize=7,
                        color="white" if j < 2 else TINTA)
        izq += M[:, j]
    ax.set_yticks(range(NC), NOM); ax.invert_yaxis()
    ax.set_xlim(0, 1); ax.xaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f} %")
    ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Porcentaje de artículos según en cuántas otras concesiones tienen un equivalente")
    ax.legend(ncol=5, loc="lower center", bbox_to_anchor=(.5, 1.0), fontsize=7.2, handlelength=1, columnspacing=1)
    guardar(fig, "fig_05_plantilla_comun")


# ------------------------------------------------------------------ figura 6: cuándo se modifica
def fig_tiempo():
    fig, ax = plt.subplots(figsize=(ANCHO, 2.9))
    for ci in range(NC):
        cs = sorted((c["anios"], c["ed"]) for c in CAMBIOS if c["ci"] == ci)
        if not cs:
            continue
        t0 = min(a for a, _ in cs) - .05
        t = np.array([t0] + [a for a, _ in cs]); y = np.concatenate([[0], np.cumsum([e for _, e in cs])]) / sum(e for _, e in cs)
        ax.step(t, y, where="post", color=CAT[ci], lw=1.6, label=NOM[ci])
    ax.axvline(0, color=TINTA2, lw=.8, ls=(0, (2, 2)))
    ax.text(.15, .04, "adjudicación", fontsize=7, color=TINTA2, rotation=90, va="bottom")
    ax.axvspan(ax.get_xlim()[0], 0, color="#f0efec", zorder=0)
    ax.text(-.15, .04, "licitación", fontsize=7, color=TINTA2, rotation=90, va="bottom", ha="right")
    ax.set_xlabel("Años desde la adjudicación del contrato")
    ax.set_ylabel("Ediciones acumuladas")
    ax.yaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f} %"); ax.set_ylim(0, 1.02)
    ax.grid(color=LINEA, lw=.5); ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=7.2, ncol=2)
    guardar(fig, "fig_06_modificaciones_en_el_tiempo")


# ------------------------------------------------------------------ figura 7: licitación vs contrato
def fig_fases():
    fig, ax = plt.subplots(figsize=(ANCHO, 2.1))
    for ci in range(NC):
        lic = sum(c["ed"] for c in CAMBIOS if c["ci"] == ci and c["fase"] == "lic")
        con = sum(c["ed"] for c in CAMBIOS if c["ci"] == ci and c["fase"] == "con")
        tot = lic + con or 1
        ax.barh(ci, lic / tot, color=CAT[0], height=.6, edgecolor="white", lw=1.5, label="Durante la licitación" if ci == 0 else None)
        ax.barh(ci, con / tot, left=lic / tot, color="#c9c8c2", height=.6, edgecolor="white", lw=1.5,
                label="Durante el contrato" if ci == 0 else None)
        ax.text(lic / tot / 2, ci, f"{100 * lic / tot:.0f} %", ha="center", va="center", color="white", fontsize=7.5)
        ax.text(1.01, ci, f"{lic + con} ediciones", va="center", fontsize=7, color=TINTA2)
    ax.set_yticks(range(NC), NOM); ax.invert_yaxis(); ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f} %")
    ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
    ax.legend(ncol=2, loc="lower center", bbox_to_anchor=(.45, 1.0), fontsize=7.5)
    guardar(fig, "fig_07_licitacion_vs_contrato")


# ------------------------------------------------------------------ figura 8: centralidad y modificación
def fig_cuartiles():
    fig, ax = plt.subplots(figsize=(ANCHO, 2.8))
    ancho = .16
    for ci in range(NC):
        gs = sorted([g for g in GS[ci] if not A["nuevo"][g]], key=lambda g: -A["pr0"][g])
        q = np.array_split(gs, 4)
        tasas = [np.mean([g in MODIF for g in qq]) for qq in q]
        ax.bar(np.arange(4) + (ci - 2) * ancho, tasas, width=ancho - .02, color=CAT[ci], label=NOM[ci])
    ax.set_xticks(range(4), ["Q1\n(más citados)", "Q2", "Q3", "Q4\n(menos citados)"])
    ax.yaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f} %")
    ax.set_ylabel("Artículos modificados")
    ax.set_xlabel("Cuartil de PageRank en las Bases originales")
    ax.grid(axis="y", color=LINEA, lw=.5); ax.set_axisbelow(True)
    ax.legend(ncol=5, loc="lower center", bbox_to_anchor=(.5, 1.0), fontsize=7.2)
    guardar(fig, "fig_08_centralidad_y_modificacion")


# ------------------------------------------------------------------ figura 9: antes y después
def fig_antes_despues():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(ANCHO, 2.9), gridspec_kw={"width_ratios": [1.1, 1]})
    datos = []
    for ci, c in enumerate(CONC):
        arts = AD["concesiones"][c["cod"]]["arts"]
        datos.append([e["phi"] for e in arts.values() if e.get("phi") is not None and not e.get("dudoso")])
        w = np.array([e["w"] for e in arts.values() if not e.get("nuevo") and not e.get("dudoso") and e["w"][0] > 0])
        a2.scatter(w[:, 0], w[:, 1], s=9, color=CAT[ci], alpha=.75, edgecolors="white", linewidths=.3, label=NOM[ci])
    tramos = [("φ ≥ 0,99\ncasi igual", .99, 1.01), ("0,95–0,99", .95, .99), ("0,80–0,95", .80, .95), ("φ < 0,80\nreescrito", -1, .80)]
    col_t = [SEQ[1], SEQ[3], SEQ[5], CAT[1]]
    izq = np.zeros(NC)
    for (et, lo, hi), col in zip(tramos, col_t):
        v = np.array([np.mean([lo <= p < hi for p in d]) if d else 0 for d in datos])
        a1.barh(range(NC), v, left=izq, color=col, edgecolor="white", lw=1.2, height=.62, label=et)
        for ci in range(NC):
            if v[ci] >= .08:
                a1.text(izq[ci] + v[ci] / 2, ci, f"{100 * v[ci]:.0f}", ha="center", va="center", fontsize=6.8,
                        color="white" if col in (SEQ[5], CAT[1]) else TINTA)
        izq += v
    a1.set_yticks(range(NC), NOM); a1.invert_yaxis(); a1.set_xlim(0, 1)
    a1.xaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f} %")
    a1.spines["left"].set_visible(False); a1.tick_params(axis="y", length=0)
    a1.set_xlabel("Artículos modificados según similitud φ\nentre texto original y vigente")
    a1.legend(ncol=2, loc="lower center", bbox_to_anchor=(.45, 1.06), fontsize=6.3, handlelength=1, columnspacing=.8)
    a1.set_title("a) Cuánto cambia el texto", loc="left", fontsize=8.5, pad=34)
    lim = [5, 2e4]
    a2.plot(lim, lim, ls=(0, (3, 3)), color=OTRAS, lw=1)
    a2.set_xscale("log"); a2.set_yscale("log"); a2.set_xlim(lim); a2.set_ylim(lim)
    a2.set_xlabel("Palabras en las Bases originales"); a2.set_ylabel("Palabras en el texto vigente")
    a2.text(1.5e3, 7e2, "se acorta", fontsize=7, color=TINTA2); a2.text(12, 2.5e2, "se alarga", fontsize=7, color=TINTA2)
    a2.set_title("b) Largo antes y después", loc="left", fontsize=8.5, pad=34)
    a2.legend(fontsize=6.5, loc="upper left", handletextpad=.1, markerscale=1.4)
    fig.subplots_adjust(wspace=.42)
    guardar(fig, "fig_09_antes_despues")


# ------------------------------------------------------------------ figura 10: citas entre comunidades
def fig_flujo_comunidades():
    K = len(COM)
    M = np.zeros((K, K))
    for g in range(N):
        for h, w in zip(A["sale"][g], A["sw"][g]):
            M[A["cm"][g], A["cm"][h]] += w
    P = M / M.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(ANCHO * .85, 4.2))
    cmap = LinearSegmentedColormap.from_list("seq", ["#f7f9fd"] + SEQ)
    im = ax.imshow(P, cmap=cmap, vmin=0, vmax=.6)
    for i in range(K):
        for j in range(K):
            if P[i, j] >= .05:
                ax.text(j, i, f"{100 * P[i, j]:.0f}", ha="center", va="center", fontsize=6.8,
                        color="white" if P[i, j] > .33 else TINTA)
    cortos = [c["t"] for c in COM]
    ax.set_yticks(range(K), cortos, fontsize=7.2)
    ax.set_xticks(range(K), cortos, rotation=50, ha="right", fontsize=7.2)
    ax.set_ylabel("Comunidad del artículo que cita"); ax.set_xlabel("Comunidad del artículo citado")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks(np.arange(-.5, K), minor=True); ax.set_yticks(np.arange(-.5, K), minor=True)
    ax.grid(which="minor", color="white", lw=1.5); ax.tick_params(which="minor", length=0)
    cb = fig.colorbar(im, ax=ax, fraction=.035, pad=.02, format=lambda v, _: f"{100 * v:.0f} %")
    cb.outline.set_visible(False); cb.ax.tick_params(labelsize=7)
    cb.set_label("Porcentaje de las citas que hace la comunidad (fila)", fontsize=7.5)
    guardar(fig, "fig_10_citas_entre_comunidades")


if __name__ == "__main__":
    print(f"figuras en {SALIDA}")
    for f in (fig_redes, fig_composicion, fig_modificacion, fig_lorenz, fig_plantilla, fig_tiempo, fig_fases,
              fig_cuartiles, fig_antes_despues, fig_flujo_comunidades):
        f()
