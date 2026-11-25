"""Genera visor/tablero_datos.js (window.TAB) desde los árboles de entrada (ver ESPEC.md §1).

    python scripts/05_tablero.py

Grupo 1 (determinista): actos, filas de artículo, citas, PageRank, historia de cambios.
Grupo 2 (similitud): vectores de contenido, proyección 2D, pares parecidos, bases comunes, comunidades.
"""
from __future__ import annotations

import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
from comun import citas, clave_numero, orden_numero  # noqa: E402

SALIDA = comun.VISOR / "tablero_datos.js"
LARGO_TITULO = 90          # títulos más largos se cortan con «…»
LARGO_TEXTO_H = 220        # texto de cada cambio en `h`
LARGO_TEXTO_CITA = 1500    # las citas se buscan en los primeros 1500 caracteres de cada inciso
CORTE_CS = 6               # `cs` se corta a los 6 sub-artículos con más citas
PARTES = (("ADMINISTRATIVA", "Administrativas"), ("TECNICA", "Técnicas"), ("ECONOMICA", "Económicas"))


# ======================================================================== grupo 1

def fechas_actos(actos: list[dict]) -> list[str]:
    """Fecha YYYY-MM-DD de cada acto: si falta o es incompleta, la del siguiente acto con fecha completa
    (y si no hay siguiente, la del anterior)."""
    completa = [a["fecha"] if a.get("fecha") and re.fullmatch(r"\d{4}-\d\d-\d\d", a["fecha"]) else None for a in actos]
    out = list(completa)
    siguiente = None
    for i in range(len(out) - 1, -1, -1):
        if out[i] is None:
            out[i] = siguiente
        else:
            siguiente = out[i]
    previa = None
    for i in range(len(out)):
        if out[i] is None:
            out[i] = previa
        else:
            previa = out[i]
    return out


def nombre_acto(a: dict) -> str:
    return re.sub(r"\s*\([^()]*\)\s*$", "", a["nombre"]).strip()


def tipo_acto(a: dict) -> str:
    return comun.sin_tilde(a.get("tipo") or "otro").strip()


def titulo_fila(n: dict) -> str:
    t = n.get("titulo") or ""
    num = n.get("numero") or ""
    if num and t.startswith(num):
        t = t[len(num):]
    t = t.lstrip(" .-\t").rstrip()
    if t.upper() == t and any(c.isalpha() for c in t):
        t = t.capitalize()
    if len(t) > LARGO_TITULO:
        t = t[:LARGO_TITULO - 1].rstrip() + "…"
    return t


def parte_de(n: dict, ix: dict) -> str:
    x = n
    while x is not None and x["tipo"] != "parte":
        x = ix.get(x.get("padre"))
    if x is not None:
        tit = comun.sin_tilde(x.get("titulo") or "").upper()
        for clave, nombre in PARTES:
            if clave in tit:
                return nombre
    return {"1": "Administrativas", "2": "Técnicas", "3": "Económicas"}.get((n.get("numero") or "").split(".")[0], "")


def texto_vig(n: dict) -> str | None:
    v = comun.vigente(n)
    return (v.get("texto") or "") if v is not None else None


def texto_original(n: dict, bases_id: str) -> str | None:
    for v in n.get("versiones") or []:
        if (v.get("acto") or {}).get("id") == bases_id:
            return v.get("texto") or ""
    return None


