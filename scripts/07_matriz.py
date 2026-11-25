"""Genera visor/matriz/datos_RITP.js (window.MATRIZ["RITP"]) — matriz de similitud entre artículos de las Bases
de RITP, ordenada por un dendrograma de Ward (ver ESPEC.md §3).

    python scripts/07_matriz.py                  # tf-idf + LSA (por defecto) → visor/matriz/datos_RITP.js
    python scripts/07_matriz.py --vectores npz   # bge-m3 de EMBEDDINGS_RITP.npz → visor/matriz/datos_RITP_bge.js
    python scripts/07_matriz.py --vectores npz --salida otra/ruta.js

Grupo 1 (determinista: unidades, a, t, p, f, x)
  * Fragmentos = los chunks de CHUNKS_RITP.jsonl que se embebieron (`embeber`, los mismos ids del .npz), menos
    los de actos posteriores (`acto_posterior`), la ficha y la portada (BL:0). Entran incisos, grupos de incisos,
    párrafos (#pN), artículos sin incisos, aclaraciones, incisos eliminados, tablas y filas de tabla.
  * Cada fragmento va al artículo de su metadato `articulo.numero`, salvo las tablas (TABLA:…), que van al
    artículo que las contiene en el árbol elegido (versiones/2026-11-11); una tabla que ya no está en ese árbol
    se descarta. El número se trunca a x.y.z: los sub-artículos x.y.z.w se pliegan en su x.y.z.
  * Una unidad (fila) es cada número x, x.y o x.y.z con al menos un fragmento → 169 (incluye «3» y A1–A4).
  * a = número; p = parte según el primer carácter (1 Administrativas, 2 Técnicas, 3 Económicas, A Anexos);
    f = fragmentos promediados.
  * t = título del nodo del árbol sin el número delante (si el nodo no existe en el árbol, el número).
  * x = textos vigentes de los nodos `inciso` del árbol cuyo artículo trunca a esa unidad, en orden del árbol,
    unidos, con los espacios colapsados y cortados a 420 caracteres.

Grupo 2 (similitud)
  * Vector de unidad = promedio de los vectores de sus fragmentos (bge-m3 normalizados, o tf-idf + LSA),
    normalizado. S = coseno × 1000 entero.
  * «Fila» = índice de la unidad con las unidades en orden alfabético del número; Z = Ward (scipy) sobre esos
    índices, sin la columna de conteo; `hoja_a_fila[fila]` = posición de la fila entre las hojas del dendrograma.
  * `arts`, `S`, `lab` y `rep` van en orden de hoja (el que dibuja el visor).
  * cortes K = 4..16: lab (fcluster maxclust, renumerado por orden de aparición en las hojas), kw (6 términos
    tf-idf), rep (3 con mayor similitud media dentro del grupo), coh (similitud media entre pares), corte
    (punto medio entre Z[-K][2] y Z[-K+1][2]) y nombre (generado desde kw y títulos).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

CID = "RITP"
SALIDA = {"lsa": comun.VISOR / "matriz" / "datos_RITP.js", "npz": comun.VISOR / "matriz" / "datos_RITP_bge.js"}
MODELO = {"lsa": "tfidf-lsa", "npz": "baai/bge-m3"}
LARGO_X = 420
KS = range(4, 17)
N_KW = 6
N_REP = 3
EXCLUIR_TIPOS = {"acto_posterior", "ficha"}
PARTE = {"1": "Administrativas", "2": "Técnicas", "3": "Económicas", "A": "Anexos"}
TIPOS_SECCION = ("articulo", "capitulo", "parte")


def x_y_z(numero: str) -> str:
    return ".".join(numero.split(".")[:3])


# ======================================================================== grupo 1

def articulo_en_arbol(I: dict, nid: str) -> str | None:
    """Número del artículo/capítulo/parte que contiene al nodo `nid` en el árbol (None si no está)."""
    n = I.get(nid)
    while n is not None and n["tipo"] not in TIPOS_SECCION:
        n = I.get(n.get("padre"))
    return n["id"][3:] if n is not None else None


def leer_fragmentos(I: dict) -> tuple[dict[str, list[dict]], int]:
    """Fragmentos embebidos agrupados por unidad x.y.z (en el orden del archivo de chunks)."""
    ruta = comun.ENTRADA / CID / f"CHUNKS_{CID}.jsonl"
    grupos: dict[str, list[dict]] = defaultdict(list)
    descartadas = 0
    with ruta.open(encoding="utf-8") as fh:
        for linea in fh:
            c = json.loads(linea)
            m = c["metadatos"]
            if not c.get("embeber") or m["tipo_nodo"] in EXCLUIR_TIPOS:
                continue
            if m.get("id_tabla"):
                num = articulo_en_arbol(I, m["id_tabla"])
                if num is None:           # tabla que el árbol elegido ya no tiene
                    descartadas += 1
                    continue
            elif m.get("articulo"):
                num = m["articulo"]["numero"]
            else:
                continue
            u = x_y_z(num)
            if u == "0":                  # portada e índice
                continue
            grupos[u].append(c)
    return grupos, descartadas


def textos_arbol(arbol: dict, I: dict) -> dict[str, list[str]]:
    """Textos vigentes de los incisos del árbol, por unidad x.y.z, en orden del árbol."""
    out: dict[str, list[str]] = defaultdict(list)

    def recorrer(nid: str, art: str | None):
        n = I[nid]
        if n["tipo"] in TIPOS_SECCION:
            art = n["id"][3:]
        if n["tipo"] == "inciso" and art:
            v = comun.vigente(n)
            if v and v.get("texto"):
                out[x_y_z(art)].append(v["texto"])
        for h in n["hijos"]:
            recorrer(h, art)

    for r in arbol["raices"]:
        recorrer(r, None)
    return out


def titulo(I: dict, u: str) -> str:
    n = I.get("BL:" + u)
    if n is None:
        return u
    t = (n.get("titulo") or "").strip()
    if t == u:
        return u
    if t.startswith(u + " "):
        return t[len(u):].strip()
    return t


def unidades(arbol: dict) -> tuple[list[dict], list[list[dict]], int]:
    """Filas (orden alfabético del número) con a, t, p, f, x y sus fragmentos."""
    I = comun.indice(arbol)
    grupos, descartadas = leer_fragmentos(I)
    textos = textos_arbol(arbol, I)
    filas = sorted(grupos)
    arts = []
    for u in filas:
        x = " ".join(" ".join(textos.get(u, [])).split())[:LARGO_X]
        arts.append({"a": u, "t": titulo(I, u), "p": PARTE[u[0]], "f": len(grupos[u]), "x": x})
    return arts, [grupos[u] for u in filas], descartadas


# ======================================================================== grupo 2

def vectores_unidad(frags: list[list[dict]], modo: str) -> np.ndarray:
    """Promedio por unidad de los vectores de sus fragmentos, normalizado (n_unidades × d)."""
    if modo == "npz":
        z = np.load(comun.ENTRADA / CID / f"EMBEDDINGS_{CID}.npz")
        pos = {str(i): k for k, i in enumerate(z["ids"])}
        V = z["vectores"].astype(np.float64)
        V /= np.linalg.norm(V, axis=1, keepdims=True).clip(1e-12)
        faltan = sum(1 for fs in frags for c in fs if c["id"] not in pos)
        if faltan:
            print(f"  aviso: {faltan} fragmentos sin vector en el .npz (se omiten)")
        M = np.array([V[[pos[c["id"]] for c in fs if c["id"] in pos]].mean(axis=0) for fs in frags])
    else:
        planos = [c for fs in frags for c in fs]
        X = comun.vectores([c["texto_embedding"] for c in planos], modo="lsa")
        M, k = [], 0
        for fs in frags:
            M.append(X[k:k + len(fs)].mean(axis=0))
            k += len(fs)
        M = np.array(M)
    M /= np.linalg.norm(M, axis=1, keepdims=True).clip(1e-12)
    return M


def texto_kw(fs: list[dict]) -> str:
    return " ".join(c["texto"] for c in fs)


def terminos_kw(docs: list[str]):
    """tf-idf (1–2 palabras, minúsculas sin tildes) de cada unidad, para las palabras clave de los grupos."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    tf = TfidfVectorizer(preprocessor=comun.sin_tilde, token_pattern=r"(?u)\b[a-zñ]{3,}\b",
                         stop_words=sorted(comun.STOP | STOP_KW), ngram_range=(1, 2),
                         sublinear_tf=True, min_df=2, max_df=0.5)
    T = tf.fit_transform(docs)
    return T, np.array(tf.get_feature_names_out())


