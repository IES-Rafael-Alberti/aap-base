"""Convierte salida/traza.jsonl en el traza.log legible.

    python ver_traza.py                 # escribe salida/traza.log
"""

import json
import sys
from pathlib import Path


def una_linea(texto: str, maximo: int = 160) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= maximo else texto[:maximo] + " ..."


def legible(eventos) -> str:
    salida = []
    for e in eventos:
        if e["tipo"] == "inicio":
            salida.append(f"# objetivo: {e['objetivo']} · modelo: {e['modelo']}")
        elif e["tipo"] == "herramienta":
            marca = "  [BLOQUEADO]" if e["bloqueado"] else ""
            salida.append(f"[{e['paso']}] modelo → {e['nombre']}({e['argumentos']}){marca}")
            salida.append(f"    ← {una_linea(e['resultado'])}")
        elif e["tipo"] == "fin":
            salida.append(f"# fin en el paso {e['paso']} · tokens: {e['tokens']}")
        elif e["tipo"] == "limite":
            salida.append(f"# PARADO por límite de {e['motivo']} · tokens: {e['tokens']}")
    return "\n".join(salida) + "\n"


if __name__ == "__main__":
    origen = Path(sys.argv[1] if len(sys.argv) > 1 else "salida/traza.jsonl")
    eventos = [json.loads(l) for l in origen.read_text(encoding="utf-8").splitlines() if l]
    destino = origen.with_suffix(".log")
    destino.write_text(legible(eventos), encoding="utf-8")
    print(f"Escrito {destino}")