class Concesion:
    """Árbol de una concesión y sus filas de artículo (nivel x.y.z con los sub-artículos plegados)."""

    def __init__(self, cid: str, ci: int):
        self.cid, self.ci = cid, ci
        self.arbol, self.etiqueta, self.carpeta = comun.version_reciente(cid)
        self.ix = comun.indice(self.arbol)
        self.bases_id = comun.acto_bases(self.arbol)
        actos = self.arbol["actos"]
        fechas = fechas_actos(actos)
        orden = sorted(range(len(actos)), key=lambda i: (i != 0, fechas[i], i))
        self.actos = [actos[i] for i in orden]
        self.k_de = {actos[i]["id"]: k for k, i in enumerate(orden)}
        self.conc_actos = [[nombre_acto(actos[i]), fechas[i], tipo_acto(actos[i])] for i in orden]
        self.adj = next((k for k, a in enumerate(self.conc_actos) if a[2] == "decreto adjudicacion"), -1)
        self._filas()

    def _filas(self):
        ix = self.ix
        vistos, arts = set(), []
        for n in self.arbol["nodos"]:             # el árbol puede traer un mismo nodo repetido (CN 1.9.11)
            if n["tipo"] == "articulo" and n["id"].startswith("BL:") and n["id"] not in vistos:
                vistos.add(n["id"])
                arts.append(n)
        self.art_por_clave = {clave_numero(n["numero"]): n["id"] for n in arts if n.get("numero")}
        top = [n for n in arts if (ix.get(n.get("padre")) or {}).get("tipo") != "articulo" and not n.get("eliminado_por")]
        top.sort(key=lambda n: orden_numero(n["numero"]))
        self.filas = top
        self.fila_de: dict[str, int] = {}      # id de artículo (o sub-artículo) → índice local de fila
        self.subs: list[list[str]] = []
        self.incisos: list[list[dict]] = []     # incisos BL: de cada fila (incluye los de sus sub-artículos)
        self.nodos_fila: list[list[dict]] = []  # todos los nodos descendientes de la fila
        for i, f in enumerate(top):
            subs, incs, todos = [], [], []
            pila, vistos = [f["id"]], set()
            while pila:
                x = ix[pila.pop()]
                if x["id"] in vistos or x.get("eliminado_por") and x["tipo"] == "articulo":
                    continue
                vistos.add(x["id"])
                todos.append(x)
                if x["tipo"] == "articulo":
                    self.fila_de[x["id"]] = i
                    if x["id"] != f["id"]:
                        subs.append(x["numero"])
                elif x["tipo"] == "inciso" and x["id"].startswith("BL:"):
                    incs.append(x)
                pila.extend(reversed(x.get("hijos") or []))
            subs.sort(key=orden_numero)
            self.subs.append(subs)
            self.incisos.append(incs)
            self.nodos_fila.append(todos)

    def destino(self, clave: str) -> tuple[int, str] | None:
        """Fila y número de artículo citado por una clave de numeral, o None."""
        aid = self.art_por_clave.get(clave)
        if aid is None or aid not in self.fila_de:
            return None
        return self.fila_de[aid], self.ix[aid]["numero"]


def articulo_de(cc: Concesion, n: dict) -> dict | None:
    x = n
    while x is not None and x["tipo"] != "articulo":
        x = cc.ix.get(x.get("padre"))
    return x


def citas_articulos(cc: Concesion):
    """Citas entre filas sobre el texto vigente. Una cita es un par único (artículo o sub-artículo que cita,
    artículo citado), como las aristas `cita` del grafo; al plegar en filas, el peso cuenta esos pares.
    La red «de las Bases originales» es la misma sin los pares que tocan un artículo o sub-artículo agregado
    por un acto posterior. → (peso[(i, j)], peso0[(i, j)], por_sub[j][subnum])."""
    pares = set()
    for i, incs in enumerate(cc.incisos):
        for inc in incs:
            t = texto_vig(inc)
            if not t:
                continue
            a = articulo_de(cc, inc)
            for c in citas(t[:LARGO_TEXTO_CITA]):
                aid = cc.art_por_clave.get(c)
                if aid is None or aid == a["id"] or aid not in cc.fila_de:
                    continue
                pares.add((a["id"], aid))
    peso, peso0, por_sub = Counter(), Counter(), defaultdict(Counter)
    for a, b in pares:
        i, j = cc.fila_de[a], cc.fila_de[b]
        if i == j:
            continue
        peso[(i, j)] += 1
        por_sub[j][cc.ix[b]["numero"]] += 1
        if not cc.ix[a].get("agregado_por") and not cc.ix[b].get("agregado_por"):
            peso0[(i, j)] += 1
    return peso, peso0, por_sub


def pagerank(n: int, peso: Counter, alpha: float = 0.85) -> list[float]:
    import networkx as nx
    D = nx.DiGraph()
    D.add_nodes_from(range(n))
    for (a, b), w in peso.items():
        D.add_edge(a, b, weight=w)
    pr = nx.pagerank(D, alpha=alpha, weight="weight")
    return [pr[i] for i in range(n)]


TIPOS_ACTO = ("acto_posterior", "instruccion", "aclaracion", "formalidad")


