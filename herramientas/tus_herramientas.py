"""Aquí van tus herramientas. Sigue el modelo de whois.py.

Para que el agente las use, añádelas a la lista HERRAMIENTAS de lanzar.py.
"""

from guard import protegida, filtrar  # noqa: F401
from whois import recortar            # noqa: F401


# @protegida(objetivo="dominio")
# def dns_registros(dominio: str, tipo: str) -> str:
#     """Describe aquí, para el modelo, qué hace y qué devuelve."""
#     # TODO: dig +short <tipo> <dominio>, sin shell y con timeout.
#     # Valida `tipo` contra una lista cerrada (A, MX, NS, TXT).
#     ...
