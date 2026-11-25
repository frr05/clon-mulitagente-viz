"""Genera visor/antes_despues.js (window.ANTES_DESPUES) desde los árboles de entrada (ver ESPEC.md §2).

    python scripts/06_antes_despues.py

Grupo 1: unidades, w, inc, cs/ce, d, nuevo.  Grupo 2: phi, v0, v1 (vecinos por LSA dentro de la concesión).
"""
from __future__ import annotations

import difflib
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
from comun import citas, orden_numero  # noqa: E402

_sp = importlib.util.spec_from_file_location("tablero05", Path(__file__).resolve().parent / "05_tablero.py")
T05 = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(T05)

SALIDA = comun.VISOR / "antes_despues.js"
K = 8
UMBRAL_CONTEXTO = 40  # un tramo sin cambios de más palabras se acorta con «…»
CONTEXTO = 18        # palabras de contexto que se conservan a cada lado de un tramo sin cambios
CORTE_SEG = 120      # un tramo con cambios de más palabras queda como [op, primeras_120, n_omitidas]
LARGO_CITA = 1500
UMBRAL_DUDOSO = 0.5
LARGO_VERSION = 400  # texto máximo de una versión que ya no está vigente


def titulo_sin_numero(n: dict) -> str:
    t = n.get("titulo") or ""
    num = n.get("numero") or ""
    return t[len(num):].strip() if num and t.startswith(num) else t.strip()


def items_de(ix: dict, n: dict, rec: bool) -> list[dict]:
    """Incisos BL: y tablas de la unidad (en el orden del árbol); con rec, también los de sus sub-artículos."""
    out = []
    for h in n.get("hijos") or []:
        x = ix.get(h)
        if x is None:
            continue
        if x["tipo"] in ("inciso", "inciso_eliminado", "tabla") and (h.startswith("BL:") or x["tipo"] == "tabla"):
            out.append(x)
        elif rec and x["tipo"] == "articulo" and h.startswith("BL:"):
            out.extend(items_de(ix, x, True))
    return out


def incisos_de(ix: dict, n: dict, rec: bool = False) -> list[dict]:
    return [x for x in items_de(ix, n, rec) if x["tipo"] in ("inciso", "inciso_eliminado")]


def propios(ix: dict, n: dict) -> list[dict]:
    return [ix[h] for h in n.get("hijos") or [] if h in ix and ix[h]["tipo"] == "inciso" and h.startswith("BL:")]


def diff_palabras(pre: str, post: str) -> list:
    a, b = pre.split(), post.split()
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    out = []
    for k, (op, i1, i2, j1, j2) in enumerate(ops):
        if op == "equal":
            w = a[i1:i2]
            if k == 0 and len(ops) > 1:
                t = (["…"] + w[-CONTEXTO:]) if len(w) > UMBRAL_CONTEXTO else w
            elif k == len(ops) - 1 and len(ops) > 1:
                t = (w[:CONTEXTO] + ["…"]) if len(w) > UMBRAL_CONTEXTO else w
            else:
                t = (w[:CONTEXTO] + ["…"] + w[-CONTEXTO:]) if len(w) > UMBRAL_CONTEXTO else w
            out.append([0, " ".join(t)])
        else:
            for signo, w in ((-1, a[i1:i2]), (1, b[j1:j2])):
                if not w:
                    continue
                if len(w) > CORTE_SEG:
                    out.append([signo, " ".join(w[:CORTE_SEG]), len(w) - CORTE_SEG])
                else:
                    out.append([signo, " ".join(w)])
    return out


def unidades(cc) -> list[dict]:
    vistos, out = set(), []
    for n in cc.arbol["nodos"]:
        if n["tipo"] == "articulo" and n["id"].startswith("BL:") and not n.get("eliminado_por") and n["id"] not in vistos:
            vistos.add(n["id"])
            out.append(n)
    return out


def recortar(t: str, largo: int = LARGO_VERSION) -> str:
    """Palabras enteras hasta ~400 caracteres, más « …»."""
    if len(t) <= largo:
        return t
    out, n = [], 0
    for w in t.split():
        add = len(w) + (1 if out else 0)
        if n + add + 1 > largo:
            break
        out.append(w)
        n += add
    return " ".join(out) + " …"


def _pre_post(cc, ix, n, rec):
    """Un inciso con historial (más de una versión) guarda cada versión recortada a ~400 caracteres."""
    o, v = [], []
    for x in incisos_de(ix, n, rec):
        hist = len(x.get("versiones") or []) > 1
        ajustar = recortar if hist else (lambda t: t)
        for vv in x.get("versiones") or []:
            if (vv.get("acto") or {}).get("id") == cc.bases_id:
                o.append(ajustar(vv.get("texto") or ""))
        vg = comun.vigente(x)
        if vg is not None:
            v.append(ajustar(vg.get("texto") or ""))
    tit = titulo_sin_numero(n)
    return " ".join([tit] + o), " ".join([tit] + v)


def textos(cc, ix, n) -> tuple[str, str, bool]:
    """(antes, después, incluye_sub-artículos): propios si cambiaron; si no, con los sub-artículos."""
    pre, post = _pre_post(cc, ix, n, False)
    if pre == post and not n.get("agregado_por"):
        pre2, post2 = _pre_post(cc, ix, n, True)
        if pre2 != post2:
            return pre2, post2, True
    return pre, post, False