def citas_actos(cc: Concesion) -> list[Counter]:
    """Por fila: Counter {k: n} de citas desde actos posteriores. Una cita es un par único (fragmento, artículo
    citado) tomado de `refs`. Si la versión del árbol no trae fragmentos/ propios (RITP 2026-11-11, con otra
    segmentación), las citas se leen con la regex en el texto vigente de los nodos de actos del árbol."""
    out = [Counter() for _ in cc.filas]
    pares = set()
    if (cc.carpeta / "fragmentos").exists() or cc.carpeta == comun.ENTRADA / cc.cid:
        for f in comun.fragmentos(cc.cid, cc.carpeta):
            k = cc.k_de.get(f.get("acto"))
            for r in f.get("refs") or []:
                pares.add((f["id"], k, cc.art_por_clave.get(clave_numero(r))))
    else:
        vistos = set()
        for n in cc.arbol["nodos"]:
            if n["tipo"] not in TIPOS_ACTO or n["id"] in vistos:
                continue
            vistos.add(n["id"])
            vs = [v for v in n.get("versiones") or [] if v.get("vigente")]
            if not vs:
                continue
            k = cc.k_de.get((vs[0].get("acto") or {}).get("id"))
            for c in citas(chr(10).join(v.get("texto") or "" for v in vs)):
                pares.add((n["id"], k, cc.art_por_clave.get(c)))
    for _, k, aid in pares:
        if k and aid in cc.fila_de:
            out[cc.fila_de[aid]][k] += 1
    return out


def etiqueta_inciso(n: dict) -> str:
    m = re.match(r"BL:(.+?)-([a-z]+)(\d+)$", n["id"])
    if m:
        return f"{m.group(1)} ¶{m.group(3)}"
    return n["id"]


def corto(t: str, largo: int) -> str:
    t = " ".join((t or "").split()).strip('"“”')
    return t if len(t) <= largo else t[:largo - 1].rstrip() + "…"


def rotulo(t: str, largo: int = 40) -> str:
    """Etiqueta de tabla/cuadro: si pasa de 40 caracteres se corta en el último espacio dentro de los 40 y se agrega «…»."""
    if len(t) <= largo:
        return t
    return t[:largo].rsplit(" ", 1)[0] + " …"


def lineas_de(v: dict) -> frozenset:
    return frozenset((l.get("doc"), n) for l in v.get("lineas") or [] for n in l.get("lineas") or [])


def historia(cc: Concesion, i: int) -> list:
    """Cambios de la fila por acto: [[k, [[tipo, inciso, texto]]]], ordenados por inciso (texto) dentro de cada k.
    Reglas deducidas del original:
    - un inciso aporta una sola edición por acto (su versión más nueva);
    - las tablas aportan «agrega» con su rótulo (sin repetir), y un artículo agregado, «agrega · artículo completo»;
    - un inciso eliminado aporta «elimina» en el acto de su versión y en el que la reemplaza (`reemplazado_por`);
    - si la versión de un inciso no «cuenta» y repite las líneas de una versión anterior de otro nodo del artículo
      (texto que se movió de inciso), esa versión anterior es la edición real: se informa en su acto con el tipo
      del inciso actual, y en el acto de la versión repetida el inciso aparece como «agrega»."""
    por_k = defaultdict(list)
    cand = []          # (nodo, k, versión) edición candidata, una por nodo y acto
    for x in cc.nodos_fila[i]:
        if x["tipo"] == "tabla":
            v = (x.get("versiones") or [None])[0]
            k = cc.k_de.get(((v or {}).get("acto") or {}).get("id"))
            e = ["agrega", rotulo(x.get("titulo") or ""), ""]
            if k and e not in por_k[k]:
                por_k[k].append(e)
            continue
        if x["tipo"] == "articulo" and x.get("agregado_por"):
            k = cc.k_de.get(x["agregado_por"].get("id"))
            if k and ["agrega", "artículo completo", ""] not in por_k[k]:
                por_k[k].append(["agrega", "artículo completo", ""])
        if x["tipo"] == "inciso_eliminado":
            for v in x.get("versiones") or []:
                for k in {cc.k_de.get((v.get("acto") or {}).get("id")), cc.k_de.get(v.get("reemplazado_por"))}:
                    if k:        # el acto de la versión y el acto que la reemplaza
                        por_k[k].append(["elimina", x.get("titulo") or "", corto(v.get("texto") or "", LARGO_TEXTO_H)])
            continue
        vistos_k = set()
        for v in x.get("versiones") or []:        # la más nueva primero
            k = cc.k_de.get((v.get("acto") or {}).get("id"))
            if not v.get("operacion") or not k or k in vistos_k:
                continue
            vistos_k.add(k)
            cand.append((x, k, v))
    kept = {id(v) for _, _, v in cand}
    retipo, anuladas, extra = {}, set(), []
    for x, k, v in cand:
        L = lineas_de(v)
        if v.get("cuenta", True) or not L:
            continue
        previa = None                          # la versión anterior más reciente con las mismas líneas
        for y in cc.nodos_fila[i]:
            for w in y.get("versiones") or []:
                k2 = cc.k_de.get((w.get("acto") or {}).get("id"))
                if w is not v and k2 and k2 < k and w.get("operacion") and w.get("cuenta", True) and lineas_de(w) == L                         and (previa is None or k2 > previa[0]):
                    previa = (k2, y, w)
        if previa is None:
            continue
        k2, y, w = previa
        if id(w) in kept and y is x:           # mismo inciso: la edición anterior toma el tipo de la repetida
            retipo[id(w)] = v["operacion"]
            v_tipo = "agrega"
        else:                                  # texto movido de inciso (o versión descartada del mismo inciso): se informa en su acto original
            extra.append((k2, [v["operacion"], etiqueta_inciso(x), corto(v.get("texto") or "", LARGO_TEXTO_H)]))
            v_tipo = "agrega"
        retipo[id(v)] = v_tipo
    for x, k, v in cand:
        por_k[k].append([retipo.get(id(v), v["operacion"]), etiqueta_inciso(x), corto(v.get("texto") or "", LARGO_TEXTO_H)])
    for k, e in extra:
        por_k[k].append(e)
    return [[k, sorted(por_k[k], key=lambda e: e[1])] for k in sorted(por_k)]


