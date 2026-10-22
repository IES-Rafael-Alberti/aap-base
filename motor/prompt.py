"""Construye el prompt de sistema del agente a partir de la plantilla, el
alcance (scope.txt) y las herramientas activas.

Así las instrucciones se arman solas: cuando cambias el scope.txt o añades una
herramienta, el prompt cambia con ello. Puedes verlo con:

    python lanzar.py --ver-prompt
"""

import inspect


def resumen_alcance(scope) -> str:
    incluir, excluir = scope
    lineas = []
    if incluir:
        lineas.append("Autorizado: " + ", ".join(incluir))
    if excluir:
        lineas.append("Excluido (nunca): " + ", ".join(excluir))
    return "\n".join(lineas) if lineas else "(vacío: todo queda fuera del alcance)"


def resumen_herramientas(herramientas) -> str:
    lineas = []
    for h in herramientas:
        doc = (inspect.getdoc(h) or "").strip().splitlines()
        primera = doc[0] if doc else "(sin descripción)"
        lineas.append(f"- {h.__name__}: {primera}")
    return "\n".join(lineas) if lineas else "(ninguna)"


def construir(plantilla: str, scope, herramientas) -> str:
    """Rellena {alcance} y {herramientas} en la plantilla."""
    return (plantilla
            .replace("{alcance}", resumen_alcance(scope))
            .replace("{herramientas}", resumen_herramientas(herramientas)))
