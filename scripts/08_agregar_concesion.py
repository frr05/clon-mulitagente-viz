"""Arma visor_cm/: el tablero con los datos del artefacto original más una concesión adicional (p. ej. Camino de la Madera).

    python scripts/08_agregar_concesion.py "../proyectos desechados/Camino de la Madera/nodos_versionados.json" [--color "#1F9BD1"]

- Las cinco concesiones quedan exactamente como en el artefacto (_original/*.js).
- La nueva se arma con las mismas reglas que 05_tablero.py (filas, citas, PageRank, historia) y 06_antes_despues.py.
- Su comunidad sale de clasificar_concesion.py (voto de sus 8 vecinos más parecidos, tf-idf + LSA), sobre las 10
  comunidades del artefacto; su posición en el mapa es el promedio ponderado de la de esos vecinos.
- ct: su más parecido en cada otra concesión (φ ≥ 0,5). bases: se une a la base de su más parecido si es recíproco y la
  base no tiene ya un artículo de la nueva; si no, base propia.
No toca visor/ (el clon validado).
"""
import argparse
import importlib.util
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import comun  # noqa: E402


def modulo(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, AQUI / archivo)
    m = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = m
    spec.loader.exec_module(m)
    return m


tab = modulo("tablero", "05_tablero.py")
ad = modulo("antes_despues", "06_antes_despues.py")
cla = modulo("clasificar", "clasificar_concesion.py")
DESTINO = AQUI.parent / "visor_cm"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arbol")
    ap.add_argument("--color", default="#1F9BD1")
    a = ap.parse_args()
    ruta = Path(a.arbol).resolve()

    T = comun.original("tablero_datos.js")
    AD = comun.original("antes_despues.js")
    A = T["arts"]
    N = len(A["c"])
    cods = [c["cod"] for c in T["conc"]]
    g_de = {(cods[A["c"][g]], A["num"][g]): g for g in range(N)}

    print("cargando árboles…", flush=True)
    ccs = [tab.Concesion(cid, ci) for ci, cid in enumerate(comun.ORDEN)]
    nueva = cla.cargar_nueva(ruta)
    ci_n = len(T["conc"])
    nueva.ci = ci_n

    # ---- grupo 1 de la nueva (índices g desplazados en N)
    g1 = tab.grupo1([nueva])
    for k in ("sale", "entra", "nueva"):
        g1[k] = [[N + j for j in l] for l in g1[k]]
    n_new = len(g1["c"])
    # árboles del pipeline antiguo (OCR): «II.x» / «III.x» se leyeron como «11.x» / «111.x»
    romanos = {"11": "Técnicas", "111": "Económicas"}
    g1["parte"] = [p or romanos.get(num.split(".")[0], "") for p, num in zip(g1["parte"], g1["num"])]

    # ---- similitud con las cinco (mismo espacio que clasificar_concesion.py)
    todas = ccs + [nueva]
    claves = [(cc.cid, f["numero"]) for cc in todas for f in cc.filas]
    X = comun.vectores(tab.textos_filas(todas), modo="lsa", dim=tab.DIM_LSA, semilla=tab.SEMILLA)
    S = X @ X.T
    pos_nueva = [i for i, k in enumerate(claves) if k[0] == nueva.cid]
    ref = [i for i, k in enumerate(claves) if k in g_de]          # filas de las cinco que existen en el original
    g_ref = np.array([g_de[claves[i]] for i in ref])
    etiq = np.array([A["cm"][g] for g in g_ref])
    xs, ys = np.array(A["x"]), np.array(A["y"])

    cm, x, y, ct, mejor = [], [], [], [], []
    rng = np.random.default_rng(7)
    for i in pos_nueva:
        sims = S[i, ref]
        c, conf, orden = cla.votar(sims, etiq)
        cm.append(c)
        w = np.clip(sims[orden], 1e-3, None)
        x.append(round(float(np.average(xs[g_ref[orden]], weights=w) + rng.normal(0, .015)), 4))
        y.append(round(float(np.average(ys[g_ref[orden]], weights=w) + rng.normal(0, .015)), 4))
        fila = []
        for cj in range(ci_n):
            idx = [k for k in range(len(ref)) if A["c"][g_ref[k]] == cj]
            k = max(idx, key=lambda k: sims[k])
            if round(float(sims[k]), 2) >= tab.UMBRAL_CT:
                fila.append([int(g_ref[k]), round(float(sims[k]), 2)])
        ct.append(fila)
        mejor.append((float(sims[orden[0]]), int(g_ref[orden[0]]), ref[orden[0]]))
    g1.update(cm=cm, x=[max(-1, min(1, v)) for v in x], y=[max(-1, min(1, v)) for v in y], ct=ct)

    # ---- bases: unirse a la base del más parecido si es recíproco
    B = {k: list(v) for k, v in T["bases"].items()}
    base_de = list(A["base"])
    con_nueva = set()
    g1["base"] = [None] * n_new
    candidatos = sorted(((s, j, g, r) for j, (s, g, r) in enumerate(mejor)), reverse=True)
    for s, j, g, r in candidatos:
        reciproco = max(pos_nueva, key=lambda i: S[r, i]) == pos_nueva[j]
        b = base_de[g]
        if s >= tab.UMBRAL_BASE and reciproco and b not in con_nueva:
            con_nueva.add(b)
            B["m"][b] = B["m"][b] + [N + j]
            g1["base"][j] = b
    for j in range(n_new):
        if g1["base"][j] is None:
            g1["base"][j] = len(B["m"])
            B["m"].append([N + j]); B["t"].append(g1["t"][j]); B["x"].append(g1["x"][j]); B["y"].append(g1["y"][j])

    # ---- unir y escribir
    for k in A:
        A[k] = A[k] + g1[k]
    corto_, largo = nueva.arbol["concesion"]["nombre"], nueva.arbol["concesion"]["nombre"]
    T["conc"].append({"cod": nueva.cid, "nombre": corto_, "largo": largo, "color": a.color, "adj": nueva.adj,
                      "actos": nueva.conc_actos})
    for i, com in enumerate(T["comunidades"]):
        com["n"] = sum(1 for v in A["cm"] if v == i)
        com["conc"] = len({A["c"][g] for g in range(len(A["c"])) if A["cm"][g] == i})
    T["bases"] = B
    T["generado"] = f"{T['generado']} + {nueva.cid} {comun.ahora()}"
    n_ad, arts_ad = ad.procesar(nueva, comun.Avance(len(ad.unidades(nueva)), nueva.cid))
    AD["concesiones"][nueva.cid] = {"n": n_ad, "arts": arts_ad}

    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    shutil.copytree(comun.VISOR, DESTINO, ignore=shutil.ignore_patterns("datos_RITP_lsa.js"))
    comun.escribir_js(DESTINO / "tablero_datos.js", "window.TAB", T)
    comun.escribir_js(DESTINO / "antes_despues.js", "window.ANTES_DESPUES", AD)
    shutil.copy(comun.ORIGINAL / "matriz" / "datos_RITP.js", DESTINO / "matriz" / "datos_RITP.js")
    adaptar_textos(DESTINO / "tablero.js", len(T["conc"]))
    for f in ("index.html", "nav.js"):
        p = DESTINO / f
        p.write_text(p.read_text(encoding="utf-8").replace("Cinco concesiones", "Seis concesiones")
                     .replace("cinco concesiones", "seis concesiones"), encoding="utf-8")
    print(f"  {nueva.cid}: {n_new} artículos, {sum(1 for b in g1['base'] if len(B['m'][b]) > 1)} en bases comunes, "
          f"{len(arts_ad)} en antes/después · escrito {DESTINO}")