def grupo1(ccs: list[Concesion]) -> dict:
    arts = {k: [] for k in ["c", "id", "num", "t", "parte", "x", "y", "pr", "sale", "entra", "ct", "h", "ca", "sub",
                            "nueva", "nuevo", "pr0", "sw", "ci", "cs", "base", "cm"]}
    for cc in ccs:
        g0 = len(arts["c"])
        n = len(cc.filas)
        peso, peso0, por_sub = citas_articulos(cc)
        pr = pagerank(n, peso)
        nuevos = [1 if f.get("agregado_por") else 0 for f in cc.filas]
        viejos = [i for i in range(n) if not nuevos[i]]
        loc = {i: j for j, i in enumerate(viejos)}
        pr0v = pagerank(len(viejos), Counter({(loc[a], loc[b]): w for (a, b), w in peso0.items()
                                               if a in loc and b in loc}))
        sale = defaultdict(list)
        entra = defaultdict(list)
        for (a, b) in sorted(peso):
            sale[a].append(b)
            entra[b].append(a)
        ca = citas_actos(cc)
        for i, f in enumerate(cc.filas):
            arts["c"].append(cc.ci)
            arts["id"].append(f["id"])
            arts["num"].append(f["numero"])
            arts["t"].append(titulo_fila(f))
            arts["parte"].append(parte_de(f, cc.ix))
            arts["pr"].append(round(pr[i], 5))
            arts["pr0"].append(round(pr0v[loc[i]], 5) if i in loc else 0.0)
            s = sorted(sale[i])
            arts["sale"].append([g0 + j for j in s])
            arts["sw"].append([peso[(i, j)] for j in s])
            arts["entra"].append([g0 + j for j in sorted(entra[i])])
            arts["ci"].append(sum(peso[(j, i)] for j in entra[i]))
            cs = sorted(por_sub[i].items(), key=lambda kv: (-kv[1], orden_numero(kv[0])))[:CORTE_CS]
            arts["cs"].append([[a, b] for a, b in cs])
            arts["ca"].append([[k, ca[i][k]] for k in sorted(ca[i])])
            arts["h"].append(historia(cc, i))
            arts["sub"].append(cc.subs[i])
            arts["nueva"].append([g0 + j for j in s if (i, j) not in peso0])
            arts["nuevo"].append(nuevos[i])
    return arts


# ======================================================================== grupo 2

