"""Clasifica los artículos de una concesión nueva en las 10 comunidades del artefacto original, por vecinos.

    python scripts/clasificar_concesion.py "../proyectos desechados/Camino de la Madera/nodos_versionados.json"

No vuelve a agrupar: las comunidades son las del artefacto (window.TAB.comunidades), con sus nombres. Cada artículo x.y.z
de la concesión nueva (armado igual que en 05_tablero.py) se compara por tf-idf + LSA con los 641 artículos de las cinco
concesiones; sus K vecinos más parecidos votan con su parecido y gana la comunidad con más peso.
Antes mide el acierto del método: saca cada concesión por turno y la clasifica contra las otras cuatro.
Escribe el informe en <proyecto>/comunidades_<ID>.md.
"""
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun  # noqa: E402

spec = importlib.util.spec_from_file_location("tablero", AQUI / "05_tablero.py")
tab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tab)

K = 8                 # vecinos que votan
MIN_PARECIDO = 0.30   # si el vecino más parecido no llega a esto: «sin comunidad clara»
MARGEN_DUDOSO = 0.60  # si la comunidad ganadora junta menos de este % del voto: «dudosa»


def cargar_nueva(ruta: Path) -> tab.Concesion:
    arbol = json.loads(ruta.read_text(encoding="utf-8"))
    original = comun.version_reciente
    comun.version_reciente = lambda cid: (arbol, "externa", ruta.parent)
    try:
        return tab.Concesion(arbol["concesion"]["id"], 5)
    finally:
        comun.version_reciente = original


def votar(sims: np.ndarray, etiquetas: np.ndarray, k: int = K):
    orden = np.argsort(-sims)[:k]
    peso = defaultdict(float)
    for j in orden:
        peso[int(etiquetas[j])] += max(float(sims[j]), 0.0)
    total = sum(peso.values()) or 1.0
    gana = max(peso, key=peso.get)
    return gana, peso[gana] / total, orden


def main():
    ruta = Path(sys.argv[1]).resolve()
    T = comun.original("tablero_datos.js")
    A, COM = T["arts"], T["comunidades"]
    cm_orig = {(T["conc"][A["c"][g]]["cod"], A["num"][g]): A["cm"][g] for g in range(len(A["c"]))}

    print("cargando las cinco concesiones y la nueva…", flush=True)
    ccs = [tab.Concesion(cid, ci) for ci, cid in enumerate(comun.ORDEN)]
    nueva = cargar_nueva(ruta)
    todas = ccs + [nueva]
    claves = [(cc.cid, f["numero"]) for cc in todas for f in cc.filas]
    textos = tab.textos_filas(todas)
    titulos = [tab.titulo_fila(f) for cc in todas for f in cc.filas]
    X = comun.vectores(textos, modo="lsa", dim=tab.DIM_LSA, semilla=tab.SEMILLA)
    S = X @ X.T
    es_nueva = np.array([c == nueva.cid for c, _ in claves])
    base = np.flatnonzero(~es_nueva)
    etiq = np.array([cm_orig.get(claves[g], -1) for g in base])
    print(f"  {len(base)} artículos de referencia (con comunidad del original: {(etiq >= 0).sum()}) · "
          f"{es_nueva.sum()} artículos de {nueva.cid}", flush=True)

    # 1. acierto: cada concesión, clasificada contra las otras cuatro
    lineas_acierto = []
    total_ok = total_n = 0
    for cid in comun.ORDEN:
        prueba = [g for g in base if claves[g][0] == cid and claves[g] in cm_orig]
        ref = np.array([g for g in base if claves[g][0] != cid and claves[g] in cm_orig])
        et = np.array([cm_orig[claves[g]] for g in ref])
        ok = sum(votar(S[g, ref], et)[0] == cm_orig[claves[g]] for g in prueba)
        total_ok += ok
        total_n += len(prueba)
        lineas_acierto.append(f"| {cid} | {ok}/{len(prueba)} | {100 * ok / len(prueba):.0f} % |")
    acierto = 100 * total_ok / total_n
    print(f"  acierto sacando cada concesión: {acierto:.0f} %", flush=True)

    # 2. la concesión nueva
    ref = np.array([g for g in base if claves[g] in cm_orig])
    et = np.array([cm_orig[claves[g]] for g in ref])
    filas = []
    for g in np.flatnonzero(es_nueva):
        sims = S[g, ref]
        c, conf, orden = votar(sims, et)
        mejor = float(sims[orden[0]])
        estado = "sin comunidad clara" if mejor < MIN_PARECIDO else ("dudosa" if conf < MARGEN_DUDOSO else "")
        vec = ref[orden[0]]
        filas.append((claves[g][1], titulos[g], COM[c]["t"], conf, mejor, f"{claves[vec][0]} {claves[vec][1]} {titulos[vec]}", estado))
    filas.sort(key=lambda f: comun.orden_numero(f[0]))
    reparto = Counter(f[2] for f in filas if f[6] != "sin comunidad clara")

    out = [f"# Comunidades de {nueva.arbol['concesion']['nombre']} ({nueva.cid})", "",
           f"Árbol: `{ruta}` (generado {nueva.arbol['generado']}). {len(filas)} artículos x.y.z, clasificados en las "
           f"10 comunidades del artefacto original por sus {K} vecinos más parecidos (tf-idf + LSA, voto ponderado).", "",
           "## Acierto del método", "",
           "Se saca cada concesión, se clasifican sus artículos contra las otras cuatro y se compara con la comunidad que "
           f"les dio el original. Acierto total: **{acierto:.0f} %**.", "",
           "| Concesión | Aciertos | % |", "|---|---|---|", *lineas_acierto, "",
           f"## Reparto de {nueva.cid}", "", "| Comunidad | Artículos |", "|---|---|",
           *[f"| {c['t']} | {reparto.get(c['t'], 0)} |" for c in COM],
           f"| (sin comunidad clara) | {sum(1 for f in filas if f[6] == 'sin comunidad clara')} |", "",
           "## Artículo por artículo", "",
           "Confianza = parte del voto que juntó la comunidad ganadora. Parecido = coseno con el vecino más parecido.", "",
           "| Artículo | Título | Comunidad | Confianza | Parecido | Vecino más parecido | Nota |", "|---|---|---|---|---|---|---|"]
    for num, t, c, conf, mejor, vec, estado in filas:
        out.append(f"| {num} | {t} | {c} | {100 * conf:.0f} % | {mejor:.2f} | {vec} | {estado} |")
    salida = AQUI.parent / f"comunidades_{nueva.cid}.md"
    salida.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"  {nueva.cid}: " + ", ".join(f"{c} {n}" for c, n in reparto.most_common()), flush=True)
    print(f"informe: {salida}")


if __name__ == "__main__":
    main()