def adaptar_textos(ruta: Path, n: int):
    """El tablero dice «las cinco» / «las otras cuatro»: con n concesiones, cambia esos textos y los tramos de «plantilla»."""
    num = {2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete"}
    t = ruta.read_text(encoding="utf-8")
    t = t.replace("las otras cuatro", f"las otras {num[n - 1]}").replace("las cinco", f"las {num[n]}")
    tramos = [f"En las otras {num[n - 1]}"] + [f"En {num[k]}" if k > 1 else "En una" for k in range(n - 2, 0, -1)] + ["Propio"]
    colores = ["#2b2d7a", "#3b47b5", "#4f58c4", "#8a90dc", "#c3c7ee", "#dfe1f5"][:len(tramos) - 1] + ["#e0a030"]
    viejo_tramos = 'const EN_OTRAS = ["En las otras {0}", "En tres", "En dos", "En una", "Propio"];'.format(num[n - 1])
    nuevo_tramos = "const EN_OTRAS = " + str(tramos).replace("'", '"') + ";"
    viejo_col = t[t.index("const COLOR_OTRAS"):t.index("\n", t.index("const COLOR_OTRAS"))]
    nuevo_col = "const COLOR_OTRAS = {" + ", ".join(f'"{k}": "{c}"' for k, c in zip(tramos, colores)) + "};"
    assert viejo_tramos in t, "no encontré EN_OTRAS en tablero.js"
    t = t.replace(viejo_tramos, nuevo_tramos).replace(viejo_col, nuevo_col)
    t = t.replace("Math.min(4, C.length - 1 - eqs(g).length)", f"Math.min({len(tramos) - 1}, C.length - 1 - eqs(g).length)")
    ruta.write_text(t, encoding="utf-8")


if __name__ == "__main__":
    main()