def citas_nuevas(cc, ix, info) -> tuple[dict, dict]:
    """Citas nuevas = citas del texto vigente (primeros 1500 caracteres de cada inciso propio) en las que el artículo
    que cita o el citado fue agregado por un acto; k = acto que agregó ese artículo (el del que cita, si ambos)."""
    k_agr = {a: cc.k_de.get((f["n"].get("agregado_por") or {}).get("id")) for a, f in info.items() if f["nuevo"]}
    cs, ce = {}, {}
    for a, f in info.items():
        vistos = set()
        for x in propios(ix, f["n"]):
            vg = comun.vigente(x)
            if vg is None:
                continue
            for c in citas((vg.get("texto") or "")[:LARGO_CITA]):
                b = cc.art_por_clave.get(c)
                if b is None or b == a or b not in info or (a not in k_agr and b not in k_agr):
                    continue
                k = k_agr[a] if a in k_agr else k_agr[b]
                if (b, k) not in vistos:
                    vistos.add((b, k))
                    cs.setdefault(a, []).append([b, k])
    for a in cs:
        for b, k in cs[a]:
            ce.setdefault(b, []).append([a, k])
    return cs, ce


def contar_inc(cc, ix, n, rec) -> list[int]:
    ag = 0
    for x in items_de(ix, n, rec):
        vg = comun.vigente(x)
        if vg is not None and (vg.get("acto") or {}).get("id") != cc.bases_id:
            ag += 1
    el = sum(1 for x in items_de(ix, n, rec) if x["tipo"] == "inciso_eliminado")
    return [ag, el]


def espacio(corpus: list[str], dim: int = 100):
    """Ajusta tf-idf + LSA (como comun.vectores) sobre `corpus` y devuelve una función texto -> vector unitario."""
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    tf = TfidfVectorizer(preprocessor=comun.sin_tilde, token_pattern=r"(?u)\b[a-zñ]{3,}\b",
                         stop_words=sorted(comun.STOP), sublinear_tf=True, min_df=1, max_df=0.6)
    M = tf.fit_transform(corpus)
    sv = TruncatedSVD(n_components=max(2, min(dim, M.shape[1] - 1)), random_state=7).fit(M)
    mu = sv.transform(M).mean(axis=0)

    def proyectar(textos: list[str]):
        X = sv.transform(tf.transform(textos)) - mu
        n = np.linalg.norm(X, axis=1, keepdims=True)
        n[n == 0] = 1
        return X / n
    return proyectar


def procesar(cc, av) -> tuple[int, dict]:
    ix = cc.ix
    us = unidades(cc)
    info = {}
    for n in us:
        pre, post, rec = textos(cc, ix, n)
        nuevo = bool(n.get("agregado_por"))
        if nuevo:
            pre = ""
        info[n["id"]] = {"n": n, "pre": pre, "post": post, "nuevo": nuevo, "rec": rec}
    cs, ce = citas_nuevas(cc, ix, info)
    for a, f in info.items():
        f["inc"] = contar_inc(cc, ix, f["n"], f["rec"])
    cambiadas = [a for a, f in info.items()
                 if f["nuevo"] or f["pre"] != f["post"] or cs.get(a) or ce.get(a) or f["inc"][1]]
    ids = list(info)
    pos = {a: i for i, a in enumerate(ids)}
    post_txt = [info[a]["post"] for a in ids]
    orig_txt = [info[a]["pre"] or info[a]["post"] for a in ids]
    proy_post = espacio(post_txt)          # espacio del texto vigente (v1 y phi)
    proy_orig = espacio(orig_txt)          # espacio del texto original (v0)
    Vpost, Vo_o = proy_post(post_txt), proy_orig(orig_txt)
    Vpre = {a: proy_post([info[a]["pre"]])[0] for a in ids if info[a]["pre"] and not info[a]["nuevo"]}
    Vorig = Vo_o
    nuevo_mask = np.array([info[a]["nuevo"] for a in ids])

    def vecinos(v, propio, base, excluir_nuevos):
        s = base @ v
        out = []
        for j in np.argsort(-s):
            if ids[j] == propio or (excluir_nuevos and nuevo_mask[j]):
                continue
            out.append([ids[j], round(float(s[j]), 3)])
            if len(out) == K:
                break
        return out

    arts = {}
    for a in sorted(cambiadas, key=lambda x: orden_numero(x[3:])):
        f = info[a]
        av.paso()
        e = {
            "phi": None if f["nuevo"] else round(float(Vpre[a] @ Vpost[pos[a]]), 3),
            "w": [len(f["pre"].split()), len(f["post"].split())],
            "inc": f["inc"],
            "v0": [] if f["nuevo"] else vecinos(Vorig[pos[a]], a, Vorig, True),
            "v1": vecinos(Vpost[pos[a]], a, Vpost, False),
            "cs": cs.get(a, []),
            "ce": sorted(ce.get(a, []), key=lambda p: (orden_numero(p[0][3:]), p[1])),
            "d": [] if f["pre"] == f["post"] else diff_palabras(f["pre"], f["post"]),
        }
        if f["nuevo"]:
            e["nuevo"] = 1
        elif e["w"][0] and e["w"][1] < UMBRAL_DUDOSO * e["w"][0]:
            e["dudoso"] = 1   # el vigente tiene menos de la mitad de las palabras: puede ser una extracción incompleta
        arts[a] = e
    return len(us), arts


def main():
    t0 = time.time()
    ccs = [T05.Concesion(cid, ci) for ci, cid in enumerate(comun.ORDEN)]
    conc = {}
    for cc in ccs:
        av = comun.Avance(len(unidades(cc)), cc.cid)
        n, arts = procesar(cc, av)
        conc[cc.cid] = {"n": n, "arts": arts}
        print(f"  {cc.cid}: n={n}, entradas={len(arts)} ({time.time() - t0:.0f} s)", flush=True)
    comun.escribir_js(SALIDA, "window.ANTES_DESPUES", {"generado": comun.ahora(), "k": K, "concesiones": conc})
    print(f"  escrito {SALIDA} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
