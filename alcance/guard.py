"""La envoltura que protege cada herramienta con el scope-guard.

Uso:

    @protegida(objetivo="dominio")
    def whois_dominio(dominio: str) -> str:
        ...

`objetivo` es el nombre del argumento que contiene el objetivo. El motor
rechaza cualquier herramienta que no lleve esta envoltura.
"""

import functools
import logging

from alcance import en_alcance

log = logging.getLogger("scope-guard")

SCOPE = None  # lo fija el motor al arrancar con fijar_scope()


def fijar_scope(scope) -> None:
    global SCOPE
    SCOPE = scope


def protegida(objetivo: str):
    def decorador(herramienta):
        @functools.wraps(herramienta)
        def envoltura(**args):
            valor = str(args.get(objetivo, ""))
            if SCOPE is None or not en_alcance(valor, SCOPE):
                log.warning("bloqueado %s(%s=%r)", herramienta.__name__, objetivo, valor)
                return f"BLOQUEADO: {valor} está fuera del alcance autorizado."
            return herramienta(**args)

        envoltura.protegida = True
        envoltura.arg_objetivo = objetivo
        return envoltura
    return decorador


def filtrar(nombres, scope=None) -> tuple[list[str], int]:
    """Deja solo los nombres en alcance. Devuelve (en_alcance, n_filtrados)."""
    scope = scope or SCOPE
    dentro = [n for n in nombres if scope and en_alcance(n, scope)]
    return dentro, len(nombres) - len(dentro)