STOP_KW = set("""sociedad concesionaria presentes bases caso forma dias deberan debe deben podra cual cuales
mediante respectivo respectiva siguiente siguientes acuerdo establecido establecida indicado indicada senalado
senalada conformidad""".split())


def nombre_grupo(kw: list[str], titulos: list[str], usados: set[str]) -> str:
    """Nombre corto automático: las dos palabras clave más fuertes que aparecen en los títulos del grupo
    (o, si no hay, las dos primeras palabras clave), en forma «Xxx y yyy»."""
    tit = comun.sin_tilde(" ".join(titulos))
    en_tit = [k for k in kw if re.search(r"\b" + re.escape(k) + r"\b", tit)]
    elegidas = []
    for k in en_tit + kw:
        if k in elegidas or any(k in e or e in k for e in elegidas):
            continue
        elegidas.append(k)
        if len(elegidas) == 2:
            break
    nombre = " y ".join(elegidas)
    nombre = nombre[:1].upper() + nombre[1:]
    base, j = nombre, 2
    while nombre in usados:
        nombre = f"{base} ({j})"
        j += 1
    usados.add(nombre)
    return nombre


def cortes(Z: np.ndarray, hojas: np.ndarray, S: np.ndarray, T, terms, arts_hoja: list[dict]) -> dict:
    """S, T y arts_hoja van en orden de hoja; Z en orden de fila."""
    from scipy.cluster.hierarchy import fcluster
    n = len(hojas)
    out = {}
    for K in KS:
        lab_f = fcluster(Z, K, criterion="maxclust")[hojas]       # etiqueta de cada hoja
        mapa: dict[int, int] = {}
        lab = [mapa.setdefault(int(l), len(mapa)) for l in lab_f]
        kw, rep, coh, nom, usados = [], [], [], [], set()
        for g in range(len(mapa)):
            idx = [i for i in range(n) if lab[i] == g]
            sub = S[np.ix_(idx, idx)]
            m = len(idx)
            media = (sub.sum(axis=1) - 1.0) / max(1, m - 1)
            rep.append([idx[i] for i in sorted(range(m), key=lambda i: -media[i])[:N_REP]])
            coh.append(round(float((sub.sum() - m) / (m * (m - 1))), 3) if m > 1 else 1.0)
            w = np.asarray(T[idx].mean(axis=0)).ravel()
            k6 = [str(terms[j]) for j in np.argsort(-w, kind="stable")[:N_KW]]
            kw.append(k6)
            nom.append(nombre_grupo(k6, [arts_hoja[i]["t"] for i in idx], usados))
        corte = round(float((Z[-K][2] + Z[-K + 1][2]) / 2), 4)
        out[str(K)] = {"lab": lab, "kw": kw, "rep": rep, "coh": coh, "corte": corte, "nombre": nom}
    return out