DIM_LSA = 150           # dimensiones del LSA
UMBRAL_CT = 0.5         # φ mínimo para `ct` (coseno LSA)
UMBRAL_BASE = 0.45      # φ mínimo para unir dos artículos en una base común
K_VECINOS = 30          # vecinos del grafo de comunidades
RESOLUCION = 0.85       # resolución de Louvain
SEMILLA = 7             # LSA y t-SNE
SEMILLA_LOUVAIN = 1
LARGO_TEXTO_VEC = 8000  # caracteres de texto por artículo que entran al vector


def textos_filas(ccs: list[Concesion], vigente: bool = True) -> list[str]:
    out = []
    for cc in ccs:
        for i, f in enumerate(cc.filas):
            partes = [titulo_fila(f)]
            for inc in cc.incisos[i]:
                t = texto_vig(inc) if vigente else texto_original(inc, cc.bases_id)
                if t:
                    partes.append(t)
            out.append(" ".join(partes)[:LARGO_TEXTO_VEC])
    return out


def similitud(textos: list[str], dim: int = DIM_LSA):
    X = comun.vectores(textos, modo="lsa", dim=dim, semilla=SEMILLA)
    return X @ X.T


def pares_ct(S, c: list[int], umbral: float = UMBRAL_CT) -> list[list]:
    """Por artículo: el más parecido de cada otra concesión (φ ≥ umbral, 2 decimales), ordenado por concesión."""
    import numpy as np
    c = np.asarray(c)
    out = []
    for g in range(len(c)):
        fila = []
        for cj in sorted(set(c.tolist()) - {int(c[g])}):
            idx = np.flatnonzero(c == cj)
            j = int(idx[np.argmax(S[g, idx])])
            if round(float(S[g, j]), 2) >= umbral:
                fila.append([j, round(float(S[g, j]), 2)])
        out.append(fila)
    return out


def calcula_bases(S, c: list[int], umbral: float = UMBRAL_BASE) -> list[list[int]]:
    """Bases comunes: pares recíprocos (cada artículo es el mejor del otro en la concesión del otro, φ ≥ umbral)
    unidos de mayor a menor φ, sin juntar dos artículos de una misma concesión en un grupo.
    → grupos de g ordenados por (tamaño descendente, g del primer miembro), miembros por concesión."""
    import numpy as np
    c = np.asarray(c)
    N = len(c)
    mejor = {}
    for g in range(N):
        for cj in set(c.tolist()) - {int(c[g])}:
            idx = np.flatnonzero(c == cj)
            mejor[(g, cj)] = int(idx[np.argmax(S[g, idx])])
    pares = sorted(((float(S[g, j]), g, j) for (g, cj), j in mejor.items()
                    if g < j and mejor[(j, int(c[g]))] == g and S[g, j] >= umbral), reverse=True)
    grupo = list(range(N))
    miembros = {g: [g] for g in range(N)}
    for _, g, j in pares:
        a, b = grupo[g], grupo[j]
        if a == b or {int(c[x]) for x in miembros[a]} & {int(c[x]) for x in miembros[b]}:
            continue
        for x in miembros[b]:
            grupo[x] = a
        miembros[a] += miembros.pop(b)
    gs = [sorted(m, key=lambda x: (int(c[x]), x)) for m in miembros.values()]
    return sorted(gs, key=lambda m: (-len(m), m[0]))


def norm_titulo(t: str) -> str:
    t = t.lower().rstrip("…").strip()
    while True:
        t2 = re.sub(r"^(del|de|la|las|los|el)\s+", "", t)
        if t2 == t:
            return t
        t = t2


def comunidades_louvain(S, k: int = K_VECINOS, resolucion: float = RESOLUCION, semilla: int = SEMILLA_LOUVAIN) -> list[int]:
    """Louvain sobre el grafo de k vecinos más parecidos (peso = φ positivo). Las comunidades se numeran por
    tamaño descendente."""
    import networkx as nx
    import numpy as np
    N = S.shape[0]
    G = nx.Graph()
    G.add_nodes_from(range(N))
    for g in range(N):
        fila = S[g].copy()
        fila[g] = -1
        for j in np.argsort(-fila)[:k]:
            if S[g, j] > 0:
                w = float(S[g, j])
                if G.has_edge(g, int(j)):
                    w = max(w, G[g][int(j)]["weight"])
                G.add_edge(g, int(j), weight=w)
    com = nx.community.louvain_communities(G, weight="weight", resolution=resolucion, seed=semilla)
    com = sorted(com, key=lambda s: (-len(s), min(s)))
    cm = [0] * N
    for i, s_ in enumerate(com):
        for g in s_:
            cm[g] = i
    return cm


