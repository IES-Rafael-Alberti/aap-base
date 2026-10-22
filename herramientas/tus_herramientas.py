"""Tus herramientas de reconocimiento. AQUÍ TRABAJAS TÚ.

Tienes `whois.py` como ejemplo COMPLETO: cópialo como modelo. Cada herramienta debe:
- hacer UNA tarea;
- estar protegida con @protegida(objetivo="<arg>");
- no usar shell (lista de argumentos, nunca shell=True);
- tener timeout, recortar la salida y filtrar por el alcance lo que descubra;
- devolver los errores como texto (no lanzar excepciones).

Cuando termines una, impórtala y añádela a la lista HERRAMIENTAS de lanzar.py.

Herramientas pasivas que puedes construir (al menos 2, como pide la Parte 2.2):
  dns_registros, subdominios_crtsh, subdominios_subfinder, ficheros_expuestos,
  wayback_urls, correos (theHarvester / hunter.io), infraestructura_ip,
  correo_postura (SPF/DMARC/MTA-STS/CAA), urlscan, shodan_host.
"""

import subprocess  # noqa: F401
import urllib.request  # noqa: F401

from guard import protegida, filtrar  # noqa: F401
from whois import recortar  # noqa: F401


@protegida(objetivo="dominio")
def dns_registros(dominio: str, tipo: str = "A") -> str:
    """Consulta registros DNS de un dominio. tipo: A, AAAA, MX, NS, TXT, CNAME o SOA.
    Devuelve los valores, uno por línea."""
    # TODO: valida `tipo` contra una lista cerrada (no cualquier cosa).
    # TODO: ejecuta `dig +short <tipo> <dominio>` con subprocess (sin shell, con timeout).
    # TODO: devuelve la salida recortada, o un texto si no hay registros o falla.
    raise NotImplementedError("Implementa dns_registros (mira whois.py como modelo).")


@protegida(objetivo="dominio")
def subdominios_crtsh(dominio: str) -> str:
    """Enumera subdominios por transparencia de certificados (crt.sh). Pasivo.
    Devuelve solo los subdominios dentro del alcance."""
    # TODO: pide https://crt.sh/?q=%25.<dominio>&output=json y parsea el JSON.
    # TODO: junta los nombres (quita '*.') y deja solo los que estén en alcance (filtrar()).
    # TODO: devuelve el resultado recortado.
    raise NotImplementedError("Implementa subdominios_crtsh (mira whois.py como modelo).")
