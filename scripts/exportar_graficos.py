"""Exporta, tal cual, los gráficos del tablero del clon (los SVG que dibuja plotagents) a SVG, PNG y PDF.

    python scripts/exportar_graficos.py                 # las cinco concesiones
    python scripts/exportar_graficos.py --conc CN AVO   # solo esas
    python scripts/exportar_graficos.py --vista cambios # el mapa en la vista «Sus cambios» (o «todo»)

Abre visor/index.html#c=<COD> en Edge (o Chrome) sin ventana, copia cada <svg> de #mapa y #g-* y lo guarda en
MT v4/graficos_clon/<COD>/. El SVG trae sus estilos adentro: se inserta directo en Word. El PNG (2×) y el PDF se
renderizan desde ese mismo SVG. Los rótulos HTML que el tablero pone encima del mapa no son parte del SVG.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

SALIDA = comun.RAIZ.parent / "graficos_clon"
NAVEGADORES = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
               r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
NOMBRES = {"mapa": "00_mapa", "g-com": "01_comunidades", "g-conc": "02_concentracion_citas",
           "g-citas": "03_mas_citados", "g-plantilla": "04_plantilla_comun", "g-mod-com": "05_modificacion_por_comunidad",
           "g-mod-cent": "06_centralidad_y_modificacion", "g-fases": "07_licitacion_vs_contrato",
           "g-anios": "08_modificaciones_por_anio", "g-ad-citas": "09_antes_despues_citas",
           "g-ad-texto": "10_antes_despues_texto"}


def navegador() -> str:
    for n in NAVEGADORES:
        if Path(n).exists():
            return n
    sys.exit("no encontré Edge ni Chrome")


def correr(nav, perfil, *args, timeout=120):
    subprocess.run([nav, "--headless=new", "--disable-gpu", f"--user-data-dir={perfil}", *args],
                   capture_output=True, timeout=timeout)


def svgs_de(dom: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r'<div id="(g-[a-z-]+|mapa)"[^>]*>', dom):
        s = dom.find("<svg", m.end())
        e = dom.find("</svg>", s)
        if s < 0 or e < 0 or m.group(1) in out:
            continue
        svg = dom[s:e + 6]
        out[m.group(1)] = svg if "xmlns=" in svg[:200] else svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conc", nargs="*", default=comun.ORDEN)
    ap.add_argument("--vista", choices=["bases", "cambios", "todo"], default="bases")
    a = ap.parse_args()
    nav = navegador()
    index = (comun.VISOR / "index.html").resolve().as_uri()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        perfil = tmp / "perfil"
        for i, cod in enumerate(a.conc):
            print(f"[{100 * i // len(a.conc):3d} %] {cod}", flush=True)
            hash_ = f"#c={cod}" + ("" if a.vista == "bases" else f"&v={a.vista}")
            dom = subprocess.run([nav, "--headless=new", "--disable-gpu", f"--user-data-dir={perfil}",
                                  "--window-size=1400,3000", "--virtual-time-budget=9000", "--dump-dom", index + hash_],
                                 capture_output=True, timeout=180).stdout.decode("utf-8", "replace")
            dest = SALIDA / (cod if a.vista == "bases" else f"{cod}_{a.vista}")
            dest.mkdir(parents=True, exist_ok=True)
            for id_, svg in svgs_de(dom).items():
                nombre = NOMBRES.get(id_, id_)
                (dest / f"{nombre}.svg").write_text(svg, encoding="utf-8")
                w, h = (int(float(x)) for x in re.search(r'width="([\d.]+)" height="([\d.]+)"', svg).groups())
                html = tmp / f"{nombre}.html"
                html.write_text(f'<!doctype html><meta charset="utf-8"><style>@page{{size:{w}px {h}px;margin:0}}'
                                f'html,body{{margin:0;background:#fff}}</style>{svg}', encoding="utf-8")
                correr(nav, perfil, f"--window-size={w},{h}", "--force-device-scale-factor=2", "--hide-scrollbars",
                       f"--screenshot={dest / (nombre + '.png')}", html.as_uri())
                correr(nav, perfil, "--no-pdf-header-footer", f"--print-to-pdf={dest / (nombre + '.pdf')}", html.as_uri())
            print(f"       {len(list(dest.glob('*.svg')))} gráficos → {dest}", flush=True)
    print(f"[100 %] listo: {SALIDA}")


if __name__ == "__main__":
    main()
