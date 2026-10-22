"""scope-guard: decide si un objetivo está dentro del alcance autorizado.

Formato de scope.txt (una entrada por línea):

    empresa.com          dominio exacto
    *.empresa.com        cualquier subdominio (NO incluye empresa.com)
    10.10.0.5            IP exacta
    10.10.0.0/24         rango CIDR
    !blog.empresa.com    exclusión (gana siempre a las inclusiones)
    # comentario         se ignora, igual que las líneas vacías

Reglas, en este orden:
  1. Normalizar el objetivo.
  2. Exclusiones primero.
  3. Coincidencia exacta.
  4. Comodines y rangos.
  5. Todo lo demás, fuera (lista blanca).
"""

import ipaddress
from pathlib import Path


def normalizar(objetivo: str) -> str:
    """https://API.Empresa.com:443/login -> api.empresa.com"""
    t = objetivo.strip().lower()
    if "://" in t:
        t = t.split("://", 1)[1]
    t = t.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    t = t.rsplit("@", 1)[-1]                  # usuario:clave@host
    if t.startswith("["):                     # [IPv6]:puerto
        t = t[1:].split("]", 1)[0]
    elif t.count(":") == 1:                   # host:puerto (no IPv6)
        t = t.split(":", 1)[0]
    return t.rstrip(".")


def _como_ip(texto: str):
    try:
        return ipaddress.ip_address(texto)
    except ValueError:
        return None


def _coincide(objetivo: str, ip, regla: str) -> bool:
    if "/" in regla:                          # rango CIDR
        try:
            red = ipaddress.ip_network(regla, strict=False)
        except ValueError:
            return False
        return ip is not None and ip.version == red.version and ip in red
    if regla.startswith("*."):                # comodín de dominio
        return ip is None and objetivo.endswith(regla[1:])
    regla_ip = _como_ip(regla)
    if regla_ip is not None:                  # IP exacta
        return ip == regla_ip
    return objetivo == regla                  # dominio exacto


def cargar(ruta: str | Path) -> tuple[list[str], list[str]]:
    """Lee scope.txt y devuelve (inclusiones, exclusiones)."""
    incluir, excluir = [], []
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        linea = linea.split("#", 1)[0].strip().lower()
        if not linea:
            continue
        destino = excluir if linea.startswith("!") else incluir
        regla = linea.lstrip("!").strip()
        destino.append(regla if "/" in regla else normalizar(regla))  # CIDR tal cual
    return incluir, excluir


def en_alcance(objetivo: str, scope: tuple[list[str], list[str]]) -> bool:
    incluir, excluir = scope
    t = normalizar(objetivo)
    if not t:
        return False
    ip = _como_ip(t)
    if any(_coincide(t, ip, r) for r in excluir):
        return False
    return any(_coincide(t, ip, r) for r in incluir)
