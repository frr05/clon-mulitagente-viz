"""Utilidades comunes del generador del clon (las mantiene el orquestador; ver ESPEC.md).

Carga los árboles de entrada (entrada/data/<ID>/, foto de arbol-de-nodos de la mañana del 2026-11-24),
lee los datos del original (_original/*.js) para comparar, escribe los .js del visor y calcula vectores
de contenido (tf-idf + LSA por defecto; bge-m3 desde un .npz si existe y se pide).
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "entrada" / "data"
ORIGINAL = RAIZ / "_original"
VISOR = RAIZ / "visor"

sys.path.insert(0, str(RAIZ / "entrada" / "grafo"))
from numerales import citas, clave_numero, orden_numero, RE_CITA  # noqa: E402,F401

ORDEN = ["CN", "LOA", "RITP", "AVO", "PCNP-2"]
CONC = {  # constantes de presentación, iguales a las del original
    "CN": ("Costanera Norte", "Concesión Sistema Oriente – Poniente (Costanera Norte)", "#D98A1E"),
    "LOA": ("Rutas del Loa", "Primera Concesión Rutas del Loa", "#1A937A"),
    "RITP": ("Talcahuano–Penco", "Concesión Ruta Interportuaria Talcahuano – Penco", "#3B47B5"),
    "AVO": ("Vespucio Oriente", "Concesión Américo Vespucio Oriente Príncipe de Gales – Los Presidentes", "#8A55D3"),
    "PCNP-2": ("Nogales–Puchuncaví", "Segunda Concesión Camino Nogales – Puchuncaví", "#D0385E"),
}


# ---------------------------------------------------------------- entradas

def version_reciente(cid: str) -> tuple[dict, str, Path]:
    """Árbol más reciente (por `generado`) entre la carpeta base y versiones/*. → (árbol, etiqueta, carpeta)."""
    base = ENTRADA / cid
    cands = [(base / "nodos_versionados.json", "base", base)]
    for d in sorted((base / "versiones").glob("*/")) if (base / "versiones").exists() else []:
        if (d / "nodos_versionados.json").exists():
            cands.append((d / "nodos_versionados.json", d.name, d))
    mejor = None
    for f, et, carpeta in cands:
        arbol = json.loads(f.read_text(encoding="utf-8"))
        if mejor is None or arbol["generado"] > mejor[0]["generado"]:
            mejor = (arbol, et, carpeta)
    return mejor


def actos_csv(carpeta: Path) -> list[dict]:
    """Filas de actos.csv de la carpeta (base o versión); si la versión no lo trae, None."""
    f = carpeta / "actos.csv"
    if not f.exists():
        return None
    with f.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def fragmentos(cid: str, carpeta: Path | None = None) -> list[dict]:
    """Todos los fragmentos (con `refs`) de la versión; si la versión no trae fragmentos/, los de la base."""
    d = (carpeta / "fragmentos") if carpeta is not None else None
    if d is None or not d.exists():
        d = ENTRADA / cid / "fragmentos"
    out = []
    for f in sorted(d.glob("*.json")):
        out.extend(json.loads(f.read_text(encoding="utf-8")).get("fragmentos", []))
    return out


def indice(arbol: dict) -> dict[str, dict]:
    return {n["id"]: n for n in arbol["nodos"]}


def acto_bases(arbol: dict) -> str:
    return next(a["id"] for a in arbol["actos"] if a.get("tipo") == "bases licitacion")


def vigente(nodo: dict) -> dict | None:
    vs = nodo.get("versiones") or []
    return vs[0] if vs and vs[0].get("vigente") else None


# ---------------------------------------------------------------- original y salida

def leer_js(ruta: Path | str) -> dict:
    """Objeto JSON de un archivo `window.X = {...};` (para matriz toma la última asignación)."""
    t = Path(ruta).read_text(encoding="utf-8")
    linea = [l for l in t.splitlines() if l.strip()][-1]
    return json.loads(linea[linea.index("=") + 1:].strip().rstrip(";"))


def original(nombre: str) -> dict:
    return leer_js(ORIGINAL / nombre)


def escribir_js(ruta: Path | str, var: str, obj, previo: str = "") -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    cuerpo = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    ruta.write_text(f"{previo}{var} = {cuerpo};\n", encoding="utf-8")


def ahora() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- texto y vectores

def sin_tilde(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


STOP = set("""a al algo ante antes como con contra cual cuando de del desde donde durante e el ella ellas ellos en entre
era es esa ese eso esta este esto estos estas fue ha hasta la las le les lo los mas me mismo muy no nos o otra otro otros
para pero por que quien se sea segun ser si sin sobre su sus tal tambien te tiene todo todos tu un una uno unos unas y ya
dicha dicho dichas dichos cada debera deberan sera seran podra podran articulo articulos letra numero n""".split())


def vectores(textos: list[str], modo: str = "lsa", dim: int = 150, semilla: int = 7, npz: dict | None = None):
    """Matriz (n × d) de vectores L2-normalizados.
    modo "lsa": tf-idf (palabras sin tildes, sublinear) → TruncatedSVD(dim) → centrado → L2.
    modo "npz": `npz` = {"vectores": array alineado con `textos`} ya promediado por el llamador (bge-m3)."""
    import numpy as np
    if modo == "npz":
        X = np.asarray(npz["vectores"], dtype=float)
    else:
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        tf = TfidfVectorizer(preprocessor=sin_tilde, token_pattern=r"(?u)\b[a-zñ]{3,}\b",
                             stop_words=sorted(STOP), sublinear_tf=True, min_df=2, max_df=0.6)
        M = tf.fit_transform(textos)
        k = max(2, min(dim, M.shape[1] - 1, M.shape[0] - 1))
        X = TruncatedSVD(n_components=k, random_state=semilla).fit_transform(M)
        X = X - X.mean(axis=0)
    nrm = np.linalg.norm(X, axis=1, keepdims=True)
    nrm[nrm == 0] = 1
    return X / nrm


# ---------------------------------------------------------------- avance

class Avance:
    """Muestra % y tiempo restante en procesos largos: `av = Avance(n, 'etiqueta'); av.paso()`."""

    def __init__(self, total: int, etiqueta: str = ""):
        self.total, self.et, self.i, self.t0 = max(1, total), etiqueta, 0, time.time()

    def paso(self, k: int = 1):
        self.i += k
        if self.i == self.total or self.i % max(1, self.total // 20) == 0:
            dt = time.time() - self.t0
            resta = dt / self.i * (self.total - self.i)
            print(f"  {self.et} {100 * self.i // self.total:3d} %  ~{resta:4.0f} s restantes", flush=True)
