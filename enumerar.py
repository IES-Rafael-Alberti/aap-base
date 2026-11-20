"""Lanza el agente en la fase de ENUMERACIÓN, separada del recon pasivo.

    python enumerar.py --ver-prompt          # ver el prompt montado (no gasta)
    python enumerar.py "Enumera la red interna autorizada y sus vulnerabilidades potenciales. Termina con un informe."

Usa el MISMO scope.txt que lanzar.py, pero sus propias instrucciones
(instrucciones-enumeracion.md) y sus propias herramientas (tus_herramientas_enumeracion.py).

Cada ejecución queda en SU PROPIA CARPETA, sin pisar las anteriores:
    salida/ejecuciones/2026-11-19_2027/
        informe.md       el informe del agente
        traza.jsonl      lo que hizo (python ver_traza.py salida/ejecuciones/.../traza.jsonl)
        evidencias/      los ficheros E01, E02... que cita el informe
Lo que entregas es UNA de esas carpetas: la del informe que entregas.
"""

import argparse
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).parent
for carpeta in ("alcance", "motor", "herramientas"):
    sys.path.insert(0, str(RAIZ / carpeta))

from agente import Agente, LimiteAlcanzado  # noqa: E402
from alcance import cargar                  # noqa: E402
from modelo import Modelo                   # noqa: E402
from prompt import construir                # noqa: E402
from traza import Traza                     # noqa: E402
import escaneo                              # noqa: E402
from tus_herramientas_enumeracion import nmap_descubrir, nmap_servicios, cve_lookup  # noqa: E402

HERRAMIENTAS = [
    nmap_descubrir,
    nmap_servicios,
    cve_lookup,
]


def cargar_env(ruta: Path) -> None:
    """Lee CLAVE=valor de .env sin pisar lo que ya esté en el entorno."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.lstrip().startswith("#"):
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip("\"'"))


def nueva_carpeta() -> Path:
    """salida/ejecuciones/AAAA-MM-DD_HHMMSS/ (nunca reutiliza una existente)."""
    base = RAIZ / "salida" / "ejecuciones"
    carpeta = base / time.strftime("%Y-%m-%d_%H%M%S")
    n = 1
    while carpeta.exists():
        n += 1
        carpeta = base / f"{time.strftime('%Y-%m-%d_%H%M%S')}-{n}"
    carpeta.mkdir(parents=True)
    return carpeta


def solo_informe(texto: str) -> str:
    """Quita la frase de antes del título («Ahora tengo toda la información...»)."""
    lineas = texto.splitlines()
    for i, l in enumerate(lineas[:15]):
        if l.startswith("# "):
            return "\n".join(lineas[i:]).strip() + "\n"
    return texto


def main():
    cargar_env(RAIZ / ".env")
    p = argparse.ArgumentParser()
    p.add_argument("objetivo", nargs="?", help="lo que le pides al agente")
    p.add_argument("--modelo", default=os.environ.get("AAP_MODELO", "openai/gpt-4o-mini"))
    p.add_argument("--max-pasos", type=int, default=30)
    p.add_argument("--max-tokens", type=int, default=200_000)
    p.add_argument("--ver-prompt", action="store_true",
                   help="muestra el prompt de sistema ya montado y sale (no llama al modelo)")
    a = p.parse_args()

    scope = cargar(RAIZ / "scope.txt")
    plantilla = (RAIZ / "instrucciones-enumeracion.md").read_text(encoding="utf-8")
    instrucciones = construir(plantilla, scope, HERRAMIENTAS)

    if a.ver_prompt:
        print(instrucciones)
        return
    if not a.objetivo:
        p.error("falta el objetivo (o usa --ver-prompt para ver el prompt)")

    carpeta = nueva_carpeta()
    escaneo.usar_carpeta(carpeta / "evidencias")
    print(f"Ejecución en {carpeta.relative_to(RAIZ)}", file=sys.stderr)
    agente = Agente(
        modelo=Modelo(a.modelo),
        instrucciones=instrucciones,
        herramientas=HERRAMIENTAS,
        scope=scope,
        traza=Traza(carpeta / "traza.jsonl"),
        max_pasos=a.max_pasos,
        max_tokens=a.max_tokens,
    )
    try:
        informe = solo_informe(agente.ejecutar(a.objetivo))
    except LimiteAlcanzado as e:
        print(f"Parado sin informe: {e} (la traza queda en {carpeta.relative_to(RAIZ)})",
              file=sys.stderr)
        sys.exit(1)
    (carpeta / "informe.md").write_text(informe, encoding="utf-8")
    print(informe)
    print(f"\nTokens: {agente.tokens} · todo en {carpeta.relative_to(RAIZ)}", file=sys.stderr)


if __name__ == "__main__":
    main()