# ======================================================================== principal

def generar(modo: str) -> dict:
    from scipy.cluster.hierarchy import leaves_list, linkage

    arbol, etiqueta, _ = comun.version_reciente(CID)
    print(f"  árbol {CID}: {etiqueta} ({arbol['generado']})")
    arts, frags, descartadas = unidades(arbol)
    print(f"  {len(arts)} unidades, {sum(a['f'] for a in arts)} fragmentos ({descartadas} de tablas fuera del árbol)")

    M = vectores_unidad(frags, modo)
    Z = linkage(M, method="ward", metric="euclidean")
    hojas = leaves_list(Z)                         # hoja → fila
    hoja_a_fila = np.empty_like(hojas)
    hoja_a_fila[hojas] = np.arange(len(hojas))     # fila → hoja (así lo guarda el original)

    Mh = M[hojas]
    S = np.clip(Mh @ Mh.T, -1.0, 1.0)
    np.fill_diagonal(S, 1.0)
    arts_hoja = [arts[i] for i in hojas]
    T, terms = terminos_kw([texto_kw(frags[i]) for i in hojas])

    return {
        "concesion": arbol["concesion"]["nombre"],
        "modelo": MODELO[modo],
        "arts": arts_hoja,
        "hoja_a_fila": [int(v) for v in hoja_a_fila],
        "Z": [[int(a), int(b), round(float(d), 4)] for a, b, d, _ in Z],
        "cortes": cortes(Z, hojas, S, T, terms, arts_hoja),
        "S": [int(v) for v in np.rint(S * 1000).astype(int).ravel()],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vectores", choices=["lsa", "npz"], default="lsa",
                    help="lsa: tf-idf + LSA (por defecto); npz: bge-m3 de EMBEDDINGS_RITP.npz")
    ap.add_argument("--salida", help="ruta del .js (por defecto datos_RITP.js para lsa y datos_RITP_bge.js para npz)")
    args = ap.parse_args()
    t0 = time.time()
    obj = generar(args.vectores)
    ruta = Path(args.salida) if args.salida else SALIDA[args.vectores]
    comun.escribir_js(ruta, f'window.MATRIZ["{CID}"]', obj, previo="window.MATRIZ = window.MATRIZ || {};\n")
    print(f"  escrito {ruta} ({ruta.stat().st_size // 1024} KB) en {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