def nombra_comunidades(titulos: list[str], cm: list[int], c: list[int], S) -> list[dict]:
    """{n, t, conc, ej}: nombre con los términos tf-idf más distintivos de los títulos de la comunidad,
    ejemplos = los títulos distintos más cercanos al centro de la comunidad."""
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    ncom = max(cm) + 1
    docs = [" ".join(titulos[g] for g in range(len(cm)) if cm[g] == i) for i in range(ncom)]
    tf = TfidfVectorizer(preprocessor=comun.sin_tilde, token_pattern=r"(?u)\b[a-zñ]{4,}\b",
                         stop_words=sorted(comun.STOP), sublinear_tf=True)
    M = tf.fit_transform(docs)
    vocab = list(tf.get_feature_names_out())
    conAcento = {}                    # palabra sin tilde → forma más común en los títulos
    for w, n_ in Counter(w.lower() for t_ in titulos for w in re.findall(r"[^\W\d_]{4,}", t_)).most_common():
        conAcento.setdefault(comun.sin_tilde(w), w)
    out = []
    for i in range(ncom):
        miembros = [g for g in range(len(cm)) if cm[g] == i]
        fila = M[i].toarray().ravel()
        top = []
        for j in np.argsort(-fila):
            if fila[j] <= 0 or len(top) == 2:
                break
            if not any(vocab[j][:5] == u[:5] for u in top):      # sin variantes de la misma raíz
                top.append(vocab[j])
        top = [conAcento.get(w, w) for w in top]
        nombre = " y ".join(top).capitalize() if top else f"Grupo {i + 1}"
        centro = S[np.ix_(miembros, miembros)].mean(axis=1)
        ej, vistos = [], set()
        for g in (miembros[j] for j in np.argsort(-centro)):
            n_ = norm_titulo(titulos[g])
            if n_ and n_ not in vistos and not titulos[g].startswith("["):
                vistos.add(n_)
                ej.append(titulos[g])
            if len(ej) == 4:
                break
        out.append({"n": len(miembros), "t": nombre, "conc": len({c[g] for g in miembros}), "ej": ej})
    return out


def proyeccion_2d(S):
    """Proyección 2D propia: t-SNE sobre la distancia 1 - φ (semilla fija), escalada a máx |coord| = 1."""
    import numpy as np
    from sklearn.manifold import TSNE
    D = np.clip(1.0 - S, 0, None)
    np.fill_diagonal(D, 0)
    P = TSNE(n_components=2, metric="precomputed", init="random", perplexity=15, random_state=SEMILLA,
             max_iter=1500).fit_transform(D)
    return P / np.abs(P).max()


def fuerza_centroides(P, cm: list[int], claves: list[tuple], orig: dict, alfa: float = 1.0):
    """CENTROIDES FORZADOS (pedido del usuario): los centroides de las comunidades vienen del artefacto original.
    Cada comunidad del clon se empareja con una del original (Hungarian sobre los artículos que comparten, por
    (cod, num)); se traslada para que su centroide coincida con el del original y se escala su dispersión al
    radio RMS de la comunidad original. Luego se recorta a [-1, 1] (reescalar movería los centroides) y se
    vuelve a centrar; la coordenada más extrema se deja en ±1."""
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    A = orig["arts"]
    pos = {(A["c"][i], A["num"][i]): i for i in range(len(A["c"]))}
    ox = np.array([[A["x"][i], A["y"][i]] for i in range(len(A["c"]))])
    ocm = np.array(A["cm"])
    nc, no = max(cm) + 1, int(ocm.max()) + 1
    M = np.zeros((nc, no))
    for g, k in enumerate(claves):
        if k in pos:
            M[cm[g], ocm[pos[k]]] += 1
    filas, cols = linear_sum_assignment(-M)
    cm_ = np.asarray(cm)
    Q = P.copy()
    objetivo = {}
    for a, b in zip(filas, cols):
        mi = np.flatnonzero(cm_ == a)
        if len(mi) == 0:
            continue
        cen_o = ox[ocm == b].mean(axis=0)
        r_o = np.sqrt(((ox[ocm == b] - cen_o) ** 2).sum(axis=1).mean())
        cen_c = P[mi].mean(axis=0)
        r_c = np.sqrt(((P[mi] - cen_c) ** 2).sum(axis=1).mean()) or 1.0
        Q[mi] = cen_o + (P[mi] - cen_c) * (alfa * r_o / r_c)
        objetivo[a] = (mi, cen_o)
    for _ in range(20):                        # recortar a [-1, 1] y recentrar sin reescalar
        Q = np.clip(Q, -1.0, 1.0)
        for a, (mi, cen_o) in objetivo.items():
            Q[mi] += cen_o - Q[mi].mean(axis=0)
    Q = np.clip(Q, -1.0, 1.0)
    if np.abs(Q).max() < 1.0:                  # sin punto en el borde: el más extremo pasa a ±1
        i, j = np.unravel_index(np.abs(Q).argmax(), Q.shape)
        Q[i, j] = np.sign(Q[i, j])
    return Q


