"""Regenera los tres archivos de datos del clon y después lo valida contra el original.

    python scripts/generar.py            # 05_tablero, 06_antes_despues, 07_matriz y validar todo
    python scripts/generar.py --sin-validar

La salida de cada paso se ve en pantalla y queda también en MT v4/armar_clon.log.
"""
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
LOG = AQUI.parents[1] / "armar_clon.log"
PASOS = ["05_tablero.py", "06_antes_despues.py", "07_matriz.py"]


def correr(script: str, args: list[str], log) -> int:
    print(f"\n=== {script} {' '.join(args)}", flush=True)
    log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} {script} {' '.join(args)}\n")
    p = subprocess.Popen([sys.executable, "-u", str(AQUI / script), *args], cwd=AQUI.parent,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    for linea in p.stdout:
        print(linea, end="", flush=True)
        log.write(linea)
        log.flush()
    return p.wait()


def main():
    validar = "--sin-validar" not in sys.argv
    pasos = PASOS + (["validar.py"] if validar else [])
    t0 = time.time()
    with LOG.open("w", encoding="utf-8") as log:
        for i, s in enumerate(pasos):
            print(f"\n[{100 * i // len(pasos)} %] paso {i + 1} de {len(pasos)}  ({time.time() - t0:.0f} s)", flush=True)
            args = {"validar.py": ["todo"],   # la matriz va con bge-m3: con tf-idf no pasa la validación
                    "07_matriz.py": ["--vectores", "npz", "--salida", "visor/matriz/datos_RITP.js"]}.get(s, [])
            cod = correr(s, args, log)
            if cod != 0:
                print(f"\n{s} terminó con error ({cod}). Log: {LOG}")
                sys.exit(cod)
    print(f"\n[100 %] listo en {time.time() - t0:.0f} s. Log: {LOG}")


if __name__ == "__main__":
    main()
