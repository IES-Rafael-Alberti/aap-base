"""Prueba UNA herramienta a mano, sin modelo y sin gastar tokens.

    python probar.py nmap_descubrir red=10.88.0.0/24
    python probar.py nmap_descubrir red=10.88.0.0/16       # más grande que tu alcance: BLOQUEADO
    python probar.py nmap_servicios host=10.88.0.20
    python probar.py cve_lookup host=10.88.0.20 puerto=9200

Usa tu scope.txt y el MISMO scope-guard que el agente. Busca la herramienta en
herramientas/tus_herramientas_enumeracion.py (o en el módulo que indiques con --modulo).
Las evidencias de las pruebas van a salida/pruebas/evidencias/, aparte de las del agente.
"""

import argparse
import importlib
import inspect
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
for carpeta in ("alcance", "motor", "herramientas"):
    sys.path.insert(0, str(RAIZ / carpeta))

from alcance import cargar  # noqa: E402
import escaneo              # noqa: E402
import guard                # noqa: E402


def argumentos(herramienta, pares: list[str]) -> dict:
    """['host=10.88.0.20', 'puerto=9200'] -> {'host': '10.88.0.20', 'puerto': 9200}."""
    firma = inspect.signature(herramienta)
    resultado = {}
    for par in pares:
        if "=" not in par:
            raise SystemExit(f"Argumento sin «=»: {par!r}. Usa nombre=valor, p. ej. host=10.88.0.20")
        nombre, valor = par.split("=", 1)
        if nombre not in firma.parameters:
            raise SystemExit(f"{herramienta.__name__} no tiene el parámetro «{nombre}». "
                             f"Tiene: {', '.join(firma.parameters)}")
        tipo = firma.parameters[nombre].annotation
        resultado[nombre] = int(valor) if tipo is int else valor
    return resultado


def main(argv=None) -> str:
    p = argparse.ArgumentParser(description="Prueba una herramienta a mano (sin modelo).")
    p.add_argument("herramienta", help="p. ej. nmap_descubrir")
    p.add_argument("args", nargs="*", help="nombre=valor")
    p.add_argument("--modulo", default="tus_herramientas_enumeracion")
    a = p.parse_args(argv)

    guard.fijar_scope(cargar(RAIZ / "scope.txt"))
    escaneo.usar_carpeta(RAIZ / "salida" / "pruebas" / "evidencias")
    modulo = importlib.import_module(a.modulo)
    herramienta = getattr(modulo, a.herramienta, None)
    if herramienta is None:
        raise SystemExit(f"No existe {a.herramienta} en {a.modulo}.py")
    if not getattr(herramienta, "protegida", False):
        raise SystemExit(f"{a.herramienta} no está protegida por el scope-guard: el agente la rechazaría")
    resultado = str(herramienta(**argumentos(herramienta, a.args)))
    print(resultado)
    return resultado


if __name__ == "__main__":
    main()