def correlacion_distancias(P, claves: list[tuple], orig: dict) -> float:
    """Pearson de las distancias por pares entre el original y la proyección (como el validador)."""
    import numpy as np
    from scipy.spatial.distance import pdist
    A = orig["arts"]
    pos = {(A["c"][i], A["num"][i]): i for i in range(len(A["c"]))}
    com = [(g, pos[k]) for g, k in enumerate(claves) if k in pos]
    Xc = np.array([P[g] for g, _ in com])
    Xo = np.array([[A["x"][i], A["y"][i]] for _, i in com])
    return float(np.corrcoef(pdist(Xo), pdist(Xc))[0, 1])


def arma_bases(grupos: list[list[int]], arts: dict) -> dict:
    B = {"m": [], "t": [], "x": [], "y": []}
    for m in grupos:
        tit = Counter(norm_titulo(arts["t"][g]) for g in m)
        mejor = max(tit.values())
        t_ = next(arts["t"][g] for g in m if tit[norm_titulo(arts["t"][g])] == mejor)
        B["m"].append(m)
        B["t"].append(t_)
        B["x"].append(round(sum(arts["x"][g] for g in m) / len(m), 4))
        B["y"].append(round(sum(arts["y"][g] for g in m) / len(m), 4))
    return B


# ======================================================================== principal

def main():
    t0 = time.time()
    ccs = [Concesion(cid, ci) for ci, cid in enumerate(comun.ORDEN)]
    conc = []
    for cc in ccs:
        corto_, largo, color = comun.CONC[cc.cid]
        conc.append({"cod": cc.cid, "nombre": corto_, "largo": largo, "color": color, "adj": cc.adj,
                     "actos": cc.conc_actos})
    print(f"  árboles cargados ({time.time() - t0:.1f} s)", flush=True)
    arts = grupo1(ccs)
    print(f"  grupo 1 listo: {len(arts['c'])} filas ({time.time() - t0:.1f} s)", flush=True)
    import numpy as np
    S = similitud(textos_filas(ccs))
    c = arts["c"]
    arts["ct"] = pares_ct(S, c)
    grupos = calcula_bases(S, c)
    arts["cm"] = comunidades_louvain(S)
    claves = list(zip(c, arts["num"]))
    original = comun.original("tablero_datos.js")
    P0 = proyeccion_2d(S)
    P = fuerza_centroides(P0, arts["cm"], claves, original)
    arts["x"] = [round(float(v), 4) for v in P[:, 0]]
    arts["y"] = [round(float(v), 4) for v in P[:, 1]]
    r0, r1 = (correlacion_distancias(Q, claves, original) for Q in (P0, P))
    print(f"  x/y: correlación de distancias con el original: t-SNE {r0:.3f} · centroides forzados {r1:.3f}")
    bases = arma_bases(grupos, arts)
    arts["base"] = [0] * len(c)
    for b, m in enumerate(grupos):
        for g in m:
            arts["base"][g] = b
    print(f"  grupo 2 listo: {len(grupos)} bases, {max(arts['cm']) + 1} comunidades ({time.time() - t0:.1f} s)", flush=True)
    tab = {"generado": comun.ahora(), "conc": conc, "arts": arts, "bases": bases,
           "comunidades": nombra_comunidades(arts["t"], arts["cm"], c, S)}
    comun.escribir_js(SALIDA, "window.TAB", tab)
    print(f"  escrito {SALIDA} ({time.time() - t0:.1f} s)")


if __name__ == "__main__":
    main()
