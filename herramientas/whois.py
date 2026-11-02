"""Herramienta de ejemplo. Úsala como modelo para las tuyas.

Reglas que cumple:
- Una herramienta, una tarea.
- Sin shell: lista de argumentos, nunca shell=True.
- Con tiempo máximo.
- Salida recortada.
- Errores como texto.
"""

import json
import subprocess
import urllib.request

from guard import protegida

MAX_CARACTERES = 3000


def recortar(texto: str, maximo: int = MAX_CARACTERES) -> str:
    if len(texto) <= maximo:
        return texto
    return texto[:maximo] + f"\n[... recortado: {len(texto) - maximo} caracteres más]"


def _servidor_rdap(dominio: str) -> str:
    """Servidor RDAP del registro del dominio, según el directorio oficial de IANA."""
    tld = dominio.rstrip(".").rsplit(".", 1)[-1].lower()
    with urllib.request.urlopen("https://data.iana.org/rdap/dns.json", timeout=20) as r:
        servicios = json.load(r)["services"]
    for tlds, urls in servicios:
        if tld in tlds:
            return urls[0].rstrip("/") + "/"
    raise ValueError(f"el registro de .{tld} no ofrece RDAP")


def _rdap(dominio: str) -> str:
    """WHOIS por HTTPS (RDAP). Útil donde el puerto 43 está cerrado."""
    req = urllib.request.Request(f"{_servidor_rdap(dominio)}domain/{dominio}",
                                 headers={"User-Agent": "aap-recon/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.load(r)
    lineas = [f"Dominio: {d.get('ldhName', dominio)}"]
    for ev in d.get("events", []):
        lineas.append(f"{ev.get('eventAction')}: {ev.get('eventDate')}")
    for ent in d.get("entities", []):
        roles = ",".join(ent.get("roles", []))
        lineas.append(f"Entidad ({roles}): {ent.get('handle', '')}")
    ns = [n.get("ldhName", "") for n in d.get("nameservers", [])]
    if ns:
        lineas.append("Nameservers: " + ", ".join(ns))
    estados = d.get("status", [])
    if estados:
        lineas.append("Estado: " + ", ".join(estados))
    return recortar("\n".join(lineas))


@protegida(objetivo="dominio")
def whois_dominio(dominio: str) -> str:
    """Consulta el registro WHOIS de un dominio. Devuelve registrador,
    fechas de alta y caducidad y servidores DNS."""
    try:
        r = subprocess.run(["whois", dominio], capture_output=True,
                           text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return recortar(r.stdout)
        error_cmd = r.stderr.strip()[:200] or "sin salida"
    except subprocess.TimeoutExpired:
        error_cmd = "no respondió en 30 segundos"
    except FileNotFoundError:
        error_cmd = "whois no está instalado"
    # El puerto 43 puede estar cerrado (cortafuegos): probamos RDAP por HTTPS.
    try:
        return _rdap(dominio)
    except Exception as e:
        return f"ERROR: whois falló ({error_cmd}) y RDAP tampoco respondió: {e}"
