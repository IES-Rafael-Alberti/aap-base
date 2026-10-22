"""Herramientas de reconocimiento pasivo de la UD1.

Todas: protegidas por el scope-guard, sin shell, con timeout, salida recortada
y, cuando descubren nombres nuevos, filtrados por el alcance.
"""

import json
import os
import subprocess
import urllib.parse
import urllib.request

from guard import protegida, filtrar
from whois import recortar


def _dig(dominio: str, tipo: str) -> list[str]:
    try:
        r = subprocess.run(["dig", "+short", tipo, dominio],
                           capture_output=True, text=True, timeout=20)
        return [l.strip() for l in r.stdout.splitlines() if l.strip()]
    except Exception:
        return []

UA = "aap-recon/1.0 (educativo; IES Rafael Alberti)"
TIPOS_DNS = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"}


def _http(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


@protegida(objetivo="dominio")
def dns_registros(dominio: str, tipo: str = "A") -> str:
    """Consulta registros DNS de un dominio. tipo: A, AAAA, MX, NS, TXT, CNAME o SOA.
    Devuelve los valores, uno por línea."""
    tipo = tipo.upper()
    if tipo not in TIPOS_DNS:
        return f"ERROR: tipo DNS no válido ({tipo}). Usa uno de: {', '.join(sorted(TIPOS_DNS))}."
    try:
        r = subprocess.run(["dig", "+short", tipo, dominio],
                           capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return "ERROR: dig no respondió en 20 segundos."
    salida = r.stdout.strip()
    return salida or f"Sin registros {tipo} para {dominio}."


@protegida(objetivo="dominio")
def subdominios_crtsh(dominio: str) -> str:
    """Enumera subdominios de un dominio por transparencia de certificados (crt.sh).
    Pasivo: no toca el objetivo. Devuelve solo los subdominios dentro del alcance."""
    url = f"https://crt.sh/?q=%25.{urllib.parse.quote(dominio)}&output=json"
    try:
        datos = json.loads(_http(url, timeout=90))
    except Exception as e:
        return (f"ERROR: crt.sh no respondió ({e}). crt.sh suele ir lento; "
                "usa subdominios_subfinder como alternativa.")
    nombres = set()
    for fila in datos:
        for n in str(fila.get("name_value", "")).splitlines():
            n = n.strip().lstrip("*.").lower()
            if n:
                nombres.add(n)
    dentro, fuera = filtrar(sorted(nombres))
    cab = f"{len(dentro)} subdominios en alcance ({fuera} filtrados por estar fuera):\n"
    return recortar(cab + "\n".join(dentro))


@protegida(objetivo="dominio")
def subdominios_subfinder(dominio: str) -> str:
    """Enumera subdominios de un dominio con subfinder (fuentes pasivas).
    Devuelve solo los subdominios dentro del alcance."""
    try:
        r = subprocess.run(["subfinder", "-d", dominio, "-silent"],
                           capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return "ERROR: subfinder no respondió en 120 segundos."
    except FileNotFoundError:
        return "ERROR: subfinder no está instalado."
    nombres = [l.strip().lower() for l in r.stdout.splitlines() if l.strip()]
    dentro, fuera = filtrar(sorted(set(nombres)))
    cab = f"{len(dentro)} subdominios en alcance ({fuera} filtrados por estar fuera):\n"
    return recortar(cab + "\n".join(dentro))


@protegida(objetivo="dominio")
def ficheros_expuestos(dominio: str) -> str:
    """Lee ficheros públicos del sitio: robots.txt y security.txt. Pasivo."""
    partes = []
    for ruta in ("robots.txt", ".well-known/security.txt", "security.txt"):
        try:
            txt = _http(f"https://{dominio}/{ruta}", timeout=15)
            partes.append(f"=== /{ruta} ===\n{recortar(txt, 1200)}")
        except Exception as e:
            partes.append(f"=== /{ruta} ===\n(no disponible: {e})")
    return "\n\n".join(partes)


@protegida(objetivo="dominio")
def wayback_urls(dominio: str) -> str:
    """Lista URLs históricas del dominio archivadas en la Wayback Machine. Pasivo."""
    url = ("https://web.archive.org/cdx/search/cdx?"
           f"url={urllib.parse.quote(dominio)}&matchType=domain&output=text"
           "&fl=original&collapse=urlkey&limit=300")
    try:
        txt = _http(url, timeout=40)
    except Exception as e:
        return f"ERROR: Wayback no respondió: {e}"
    urls = sorted(set(l.strip() for l in txt.splitlines() if l.strip()))
    return recortar(f"{len(urls)} URLs históricas (muestra):\n" + "\n".join(urls))


@protegida(objetivo="dominio")
def correos_personas(dominio: str) -> str:
    """Recolecta correos y hosts de un dominio con theHarvester (fuentes pasivas sin clave).
    Dato sensible: en el informe, resume el tipo de dato, no publiques correos reales."""
    # Esta versión de theHarvester acepta UNA fuente por ejecución, no una lista.
    correos, hosts = set(), set()
    for fuente in ("crtsh", "duckduckgo", "bing", "rapiddns", "hackertarget", "otx"):
        try:
            r = subprocess.run(
                ["theHarvester", "-d", dominio, "-b", fuente, "-l", "100"],
                capture_output=True, text=True, timeout=90)
        except subprocess.TimeoutExpired:
            continue
        except FileNotFoundError:
            return "ERROR: theHarvester no está instalado."
        seccion = None
        for linea in r.stdout.splitlines():
            l = linea.strip()
            if "Emails found" in l:
                seccion = "correos"; continue
            if "Hosts found" in l:
                seccion = "hosts"; continue
            if l.startswith("[") or l.startswith("-") or not l:
                continue
            if seccion == "correos" and "@" in l:
                correos.add(l.lower())
            elif seccion == "hosts":
                hosts.add(l.split(":")[0].lower())
    hosts_dentro, fuera = filtrar(sorted(hosts))
    return recortar(
        f"Correos encontrados ({len(correos)}):\n" +
        ("\n".join(sorted(correos)) or "  (ninguno en fuentes públicas gratuitas)") +
        f"\n\nHosts encontrados en alcance ({len(hosts_dentro)}, {fuera} filtrados):\n" +
        "\n".join(hosts_dentro), 2800)


@protegida(objetivo="dominio")
def hunter_io(dominio: str) -> str:
    """Busca en Hunter.io los correos públicos de un dominio y su patrón
    (p. ej. {nombre}@dominio). Pasivo (lee su base de datos). Necesita HUNTER_API_KEY."""
    clave = os.environ.get("HUNTER_API_KEY")
    if not clave:
        return ("ERROR: falta HUNTER_API_KEY. Consigue una clave gratuita en "
                "hunter.io (25 búsquedas/mes) y añádela al .env.")
    # El plan gratuito de Hunter.io admite como mucho limit=10.
    url = (f"https://api.hunter.io/v2/domain-search?domain={urllib.parse.quote(dominio)}"
           f"&limit=10&api_key={clave}")
    try:
        d = json.loads(_http(url, timeout=30)).get("data", {})
    except Exception as e:
        return f"ERROR: Hunter.io no respondió: {e}"
    correos = [f"{e.get('value','')} ({e.get('type','')}, "
               f"{(e.get('first_name') or '')} {(e.get('last_name') or '')})".strip()
               for e in d.get("emails", [])]
    return recortar(
        f"Patrón de correo: {d.get('pattern') or '(desconocido)'}\n"
        f"Organización: {d.get('organization') or '?'}\n"
        f"Correos ({len(correos)}):\n" + ("\n".join(correos) or "  (ninguno)"))


@protegida(objetivo="dominio")
def subdominios_amass(dominio: str) -> str:
    """Enumera subdominios con amass en modo pasivo (más fuentes que subfinder).
    Devuelve solo los subdominios dentro del alcance."""
    try:
        r = subprocess.run(["amass", "enum", "-passive", "-d", dominio, "-timeout", "3"],
                           capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return "ERROR: amass no respondió en 300 segundos."
    except FileNotFoundError:
        return "ERROR: amass no está instalado."
    nombres = [l.strip().lower() for l in r.stdout.splitlines()
               if l.strip() and dominio in l]
    dentro, fuera = filtrar(sorted(set(nombres)))
    cab = f"{len(dentro)} subdominios en alcance ({fuera} filtrados por estar fuera):\n"
    return recortar(cab + "\n".join(dentro))


@protegida(objetivo="dominio")
def infraestructura_ip(dominio: str) -> str:
    """Resuelve el dominio a su IP y consulta quién la aloja (ASN, organización,
    rango de red y país) por RDAP. Pasivo: no escanea la IP."""
    ips = _dig(dominio, "A")
    if not ips:
        return f"Sin registro A para {dominio}; no hay IP que consultar."
    ip = ips[0]
    try:
        req = urllib.request.Request(f"https://rdap.org/ip/{ip}",
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
    except Exception as e:
        return f"IP {ip}: RDAP no respondió ({e})."
    org = ""
    for ent in d.get("entities", []):
        for v in ent.get("vcardArray", [[], []])[1]:
            if v and v[0] == "fn":
                org = v[3]
    lineas = [f"IP: {ip}",
              f"Rango: {d.get('startAddress','?')} - {d.get('endAddress','?')}",
              f"Red: {d.get('name','?')} ({d.get('handle','?')})",
              f"País: {d.get('country','?')}",
              f"Organización: {org or '?'}"]
    return "\n".join(lineas)


@protegida(objetivo="dominio")
def correo_postura(dominio: str) -> str:
    """Comprueba la configuración de seguridad del correo del dominio:
    SPF, DMARC, MTA-STS y registros CAA. Pasivo (consulta DNS pública)."""
    spf = [t for t in _dig(dominio, "TXT") if "v=spf1" in t]
    dmarc = _dig(f"_dmarc.{dominio}", "TXT")
    mtasts = _dig(f"_mta-sts.{dominio}", "TXT")
    caa = _dig(dominio, "CAA")
    def linea(nombre, valores):
        return f"{nombre}: " + ("; ".join(valores) if valores else "(no configurado)")
    return "\n".join([
        linea("SPF", spf),
        linea("DMARC", dmarc),
        linea("MTA-STS", mtasts),
        linea("CAA", caa),
    ])


@protegida(objetivo="dominio")
def urlscan_busqueda(dominio: str) -> str:
    """Busca en urlscan.io escaneos públicos del dominio hechos por terceros:
    URLs vistas y subdominios relacionados. Pasivo, sin clave."""
    url = f"https://urlscan.io/api/v1/search/?q=domain:{urllib.parse.quote(dominio)}&size=100"
    try:
        datos = json.loads(_http(url, timeout=30))
    except Exception as e:
        return f"ERROR: urlscan.io no respondió: {e}"
    urls, dominios = set(), set()
    for res in datos.get("results", []):
        pg = res.get("page", {})
        if pg.get("url"):
            urls.add(pg["url"])
        if pg.get("domain"):
            dominios.add(pg["domain"].lower())
    dentro, fuera = filtrar(sorted(dominios))
    cab = (f"{datos.get('total', 0)} escaneos en urlscan.io. "
           f"{len(dentro)} dominios en alcance ({fuera} filtrados), "
           f"{len(urls)} URLs vistas (muestra):\n")
    return recortar(cab + "\n".join(sorted(urls)[:60]))


@protegida(objetivo="dominio")
def shodan_host(dominio: str) -> str:
    """Consulta en Shodan los puertos y servicios ya expuestos en la IP del dominio,
    leyendo su base de datos (pasivo). Necesita SHODAN_API_KEY."""
    clave = os.environ.get("SHODAN_API_KEY")
    if not clave:
        return ("ERROR: falta SHODAN_API_KEY. Consigue una clave gratuita en "
                "shodan.io y añádela al .env.")
    ips = _dig(dominio, "A")
    if not ips:
        return f"Sin registro A para {dominio}."
    ip = ips[0]
    try:
        datos = json.loads(_http(f"https://api.shodan.io/shodan/host/{ip}?key={clave}",
                                 timeout=30))
    except Exception as e:
        return f"IP {ip}: Shodan no respondió o no tiene datos ({e})."
    puertos = datos.get("ports", [])
    servicios = [f"{s.get('port')}/{s.get('_shodan',{}).get('module','?')} "
                 f"{(s.get('product') or '').strip()}" for s in datos.get("data", [])]
    return recortar("\n".join([
        f"IP: {ip}",
        f"Organización: {datos.get('org','?')}",
        f"Puertos: {', '.join(map(str, puertos)) or 'ninguno'}",
        "Servicios:\n  " + "\n  ".join(servicios),
    ]))
