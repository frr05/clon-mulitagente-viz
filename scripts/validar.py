"""Validador del clon «Bases de Licitación · cinco concesiones» (ver ESPEC.md §4).

Compara, valor por valor y emparejando siempre por clave (nunca por índice), los datos del clon
(visor/…) con los del original (_original/…), y escribe VALIDACION.md en la raíz del proyecto.

Uso:
    python scripts/validar.py [tablero|ad|matriz|todo] [--detalle N] [--clon-dir RUTA]
                              [--orig-dir RUTA] [--salida RUTA]

- tablero → tablero_datos.js · ad → antes_despues.js · matriz → matriz/datos_RITP.js
- Si se pide una sola parte, VALIDACION.md solo cambia esa sección y conserva las demás.
- Grupo 1 (deterministas): deben calzar exacto (100 %). Grupo 2 (similitud): métricas con umbral.
- «Estructura»: chequeos que se corren sobre el clon y también sobre el original; si el original
  tampoco los cumple se marca «= original» y no cuenta como falla.
- No lee los generadores (05/06/07): es independiente, basado solo en ESPEC.md y en el original.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

import numpy as np  # noqa: E402
from scipy.spatial.distance import pdist  # noqa: E402
from scipy.stats import pearsonr, spearmanr  # noqa: E402
from sklearn.metrics import adjusted_rand_score  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ARCHIVOS = {"tablero": "tablero_datos.js", "ad": "antes_despues.js", "matriz": "matriz/datos_RITP.js"}
TITULOS = {"tablero": "Tablero · tablero_datos.js", "ad": "Antes/después · antes_despues.js",
           "matriz": "Matriz RITP · matriz/datos_RITP.js"}
PARTES = ["tablero", "ad", "matriz"]
TIPOS_H = {"reemplaza_parrafo", "reemplaza_texto", "reemplaza_articulo", "agrega", "agrega_parrafo",
           "agrega_articulo", "elimina", "agrega_texto", "elimina_texto"}
TOL_PR = 1e-4

PASA, NOPASA, INFO, IGUAL_ORIG = "PASA", "NO PASA", "info", "= original"


# ---------------------------------------------------------------- utilidades

def corto(v, n: int = 240) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    s = s.replace("\n", " ").replace("|", "\\|").replace("`", "'")
    return s if len(s) <= n else s[:n] + "…"


def par_corto(a, b, n: int = 240) -> tuple[str, str]:
    """Ambos valores recortados; si son largos, la ventana empieza cerca de la primera diferencia."""
    sa = a if isinstance(a, str) else json.dumps(a, ensure_ascii=False)
    sb = b if isinstance(b, str) else json.dumps(b, ensure_ascii=False)
    i = next((k for k, (x, y) in enumerate(zip(sa, sb)) if x != y), min(len(sa), len(sb)))
    if i > n - 60:
        ini = i - 60
        return "…" + corto(sa[ini:], n), "…" + corto(sb[ini:], n)
    return corto(a, n), corto(b, n)


def fclave(c) -> str:
    if isinstance(c, tuple):
        return " ".join(str(x) for x in c)
    return str(c)


def pct(ok: int, tot: int) -> str:
    if not tot:
        return "sin datos"
    p = 100 * ok / tot
    return f"{p:.0f} % ({ok}/{tot})" if ok == tot else f"{p:.2f} % ({ok}/{tot})"


def rho(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3:
        return None
    if np.all(a == a[0]) or np.all(b == b[0]):
        return 1.0 if np.array_equal(a, b) else float("nan")
    return float(spearmanr(a, b)[0])


def ari(a, b):
    if len(a) < 2:
        return None
    return float(adjusted_rand_score([str(x) for x in a], [str(x) for x in b]))


def nat(s: str) -> tuple:
    """Orden natural de numerales (1.2 < 1.10; A1 al final de su nivel)."""
    s = s.split(":", 1)[-1]
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in s.split("."))


def norm_t(s: str) -> str:
    """Título sin mayúsculas, sin «…» final y sin artículos iniciales («De la», «Del»…)."""
    s = str(s).lower().rstrip("…").strip()
    while True:
        s2 = re.sub(r"^(del|de|la|las|los|el)\s+", "", s)
        if s2 == s:
            return s
        s = s2


def tipo(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    return type(v).__name__


def firma(obj, ruta: str = "$", out: set | None = None, comodin: tuple = ()) -> set:
    """Conjunto de (ruta, tipo) de todos los niveles. Las listas se resumen como `[]`;
    los dicts cuyas claves son datos (ids, códigos) se resumen como `*`."""
    if out is None:
        out = set()
    if isinstance(obj, dict):
        out.add((ruta, "dict"))
        w = ruta in comodin
        for k, v in obj.items():
            firma(v, f"{ruta}.{'*' if w else k}", out, comodin)
    elif isinstance(obj, list):
        out.add((ruta, "list"))
        for v in obj:
            firma(v, ruta + "[]", out, comodin)
    else:
        out.add((ruta, tipo(obj)))
    return out


# ---------------------------------------------------------------- sección del informe

class Seccion:
    def __init__(self, parte: str, N: int):
        self.parte, self.N = parte, N
        self.filas: list[tuple] = []          # (grupo, campo, resultado, umbral, estado)
        self.ejemplos: dict[str, list[str]] = {}
        self.extra: list[str] = []            # bloques markdown adicionales (tablas por concesión)
        self.notas: list[str] = []

    def fila(self, grupo, campo, resultado, umbral, estado):
        self.filas.append((grupo, campo, resultado, umbral, estado))

    def ej(self, campo, lineas):
        if lineas:
            self.ejemplos.setdefault(campo, []).extend(lineas[: self.N])

    def exacto(self, campo, items, eq=None, grupo="G1", umbral="100 %", estado_fijo=None):
        """items: iterable de (clave, original, clon). Cuenta coincidencias exactas."""
        ok = tot = 0
        malos = []
        for c, a, b in items:
            tot += 1
            if (eq(a, b) if eq else a == b):
                ok += 1
            elif len(malos) < self.N:
                xa, xb = par_corto(a, b)
                malos.append(f"`{fclave(c)}` — original: {xa} · clon: {xb}")
        estado = estado_fijo or (PASA if tot and ok == tot else NOPASA)
        self.fila(grupo, campo, pct(ok, tot), umbral, estado)
        self.ej(campo, malos)
        return ok, tot

    def metrica(self, campo, valor, umbral: float | None, n=None, grupo="G2", extra=""):
        if valor is None or (isinstance(valor, float) and np.isnan(valor)):
            res = "sin datos" if valor is None else "nan"
            estado = INFO if umbral is None else NOPASA
        else:
            res = f"{valor:.4f}" if abs(valor) <= 1.5 else f"{valor:.4g}"
            estado = INFO if umbral is None else (PASA if valor >= umbral - 1e-12 else NOPASA)
        if n is not None:
            res += f" (n={n})"
        if extra:
            res += f" · {extra}"
        self.fila(grupo, campo, res, "—" if umbral is None else f"≥ {umbral:g}", estado)

    def porcentaje(self, campo, ok, tot, umbral_pct: float, grupo="G2", extra=""):
        p = 100 * ok / tot if tot else None
        estado = NOPASA if p is None else (PASA if p >= umbral_pct - 1e-9 else NOPASA)
        res = pct(ok, tot) + (f" · {extra}" if extra else "")
        self.fila(grupo, campo, res, f"≥ {umbral_pct:g} %", estado)

    def info(self, campo, texto):
        self.fila("info", campo, texto, "—", INFO)

    def estructura(self, chk_clon: dict, chk_orig: dict):
        for nombre, malos in chk_clon.items():
            mo = chk_orig.get(nombre)
            ok_o = mo is not None and not mo
            if not malos:
                estado = PASA
            elif mo:  # el original tampoco lo cumple
                estado = IGUAL_ORIG
            else:
                estado = NOPASA
            res = "ok" if not malos else f"{len(malos)} caso(s)"
            res += " · original: " + ("ok" if ok_o else (f"{len(mo)} caso(s)" if mo else "—"))
            self.fila("Estructura", nombre, res, "sin casos", estado)
            if malos:
                self.ej("Estructura: " + nombre, [corto(m, 300) for m in malos])

    def firma(self, campo, fo: set, fc: set, permitidas: tuple = ()):
        solo_o = sorted(fo - fc)
        solo_c = sorted(x for x in fc - fo if not any(x[0].startswith(p) for p in permitidas))
        ok = not solo_o and not solo_c
        res = "iguales" if ok else f"{len(solo_o)} solo en original · {len(solo_c)} solo en clon"
        self.fila("Estructura", campo, res, "iguales", PASA if ok else NOPASA)
        lin = [f"solo en original: `{r}` ({t})" for r, t in solo_o[: self.N]]
        lin += [f"solo en clon: `{r}` ({t})" for r, t in solo_c[: self.N]]
        self.ej("Estructura: " + campo, lin)

    def conteo(self):
        c = Counter(f[4] for f in self.filas)
        return c[PASA], c[NOPASA], c[INFO] + c[IGUAL_ORIG]

    def markdown(self, fecha: str, ruta_clon: str, ruta_orig: str) -> str:
        p, np_, i = self.conteo()
        L = [f"<!-- seccion:{self.parte} pasa={p} nopasa={np_} fecha={fecha} -->",
             f"## {TITULOS[self.parte]}", "",
             f"Validado el {fecha} · clon: `{ruta_clon}` · original: `{ruta_orig}` · "
             f"**{p} PASA · {np_} NO PASA** · {i} informativos", ""]
        for n in self.notas:
            L += [f"> {n}", ""]
        if self.filas:
            L += ["| Grupo | Campo | Resultado | Umbral | Estado |", "|---|---|---|---|---|"]
            for g, campo, res, umb, est in self.filas:
                est_md = f"**{est}**" if est == NOPASA else est
                cel = [re.sub(r"(?<!\\)\|", r"\\|", str(x)) for x in (g, campo, res, umb)]
                L.append(f"| {' | '.join(cel)} | {est_md} |")
            L.append("")
        for bloque in self.extra:
            L += [bloque, ""]
        if self.ejemplos:
            L += [f"### Ejemplos de diferencias (hasta {self.N} por campo)", ""]
            for campo, lin in self.ejemplos.items():
                L.append(f"**{campo}**")
                L.append("")
                L += [f"- {x}" for x in lin]
                L.append("")
        L.append(f"<!-- /seccion:{self.parte} -->")
        return "\n".join(L)


def seguro(fn):
    try:
        return fn()
    except Exception as e:  # un clon mal formado no debe tumbar el validador
        return [f"error al revisar: {type(e).__name__}: {e}"]


# ================================================================ TABLERO

class Tab:
    """Vista de tablero_datos.js con índices g traducidos a claves (cod, num)."""

    def __init__(self, T: dict):
        self.T = T
        self.conc = T.get("conc", [])
        self.cods = [c.get("cod") for c in self.conc]
        self.A = T.get("arts", {})
        self.N = len(self.A.get("c", []))
        self.clave = []
        for g in range(self.N):
            c = self.A["c"][g]
            cod = self.cods[c] if isinstance(c, int) and 0 <= c < len(self.cods) else f"?{c}"
            num = self.A.get("num", [None] * self.N)[g]
            self.clave.append((cod, num))
        self.pos = {}
        self.dup = []
        for g, k in enumerate(self.clave):
            if k in self.pos:
                self.dup.append(k)
            else:
                self.pos[k] = g

    def tr(self, g):
        return self.clave[g] if isinstance(g, int) and 0 <= g < self.N else ("?", f"g={g}")

    def v(self, campo, g, defecto=None):
        L = self.A.get(campo)
        return L[g] if L is not None and g < len(L) else defecto


def chequeos_tab(T: dict) -> dict:
    t = Tab(T)
    A, N, out = t.A, t.N, {}

    def reg(nombre, fn):
        out[nombre] = seguro(fn)

    reg("conc en orden CN, LOA, RITP, AVO, PCNP-2",
        lambda: [] if t.cods == comun.ORDEN else [f"orden: {t.cods}"])

    def f_actos():
        m = []
        for c in t.conc:
            ac = c["actos"]
            if not ac or ac[0][2] != "bases licitacion":
                m.append(f"{c['cod']}: el primer acto no es Bases: {ac[:1]}")
            f = [a[1] for a in ac]
            if f != sorted(f):
                m.append(f"{c['cod']}: actos no ordenados por fecha")
            if not (0 <= c["adj"] < len(ac)) or ac[c["adj"]][2] != "decreto adjudicacion":
                m.append(f"{c['cod']}: adj={c['adj']} no es un decreto adjudicacion")
            for a in ac:
                if len(a) != 3 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(a[1])):
                    m.append(f"{c['cod']}: acto mal formado {a}")
        return m
    reg("conc.actos: bases primero, orden por fecha, adj coherente", f_actos)

    reg("arts: 22 listas paralelas del mismo largo",
        lambda: [f"{k}: {len(v)} ≠ {N}" for k, v in A.items() if len(v) != N])
    reg("arts.id = 'BL:' + num",
        lambda: [f"g={g}: {A['id'][g]} / {A['num'][g]}" for g in range(N) if A["id"][g] != "BL:" + A["num"][g]])
    reg("claves (cod, num) únicas", lambda: [str(k) for k in t.dup])

    def f_orden():
        m = []
        for g in range(1, N):
            a, b = (A["c"][g - 1], nat(A["num"][g - 1])), (A["c"][g], nat(A["num"][g]))
            if a > b:
                m.append(f"g={g}: {t.clave[g - 1]} antes de {t.clave[g]}")
        return m
    reg("filas ordenadas por c y por número", f_orden)

    def f_sale():
        m = []
        for g in range(N):
            s, w = A["sale"][g], A["sw"][g]
            if s != sorted(set(s)):
                m.append(f"{t.clave[g]}: sale no ascendente/único {s}")
            if g in s:
                m.append(f"{t.clave[g]}: autocita")
            if any(A["c"][h] != A["c"][g] for h in s if 0 <= h < N):
                m.append(f"{t.clave[g]}: cita fuera de su concesión")
            if any(not (0 <= h < N) for h in s):
                m.append(f"{t.clave[g]}: índice fuera de rango")
            if len(w) != len(s):
                m.append(f"{t.clave[g]}: len(sw)={len(w)} ≠ len(sale)={len(s)}")
            if any((not isinstance(x, int)) or x < 1 for x in w):
                m.append(f"{t.clave[g]}: sw no positivo {w}")
        return m
    reg("sale ascendente, sin autocitas, misma concesión; sw paralela", f_sale)

    def f_entra():
        inv = defaultdict(list)
        for g in range(N):
            for h in A["sale"][g]:
                inv[h].append(g)
        return [f"{t.clave[g]}: entra={A['entra'][g]} · inversa={sorted(inv[g])}"
                for g in range(N) if sorted(A["entra"][g]) != sorted(inv[g])]
    reg("entra = inversa exacta de sale", f_entra)

    reg("nueva ⊆ sale", lambda: [f"{t.clave[g]}: {A['nueva'][g]}" for g in range(N)
                                 if not set(A["nueva"][g]) <= set(A["sale"][g])])

    def f_ci():
        s = Counter()
        for g in range(N):
            for h, w in zip(A["sale"][g], A["sw"][g]):
                s[h] += w
        return [f"{t.clave[g]}: ci={A['ci'][g]} · Σsw={s[g]}" for g in range(N) if A["ci"][g] != s[g]]
    reg("ci = suma de sw entrantes", f_ci)

    def f_cs():
        m = []
        for g in range(N):
            cs = A["cs"][g]
            if len(cs) > 6:
                m.append(f"{t.clave[g]}: {len(cs)} > 6")
            ns = [n for _, n in cs]
            if ns != sorted(ns, reverse=True):
                m.append(f"{t.clave[g]}: cs no ordenado por n desc {cs}")
        return m
    reg("cs ≤ 6 y ordenado por n descendente", f_cs)

    def f_ca():
        m = []
        for g in range(N):
            na = len(t.conc[A["c"][g]]["actos"])
            ks = [k for k, _ in A["ca"][g]]
            if ks != sorted(set(ks)) or any(not (1 <= k < na) for k in ks):
                m.append(f"{t.clave[g]}: ca {A['ca'][g]}")
        return m
    reg("ca ordenado por k, 1 ≤ k < nº actos", f_ca)

    def f_h():
        m = []
        for g in range(N):
            na = len(t.conc[A["c"][g]]["actos"])
            ks = [k for k, _ in A["h"][g]]
            if ks != sorted(set(ks)) or any(not (0 <= k < na) for k in ks):
                m.append(f"{t.clave[g]}: k de h {ks}")
            for k, eds in A["h"][g]:
                for e in eds:
                    if len(e) != 3 or e[0] not in TIPOS_H or len(e[2]) > 220:
                        m.append(f"{t.clave[g]} k={k}: edición {corto(e, 120)}")
        return m
    reg("h ordenado por k; tipo conocido; texto ≤ 220", f_h)

    reg("sub son sub-números del artículo",
        lambda: [f"{t.clave[g]}: {A['sub'][g]}" for g in range(N)
                 if any(not s.startswith(A["num"][g] + ".") for s in A["sub"][g])])

    def f_pr():
        m = []
        for ci, cod in enumerate(t.cods):
            s = sum(A["pr"][g] for g in range(N) if A["c"][g] == ci)
            s0 = sum(A["pr0"][g] for g in range(N) if A["c"][g] == ci)
            if abs(s - 1) > 1e-3:
                m.append(f"{cod}: Σpr = {s:.6f}")
            if abs(s0 - 1) > 1e-3:
                m.append(f"{cod}: Σpr0 = {s0:.6f}")
        m += [f"{t.clave[g]}: nuevo y pr0={A['pr0'][g]}" for g in range(N)
              if A["nuevo"][g] and A["pr0"][g] != 0]
        m += [f"{t.clave[g]}: nuevo={A['nuevo'][g]}" for g in range(N) if A["nuevo"][g] not in (0, 1)]
        return m
    reg("pr y pr0 suman 1 por concesión (±1e-3); pr0 = 0 si nuevo", f_pr)

    def f_ct():
        m = []
        for g in range(N):
            ct = A["ct"][g]
            cs_ = [A["c"][h] for h, _ in ct if 0 <= h < N]
            if (len(ct) > 4 or len(cs_) != len(ct) or cs_ != sorted(set(cs_)) or A["c"][g] in cs_
                    or any(f < 0.5 for _, f in ct)):
                m.append(f"{t.clave[g]}: ct {ct}")
        return m
    reg("ct ≤ 4, uno por otra concesión, ordenado, φ ≥ 0,5", f_ct)

    def f_xy():
        mx = max(max(map(abs, A["x"])), max(map(abs, A["y"])))
        return [] if abs(mx - 1) <= 1e-3 else [f"máx |coord| = {mx}"]
    reg("x, y con máx |coord| = 1", f_xy)

    B = T.get("bases", {})

    def f_bases():
        m = []
        nb = len(B["m"])
        m += [f"bases.{k}: {len(v)} ≠ {nb}" for k, v in B.items() if len(v) != nb]
        vistos = Counter(h for mm in B["m"] for h in mm)
        m += [f"{t.tr(h)} aparece {n} veces" for h, n in vistos.items() if n > 1]
        m += [f"{t.clave[g]} no está en ninguna base" for g in range(N) if g not in vistos]
        # el original las ordena por tamaño descendente y luego por el g de su primer miembro
        orden = [(-len(mm), mm[0]) for mm in B["m"] if mm]
        if orden != sorted(orden):
            m.append("bases no ordenadas por (tamaño desc., g del primer miembro)")
        for i, mm in enumerate(B["m"]):
            cs_ = [A["c"][h] for h in mm]
            if cs_ != sorted(set(cs_)):
                m.append(f"base {i}: miembros no ordenados / repiten concesión {[t.tr(h) for h in mm]}")
            if abs(np.mean([A["x"][h] for h in mm]) - B["x"][i]) > 1e-3 or \
                    abs(np.mean([A["y"][h] for h in mm]) - B["y"][i]) > 1e-3:
                m.append(f"base {i}: x/y no es el promedio de sus miembros")
            tit = Counter(norm_t(A["t"][h]) for h in mm)
            if tit.get(norm_t(B["t"][i]), 0) != max(tit.values()):
                m.append(f"base {i}: t='{B['t'][i]}' no es el título más frecuente")
        for g in range(N):
            b = A["base"][g]
            if not (0 <= b < nb) or g not in B["m"][b]:
                m.append(f"{t.clave[g]}: base={b} no lo contiene")
        return m
    reg("bases: paralelas, cada g una vez, ≤1 por concesión, orden, base[g] coherente, x/y, t (normalizado)", f_bases)

    def f_cm():
        C = T["comunidades"]
        m = [f"{t.clave[g]}: cm={A['cm'][g]}" for g in range(N) if not (0 <= A["cm"][g] < len(C))]
        cnt = Counter(A["cm"])
        for i, co in enumerate(C):
            if co["n"] != cnt[i]:
                m.append(f"comunidad {i} '{co['t']}': n={co['n']} · cuenta={cnt[i]}")
            nc = len({A["c"][g] for g in range(N) if A["cm"][g] == i})
            if co["conc"] != nc:
                m.append(f"comunidad {i} '{co['t']}': conc={co['conc']} · real={nc}")
            if not (2 <= len(co["ej"]) <= 4):
                m.append(f"comunidad {i}: {len(co['ej'])} ejemplos")
        return m
    reg("comunidades: n y conc coherentes con cm; 2–4 ejemplos", f_cm)
    return out


def validar_tablero(To: dict, Tc: dict, S: Seccion):
    o, c = Tab(To), Tab(Tc)

    # --- estructura
    S.firma("claves y tipos en todos los niveles", firma(To), firma(Tc))
    S.estructura(chequeos_tab(Tc), chequeos_tab(To))

    # --- conc
    co = {x["cod"]: x for x in o.conc}
    cc = {x["cod"]: x for x in c.conc}
    S.exacto("conc: concesiones presentes", [(cod, cod in co, cod in cc) for cod in comun.ORDEN])
    comunes_c = [cod for cod in comun.ORDEN if cod in co and cod in cc]
    for campo in ("nombre", "largo", "color", "adj"):
        S.exacto(f"conc.{campo}", [(cod, co[cod].get(campo), cc[cod].get(campo)) for cod in comunes_c])
    S.exacto("conc.actos (lista completa)", [(cod, co[cod].get("actos"), cc[cod].get("actos"))
                                            for cod in comunes_c])
    items = []
    for cod in comunes_c:
        ao, ac = co[cod].get("actos", []), cc[cod].get("actos", [])
        for i in range(max(len(ao), len(ac))):
            items.append(((cod, f"acto {i}"), ao[i] if i < len(ao) else None, ac[i] if i < len(ac) else None))
    S.exacto("conc.actos (elemento a elemento)", items)
    S.info("generado", f"original {To.get('generado')} · clon {Tc.get('generado')}")

    # --- conjunto de artículos
    ko, kc = set(o.pos), set(c.pos)
    comunes = [k for k in o.clave if k in kc]
    tabla = ["| Concesión | Original | Clon | Comunes | Faltan en el clon | Sobran en el clon |",
             "|---|---|---|---|---|---|"]
    for cod in comun.ORDEN:
        a = {k for k in ko if k[0] == cod}
        b = {k for k in kc if k[0] == cod}
        falt = sorted(a - b, key=lambda k: nat(k[1] or ""))
        sobr = sorted(b - a, key=lambda k: nat(k[1] or ""))
        fl = ", ".join(k[1] for k in falt[: S.N]) + (" …" if len(falt) > S.N else "")
        sl = ", ".join(k[1] for k in sobr[: S.N]) + (" …" if len(sobr) > S.N else "")
        tabla.append(f"| {cod} | {len(a)} | {len(b)} | {len(a & b)} | {len(falt)}{': ' + fl if falt else ''} "
                     f"| {len(sobr)}{': ' + sl if sobr else ''} |")
    S.extra.append("**Artículos por concesión** (emparejados por (cod, num))\n\n" + "\n".join(tabla))
    S.fila("G1", "artículos (cod, num): comunes / unión", pct(len(ko & kc), len(ko | kc)), "100 %",
           PASA if ko == kc else NOPASA)

    def campo_items(campo, fn):
        return [(k, fn(o, o.pos[k], campo), fn(c, c.pos[k], campo)) for k in comunes]

    crudo = lambda t, g, campo: t.v(campo, g)  # noqa: E731
    lista_g = lambda t, g, campo: sorted(t.tr(h) for h in (t.v(campo, g) or []))  # noqa: E731

    def sw_dict(t, g, _):
        return {fclave(t.tr(h)): w for h, w in zip(t.v("sale", g) or [], t.v("sw", g) or [])}

    for campo in ("t", "parte", "sub", "nuevo"):
        S.exacto(f"arts.{campo}", campo_items(campo, crudo))
    for campo in ("sale", "entra", "nueva"):
        S.exacto(f"arts.{campo} (como (cod, num))", campo_items(campo, lista_g))
    S.exacto("arts.sw (destino → peso)", campo_items("sw", sw_dict))
    S.exacto("arts.ci", campo_items("ci", crudo))
    cs_items = campo_items("cs", crudo)
    S.exacto("arts.cs", cs_items)
    S.exacto("arts.cs (sin orden de empates)", cs_items,
             eq=lambda a, b: sorted(map(tuple, a or [])) == sorted(map(tuple, b or [])), grupo="info",
             umbral="—", estado_fijo=INFO)
    S.exacto("arts.ca", campo_items("ca", crudo))

    # --- h
    hdict = lambda t, g, _: {k: e for k, e in (t.v("h", g) or [])}  # noqa: E731
    h_items = campo_items("h", hdict)
    S.exacto("arts.h (exacto: acto → ediciones)", h_items)
    S.exacto("arts.h: conjunto de actos k", [(k, sorted(a), sorted(b)) for k, a, b in h_items])
    n_items, cmp = [], {"tipo": [], "inciso": [], "texto": []}
    for k, ho, hc in h_items:
        for acto in sorted(set(ho) & set(hc)):
            lo, lc = ho[acto], hc[acto]
            n_items.append(((*k, f"k={acto}"), len(lo), len(lc)))
            for i, (eo, ec) in enumerate(zip(lo, lc)):
                for j, nom in enumerate(("tipo", "inciso", "texto")):
                    cmp[nom].append(((*k, f"k={acto}", f"#{i}"), eo[j] if j < len(eo) else None,
                                     ec[j] if j < len(ec) else None))
    S.exacto("arts.h: nº de ediciones por (artículo, k)", n_items)
    for nom in ("tipo", "inciso", "texto"):
        S.exacto(f"arts.h: {nom} (ediciones alineadas)", cmp[nom])

    # --- pr, pr0
    for campo in ("pr", "pr0"):
        it = campo_items(campo, crudo)
        par = [(k, a, b) for k, a, b in it if isinstance(a, (int, float)) and isinstance(b, (int, float))]
        S.exacto(f"arts.{campo} (tolerancia 1e-4)", it,
                 eq=lambda a, b: isinstance(a, (int, float)) and isinstance(b, (int, float))
                 and abs(a - b) <= TOL_PR + 1e-12, umbral="100 %")
        if par:
            dmax = max(abs(a - b) for _, a, b in par)
            r = rho([a for _, a, _ in par], [b for _, _, b in par])
            S.info(f"arts.{campo}: dif. máx. · Spearman", f"{dmax:.2e} · ρ = {r:.4f}" if r is not None else f"{dmax:.2e}")

    # --- Grupo 2: ct
    def pares_ct(t):
        P = {}
        for g in range(t.N):
            for h, f in (t.v("ct", g) or []):
                P[(t.clave[g], t.tr(h))] = f
        return P
    Po, Pc = pares_ct(o), pares_ct(c)
    # solo pares cuyo artículo origen está en ambos lados (los que faltan ya se informan arriba)
    Po_ = {p: f for p, f in Po.items() if p[0] in kc}
    Pc_ = {p: f for p, f in Pc.items() if p[0] in ko}
    com = sorted(set(Po_) & set(Pc_))
    uni = set(Po_) | set(Pc_)
    S.porcentaje("ct: coincidencia de pares (Jaccard)", len(com), len(uni), 85,
                 extra=f"recall {100 * len(com) / max(1, len(Po_)):.1f} % · precisión "
                       f"{100 * len(com) / max(1, len(Pc_)):.1f} %")
    S.metrica("ct: Spearman de φ en pares comunes", rho([Po_[p] for p in com], [Pc_[p] for p in com]),
              0.8, len(com))
    S.ej("ct: coincidencia de pares (Jaccard)",
         [f"solo original: `{fclave(a)}` → `{fclave(b)}` φ={Po_[(a, b)]}" for a, b in sorted(set(Po_) - set(Pc_))[: S.N]]
         + [f"solo clon: `{fclave(a)}` → `{fclave(b)}` φ={Pc_[(a, b)]}" for a, b in sorted(set(Pc_) - set(Po_))[: S.N]])

    # --- bases y comunidades
    lab_o = [o.v("base", o.pos[k]) for k in comunes]
    lab_c = [c.v("base", c.pos[k]) for k in comunes]
    S.metrica("bases: ARI (etiqueta = índice de base)", ari(lab_o, lab_c), 0.8, len(comunes))

    def conj_bases(t):
        B = t.T.get("bases", {})
        return {frozenset(t.tr(h) for h in mm): (B.get("t") or [None] * len(B["m"]))[i]
                for i, mm in enumerate(B.get("m", []))}
    Bo, Bc = conj_bases(o), conj_bases(c)
    iguales = set(Bo) & set(Bc)
    S.info("bases idénticas (mismos miembros)",
           f"{pct(len(iguales), len(Bo))} · bases: original {len(Bo)}, clon {len(Bc)} · "
           f"t igual en {sum(Bo[b] == Bc[b] for b in iguales)}/{len(iguales)}")
    tam = lambda B: dict(sorted(Counter(len(b) for b in B).items()))  # noqa: E731
    S.info("bases: tamaños", f"original {tam(Bo)} · clon {tam(Bc)}")
    S.ej("bases: ARI (etiqueta = índice de base)",
         [f"base solo en original: {sorted(fclave(x) for x in b)}" for b in list(set(Bo) - set(Bc))[: S.N]])
    S.metrica("cm: ARI de comunidades", ari([o.v("cm", o.pos[k]) for k in comunes],
                                            [c.v("cm", c.pos[k]) for k in comunes]), 0.6, len(comunes))
    nom = lambda T: ", ".join(f"{x.get('t')} ({x.get('n')})" for x in T.get("comunidades", []))  # noqa: E731
    S.info("comunidades", f"original: {nom(To)} · clon: {nom(Tc)}")

    # --- x/y: correlación de distancias por pares (informativo)
    if len(comunes) > 3:
        Xo = np.array([[o.v("x", o.pos[k]), o.v("y", o.pos[k])] for k in comunes], float)
        Xc = np.array([[c.v("x", c.pos[k]), c.v("y", c.pos[k])] for k in comunes], float)
        do, dc = pdist(Xo), pdist(Xc)
        r = float(pearsonr(do, dc)[0]) if do.std() and dc.std() else (1.0 if np.allclose(do, dc) else float("nan"))
        S.metrica("x/y: correlación de distancias por pares (Pearson)", r, None, len(comunes), grupo="info")


# ================================================================ ANTES/DESPUÉS

def chequeos_ad(D: dict) -> dict:
    out = {}

    def reg(nombre, fn):
        out[nombre] = seguro(fn)

    C = D.get("concesiones", {})
    reg("k = 8 y concesiones = las 5",
        lambda: ([] if D.get("k") == 8 else [f"k={D.get('k')}"])
        + ([] if set(C) == set(comun.ORDEN) else [f"concesiones: {sorted(C)}"]))

    def f_claves():
        m = []
        for cod, cc in C.items():
            ks = list(cc["arts"])
            if any(not k.startswith("BL:") for k in ks):
                m.append(f"{cod}: claves sin 'BL:'")
            if ks != sorted(ks, key=nat):
                m.append(f"{cod}: claves no van en orden natural")
            if len(ks) > cc["n"]:
                m.append(f"{cod}: {len(ks)} entradas > n={cc['n']}")
        return m
    reg("claves 'BL:' en orden natural; entradas ≤ n", f_claves)

    def f_art():
        m = []
        for cod, cc in C.items():
            for k, a in cc["arts"].items():
                nv = a.get("nuevo", 0)
                if (a["phi"] is None) != bool(nv):
                    m.append(f"{cod} {k}: phi={a['phi']} con nuevo={nv}")
                if nv and a["v0"]:
                    m.append(f"{cod} {k}: nuevo con v0 no vacío")
                for vv in ("v0", "v1"):
                    L = a[vv]
                    if len(L) > 8 or any(i == k for i, _ in L) or [x for _, x in L] != sorted([x for _, x in L], reverse=True):
                        m.append(f"{cod} {k}: {vv} mal formado ({len(L)} elementos)")
                if len(a["w"]) != 2 or len(a["inc"]) != 2:
                    m.append(f"{cod} {k}: w/inc no tienen 2 valores")
                for s in a["d"]:
                    if s[0] not in (-1, 0, 1) or len(s) not in (2, 3) or (len(s) == 3 and len(s[1].split()) > 120):
                        m.append(f"{cod} {k}: segmento de d mal formado {corto(s, 80)}")
                        break
                for f in ("nuevo", "dudoso"):
                    if f in a and a[f] != 1:
                        m.append(f"{cod} {k}: {f}={a[f]} (solo debe aparecer si vale 1)")
        return m
    reg("phi null ⇔ nuevo; v0 = [] si nuevo; v0/v1 ≤ 8 sin sí mismo; d, w, inc bien formados", f_art)
    return out


def tokens_d(d):
    return [(s[0], w) for s in (d or []) for w in str(s[1]).split()]


def validar_ad(Do: dict, Dc: dict, S: Seccion):
    S.firma("claves y tipos en todos los niveles",
            firma(Do, comodin=("$.concesiones", "$.concesiones.*.arts")),
            firma(Dc, comodin=("$.concesiones", "$.concesiones.*.arts")))
    S.estructura(chequeos_ad(Dc), chequeos_ad(Do))
    Co, Cc = Do.get("concesiones", {}), Dc.get("concesiones", {})
    S.exacto("k", [("k", Do.get("k"), Dc.get("k"))])
    S.exacto("concesiones presentes", [(cod, cod in Co, cod in Cc) for cod in comun.ORDEN])
    cods = [cod for cod in comun.ORDEN if cod in Co and cod in Cc]
    S.exacto("n por concesión", [(cod, Co[cod].get("n"), Cc[cod].get("n")) for cod in cods])
    S.info("generado", f"original {Do.get('generado')} · clon {Dc.get('generado')}")

    tabla = ["| Concesión | n orig. | n clon | Entradas orig. | Entradas clon | Comunes | Faltan en el clon | Sobran en el clon |",
             "|---|---|---|---|---|---|---|---|"]
    comunes, tot_o, tot_u = [], 0, 0
    for cod in comun.ORDEN:
        ao = Co.get(cod, {}).get("arts", {})
        ac = Cc.get(cod, {}).get("arts", {})
        a, b = set(ao), set(ac)
        tot_o += len(a & b)
        tot_u += len(a | b)
        comunes += [(cod, k) for k in ao if k in b]
        falt = sorted(a - b, key=nat)
        sobr = sorted(b - a, key=nat)
        fl = ", ".join(falt[: S.N]) + (" …" if len(falt) > S.N else "")
        sl = ", ".join(sobr[: S.N]) + (" …" if len(sobr) > S.N else "")
        tabla.append(f"| {cod} | {Co.get(cod, {}).get('n')} | {Cc.get(cod, {}).get('n')} | {len(a)} | {len(b)} "
                     f"| {len(a & b)} | {len(falt)}{': ' + fl if falt else ''} | {len(sobr)}{': ' + sl if sobr else ''} |")
    S.extra.append("**Entradas por concesión** (emparejadas por (cod, id BL:))\n\n" + "\n".join(tabla))
    S.fila("G1", "claves (cod, id): comunes / unión", pct(tot_o, tot_u), "100 %", PASA if tot_o == tot_u else NOPASA)

    ao = lambda cod, k: Co[cod]["arts"][k]  # noqa: E731
    ac = lambda cod, k: Cc[cod]["arts"][k]  # noqa: E731
    for campo in ("w", "inc", "cs", "ce", "d"):
        S.exacto(campo, [((cod, k), ao(cod, k).get(campo), ac(cod, k).get(campo)) for cod, k in comunes])
    for campo in ("nuevo", "dudoso"):
        S.exacto(campo, [((cod, k), ao(cod, k).get(campo, 0), ac(cod, k).get(campo, 0)) for cod, k in comunes])
    for campo in ("cs", "ce"):
        S.exacto(f"{campo} (como conjunto)",
                 [((cod, k), ao(cod, k).get(campo), ac(cod, k).get(campo)) for cod, k in comunes],
                 eq=lambda a, b: sorted(map(tuple, a or [])) == sorted(map(tuple, b or [])),
                 grupo="info", umbral="—", estado_fijo=INFO)
    # similitud del diff (diagnóstico)
    rat = []
    for cod, k in comunes:
        a, b = ao(cod, k).get("d"), ac(cod, k).get("d")
        if a != b:
            rat.append(difflib.SequenceMatcher(None, tokens_d(a), tokens_d(b), autojunk=False).ratio())
    if rat:
        S.info("d: similitud por palabras de los diffs distintos",
               f"media {np.mean(rat):.3f} · mín {min(rat):.3f} (n={len(rat)})")

    # --- Grupo 2
    ph = [(ao(cod, k).get("phi"), ac(cod, k).get("phi")) for cod, k in comunes]
    ph = [(a, b) for a, b in ph if a is not None and b is not None]
    S.metrica("phi: Spearman", rho([a for a, _ in ph], [b for _, b in ph]) if ph else None, 0.8, len(ph))
    if ph:
        S.info("phi: |Δ| ≤ 0,01", pct(sum(abs(a - b) <= 0.01 + 1e-9 for a, b in ph), len(ph)))
    S.exacto("phi null (unidad nueva)", [((cod, k), ao(cod, k).get("phi") is None, ac(cod, k).get("phi") is None)
                                         for cod, k in comunes])
    for vv in ("v0", "v1"):
        sol, malos = [], []
        for cod, k in comunes:
            a = {i for i, _ in ao(cod, k).get(vv) or []}
            b = {i for i, _ in ac(cod, k).get(vv) or []}
            if not a and not b:
                continue
            s = len(a & b) / max(len(a), len(b))
            sol.append(s)
            if s < 1 and len(malos) < S.N:
                malos.append(f"`{cod} {k}` solape {s:.2f} — solo original: {sorted(a - b)} · solo clon: {sorted(b - a)}")
        m = 100 * float(np.mean(sol)) if sol else None
        S.fila("G2", f"{vv}: solape medio del top-8", f"{m:.1f} % (n={len(sol)})" if sol else "sin datos",
               "≥ 60 %", PASA if m is not None and m >= 60 else NOPASA)
        S.ej(f"{vv}: solape medio del top-8", malos)


# ================================================================ MATRIZ

def chequeos_matriz(M: dict) -> dict:
    out = {}

    def reg(nombre, fn):
        out[nombre] = seguro(fn)

    arts = M.get("arts", [])
    n = len(arts)
    reg("largos: arts = hoja_a_fila = n; Z = n−1 filas de 3; S = n²",
        lambda: [x for x in [
            f"hoja_a_fila {len(M['hoja_a_fila'])} ≠ {n}" if len(M["hoja_a_fila"]) != n else "",
            f"Z {len(M['Z'])} ≠ {n - 1}" if len(M["Z"]) != n - 1 else "",
            "Z con filas ≠ 3" if any(len(z) != 3 for z in M["Z"]) else "",
            f"S {len(M['S'])} ≠ {n * n}" if len(M["S"]) != n * n else ""] if x])
    reg("hoja_a_fila es una permutación", lambda: [] if sorted(M["hoja_a_fila"]) == list(range(n)) else ["no"])
    reg("unidades `a` únicas", lambda: [f"{a} ×{k}" for a, k in Counter(x["a"] for x in arts).items() if k > 1])

    def f_S():
        S = np.asarray(M["S"]).reshape(n, n)
        m = []
        if not np.array_equal(S, S.T):
            i, j = np.argwhere(S != S.T)[0]
            m.append(f"S no simétrica (p. ej. [{i},{j}]={S[i, j]} vs {S[j, i]})")
        if not np.all(np.diag(S) == 1000):
            m.append(f"diagonal ≠ 1000 en {int(np.sum(np.diag(S) != 1000))} filas")
        if S.dtype.kind != "i":
            m.append("S no es entera")
        return m
    reg("S simétrica, entera, diagonal 1000", f_S)
    reg("x ≤ 420 caracteres; p conocido",
        lambda: [f"{x['a']}: {len(x['x'])} car." for x in arts if len(x["x"]) > 420]
        + [f"{x['a']}: p={x['p']}" for x in arts if x["p"] not in ("Administrativas", "Técnicas", "Económicas", "Anexos")])

    def f_cortes():
        m = []
        C = M["cortes"]
        if set(C) != {str(k) for k in range(4, 17)}:
            m.append(f"claves de cortes: {sorted(C, key=int)}")
        Z = M["Z"]
        for K, cc in C.items():
            K_ = int(K)
            lab = cc["lab"]
            if len(lab) != n:
                m.append(f"K={K}: lab tiene {len(lab)}")
            if len(set(lab)) != K_:
                m.append(f"K={K}: {len(set(lab))} grupos")
            cambios = sum(1 for i in range(1, len(lab)) if lab[i] != lab[i - 1])
            if cambios != len(set(lab)) - 1:
                m.append(f"K={K}: grupos no contiguos")
            if len(cc["kw"]) != K_ or any(len(k) != 6 for k in cc["kw"]):
                m.append(f"K={K}: kw no tiene 6 términos por grupo")
            if len(cc["rep"]) != K_ or any(len(r) > 3 for r in cc["rep"]):
                m.append(f"K={K}: rep mal formado")
            if len(cc["coh"]) != K_:
                m.append(f"K={K}: coh tiene {len(cc['coh'])}")
            esperado = (Z[-K_][2] + Z[-K_ + 1][2]) / 2
            if abs(cc["corte"] - esperado) > 1e-3:
                m.append(f"K={K}: corte {cc['corte']} ≠ punto medio {esperado:.4f}")
        return m
    reg("cortes 4–16: lab contiguo con K grupos; kw 6; rep ≤ 3; coh; corte = punto medio", f_cortes)
    return out


def validar_matriz(Mo: dict, Mc: dict, S: Seccion):
    S.firma("claves y tipos en todos los niveles", firma(Mo, comodin=("$.cortes",)),
            firma(Mc, comodin=("$.cortes",)), permitidas=("$.cortes.*.nombre",))
    S.estructura(chequeos_matriz(Mc), chequeos_matriz(Mo))
    S.exacto("concesion", [("concesion", Mo.get("concesion"), Mc.get("concesion"))])
    S.info("modelo (modo de vectores)", f"original {Mo.get('modelo')} · clon {Mc.get('modelo')}")
    S.info("cortes.*.nombre (agregado por el clon)",
           "presente" if all("nombre" in v for v in Mc.get("cortes", {}).values()) and Mc.get("cortes") else "ausente")

    ao = {x["a"]: (i, x) for i, x in enumerate(Mo.get("arts", []))}
    ac = {x["a"]: (i, x) for i, x in enumerate(Mc.get("arts", []))}
    comunes = [a for a in ao if a in ac]
    falt = sorted(set(ao) - set(ac), key=nat)
    sobr = sorted(set(ac) - set(ao), key=nat)
    S.fila("G1", "unidades `a`: comunes / unión", pct(len(comunes), len(set(ao) | set(ac))), "100 %",
           PASA if not falt and not sobr else NOPASA)
    S.ej("unidades `a`: comunes / unión", [f"falta en el clon: `{a}` — {corto(ao[a][1].get('t'), 80)}" for a in falt[: S.N]]
         + [f"sobra en el clon: `{a}` — {corto(ac[a][1].get('t'), 80)}" for a in sobr[: S.N]])
    S.extra.append(f"**Unidades:** original {len(ao)} · clon {len(ac)} · comunes {len(comunes)} · "
                   f"faltan {len(falt)} · sobran {len(sobr)}")
    for campo in ("t", "p", "f", "x"):
        S.exacto(campo, [(a, ao[a][1].get(campo), ac[a][1].get(campo)) for a in comunes])

    # --- Grupo 2
    no, nc = len(ao), len(ac)
    try:
        So = np.asarray(Mo["S"]).reshape(no, no)
        Sc = np.asarray(Mc["S"]).reshape(nc, nc)
        io = np.array([ao[a][0] for a in comunes])
        ic = np.array([ac[a][0] for a in comunes])
        iu, ju = np.triu_indices(len(comunes), 1)
        vo, vc = So[io[iu], io[ju]], Sc[ic[iu], ic[ju]]
        S.metrica("S: Spearman en pares de unidades comunes", rho(vo, vc), 0.8, len(vo),
                  extra=f"|Δ| medio {np.mean(np.abs(vo - vc)):.1f}")
    except Exception as e:
        S.metrica("S: Spearman en pares de unidades comunes", None, 0.8, extra=f"error: {e}")
    for K in [str(k) for k in range(4, 17)]:
        try:
            lo = Mo["cortes"][K]["lab"]
            lc = Mc["cortes"][K]["lab"]
            r = ari([lo[ao[a][0]] for a in comunes], [lc[ac[a][0]] for a in comunes])
        except Exception:
            r = None
        if K == "12":
            S.metrica('cortes["12"].lab: ARI', r, 0.6, len(comunes))
        else:
            S.metrica(f'cortes["{K}"].lab: ARI', r, None, len(comunes), grupo="info")
    S.metrica("orden de hojas: Spearman de la posición", rho([ao[a][0] for a in comunes], [ac[a][0] for a in comunes]),
              None, len(comunes), grupo="info")


# ================================================================ informe

def leer(ruta: Path):
    if not ruta.exists():
        return None, f"no existe `{ruta}`"
    try:
        return comun.leer_js(ruta), None
    except Exception as e:
        return None, f"no se pudo leer `{ruta}`: {type(e).__name__}: {e}"


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(comun.RAIZ)).replace("\\", "/")
    except ValueError:
        return str(p)


def correr(parte: str, orig_dir: Path, clon_dir: Path, N: int, fecha: str) -> Seccion:
    S = Seccion(parte, N)
    fo, fc = orig_dir / ARCHIVOS[parte], clon_dir / ARCHIVOS[parte]
    O, err_o = leer(fo)
    C, err_c = leer(fc)
    if err_o:
        S.notas.append(f"Original: {err_o}.")
        S.fila("—", "archivo original", "no disponible", "—", NOPASA)
        return S
    if err_c:
        S.notas.append(f"Clon: {err_c}. Se omite esta parte.")
        S.fila("—", "archivo del clon", "no existe" if "no existe" in err_c else "ilegible", "—", NOPASA)
        return S
    fn = {"tablero": validar_tablero, "ad": validar_ad, "matriz": validar_matriz}[parte]
    try:
        fn(O, C, S)
    except Exception as e:  # informe parcial antes que un traceback
        import traceback
        S.notas.append(f"La validación se interrumpió: {type(e).__name__}: {e}")
        S.fila("—", "validación", "interrumpida", "—", NOPASA)
        traceback.print_exc()
    return S


def modelo_vectores(clon_dir: Path, orig_dir: Path) -> str:
    M, err = leer(clon_dir / ARCHIVOS["matriz"])
    Mo, _ = leer(orig_dir / ARCHIVOS["matriz"])
    mo = Mo.get("modelo") if Mo else "?"
    if M is None:
        return f"clon: desconocido (no existe la matriz del clon) · original: {mo}"
    return f"clon: {M.get('modelo', 'sin campo modelo')} · original: {mo}"


RE_SEC = re.compile(r"<!-- seccion:(\w+) pasa=(\d+) nopasa=(\d+) fecha=([^>]*?) -->.*?<!-- /seccion:\1 -->", re.S)


def escribir_informe(salida: Path, secciones: dict[str, str], cabecera: dict):
    previas = {}
    if salida.exists():
        for m in RE_SEC.finditer(salida.read_text(encoding="utf-8")):
            previas[m.group(1)] = m.group(0)
    previas.update(secciones)
    filas = []
    for p in PARTES:
        if p in previas:
            m = RE_SEC.search(previas[p])
            pa, npa, f = int(m.group(2)), int(m.group(3)), m.group(4)
            filas.append(f"| {TITULOS[p]} | {f} | {pa} | {npa} | {'PASA' if npa == 0 else '**NO PASA**'} |")
        else:
            filas.append(f"| {TITULOS[p]} | — | — | — | sin validar |")
    L = ["# Validación del clon", "",
         f"Última ejecución: {cabecera['fecha']} · partes: {cabecera['partes']} · clon: `{cabecera['clon']}` · "
         f"original: `{cabecera['orig']}`", "",
         f"Modo de vectores: {cabecera['modelo']}", "",
         "Emparejamiento siempre por clave: artículos del tablero por (cod, num), con los índices g traducidos a "
         "(cod, num); antes/después por (cod, id BL:); matriz por `a`. **G1** = determinista, debe calzar exacto; "
         "**G2** = similitud con umbral; **Estructura** = chequeos internos del clon (entre paréntesis, el "
         "resultado del mismo chequeo sobre el original; «= original» si el original tampoco lo cumple); "
         "**info** = solo diagnóstico.", "",
         "| Parte | Validada | PASA | NO PASA | Estado |", "|---|---|---|---|---|", *filas, ""]
    for p in PARTES:
        if p in previas:
            L += [previas[p], ""]
    salida.write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Valida el clon contra el original (ver ESPEC.md §4).")
    ap.add_argument("parte", nargs="?", default="todo", choices=PARTES + ["todo"])
    ap.add_argument("--detalle", type=int, default=5, metavar="N", help="ejemplos de diferencias por campo (5)")
    ap.add_argument("--clon-dir", default=str(comun.VISOR), help="carpeta del clon (visor/)")
    ap.add_argument("--orig-dir", default=str(comun.ORIGINAL), help="carpeta del original (_original/)")
    ap.add_argument("--salida", default=str(comun.RAIZ / "VALIDACION.md"), help="informe (VALIDACION.md)")
    a = ap.parse_args()
    t0 = time.time()
    clon_dir, orig_dir, salida = Path(a.clon_dir), Path(a.orig_dir), Path(a.salida)
    partes = PARTES if a.parte == "todo" else [a.parte]
    fecha = time.strftime("%Y-%m-%d %H:%M:%S")
    secs = {}
    print(f"Validando {', '.join(partes)} · clon: {clon_dir} · original: {orig_dir}")
    for i, p in enumerate(partes, 1):
        t1 = time.time()
        S = correr(p, orig_dir, clon_dir, a.detalle, fecha)
        secs[p] = S.markdown(fecha, rel(clon_dir / ARCHIVOS[p]), rel(orig_dir / ARCHIVOS[p]))
        pa, npa, inf = S.conteo()
        print(f"  [{100 * i // len(partes):3d} %] {p:8s} {pa:3d} PASA · {npa:3d} NO PASA · {inf:3d} info "
              f"({time.time() - t1:.1f} s)")
        for n in S.notas:
            print(f"      {n}")
        for g, campo, res, umb, est in S.filas:
            if est == NOPASA:
                print(f"      NO PASA  {campo}: {res} (umbral {umb})")
    escribir_informe(salida, secs, {"fecha": fecha, "partes": ", ".join(partes), "clon": rel(clon_dir),
                                    "orig": rel(orig_dir), "modelo": modelo_vectores(clon_dir, orig_dir)})
    print(f"Informe: {salida} · {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
