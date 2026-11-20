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

Si lo que se pide es un RANGO (10.10.0.0/16), se comprueba aparte: tiene que
caber entero dentro de una inclusión y no contener ninguna exclusión. Lo que va
tras la barra es el tamaño de la red; no se puede descartar como en una URL.
"""

import ipaddress
import re
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


def _como_red(regla: str):
    """Una regla del scope como red: 10.10.0.0/24 o una IP sola (/32)."""
    try:
        return ipaddress.ip_network(regla, strict=False)
    except ValueError:
        return None


def _red_en_alcance(red, scope) -> bool:
    """Un rango pedido está en alcance solo si cabe ENTERO en una inclusión
    y no contiene ninguna exclusión (escanearlo tocaría lo excluido)."""
    incluir, excluir = scope
    for regla in excluir:
        r = _como_red(regla)
        if r is not None and r.version == red.version and red.overlaps(r):
            return False
    for regla in incluir:
        r = _como_red(regla)
        if r is not None and r.version == red.version and red.subnet_of(r):
            return True
    return False


def en_alcance(objetivo: str, scope: tuple[list[str], list[str]]) -> bool:
    incluir, excluir = scope
    # Rango pedido (10.10.0.0/16): lo que va tras la barra es su TAMAÑO, no una
    # ruta web. No se puede normalizar quitándolo: hay que comprobarlo entero.
    pedido = objetivo.strip().lower()
    if "://" not in pedido and "/" in pedido:
        base = pedido.split("/", 1)[0]
        if _como_ip(base) is not None:
            # Una IP con barra es un rango, y solo vale escrito tal cual: 10.10.0.0/24.
            # Nada de «/ 24», «/+24», «/24x» ni máscaras (/255.255.255.0).
            if not re.fullmatch(r"[0-9a-f.:]+/\d{1,3}", pedido):
                return False
            red = _como_red(pedido)
            return red is not None and _red_en_alcance(red, scope)
        if re.fullmatch(r"[^/\s]+/\d+", pedido):     # nombre/24: no es un rango válido
            return False
    t = normalizar(objetivo)
    if not t:
        return False
    ip = _como_ip(t)
    if any(_coincide(t, ip, r) for r in excluir):
        return False
    return any(_coincide(t, ip, r) for r in incluir)
