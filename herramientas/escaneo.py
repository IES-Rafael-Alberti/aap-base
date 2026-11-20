"""Piezas comunes de la fase de ENUMERACIÓN (UD2). Vienen hechas: no las toques.

Las usan tus herramientas de tus_herramientas_ud2.py. Aquí está la fontanería:

- lanzar nmap con las opciones que fija el profesor y leer su resultado;
- guardar la EVIDENCIA COMPLETA en la carpeta de la ejecución, con un identificador;
- consultar NVD (CVE, CVSS, CWE), EPSS (FIRST) y el catálogo KEV (CISA).

La idea clave: el agente RELEE TODO LO ANTERIOR EN CADA PASO. Si le pasas la
salida entera de nmap o de NVD, en pocos pasos se queda sin presupuesto y el
informe empeora. Por eso cada herramienta guarda el resultado completo en un
fichero y al modelo solo le pasa un resumen con el identificador de la
evidencia (E01, E02...), para que tú puedas comprobar cada dato.
"""

import ipaddress
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "salida"
CARPETA = SALIDA / "evidencias"     # enumerar.py la cambia: una carpeta por ejecución
CACHE = SALIDA / "cache"

# --- nmap: opciones FIJADAS por el profesor; el modelo no puede cambiarlas ----
# Sin scripts (-sC / --script): el proyecto prohíbe lo intrusivo.
# Solo TCP y solo IPv4, de momento. Sin sudo: -sT (connect) y sondas TCP.
# Ritmo -T3 (normal): hay un equipo antiguo y delicado en la red del proyecto,
# y «a lo bruto» (-T4/-T5) se cae. Tumbar un servicio es un 0 también para el agente.
NMAP_DESCUBRIR = ["-sn", "-n", "-T3", "-PS21,22,25,80,139,443,445,3306,3389,8080"]
NMAP_SERVICIOS = ["-sT", "-sV", "-p-", "-n", "-Pn", "-T3",
                  "--max-retries", "2", "--host-timeout", "15m"]
TIEMPO_DESCUBRIR = 300   # segundos
TIEMPO_SERVICIOS = 960

# --- Fuentes de vulnerabilidades: lista cerrada --------------------------------
NVD = "https://services.nvd.nist.gov/rest/json/cves/2.0"
EPSS = "https://api.first.org/data/v1/epss"
KEV = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
UA = "aap-enum/1.0 (educativo; IES Rafael Alberti)"


# ============================== Evidencias ===================================

def usar_carpeta(ruta: Path) -> None:
    """Las evidencias de esta ejecución van a `ruta` (enumerar.py: una carpeta por ejecución)."""
    global CARPETA
    CARPETA = Path(ruta)
    CARPETA.mkdir(parents=True, exist_ok=True)


def _mostrar(ruta: Path) -> str:
    try:
        return str(ruta.resolve().relative_to(RAIZ))
    except ValueError:
        return str(ruta)


def nueva_ejecucion() -> None:
    """Vacía la carpeta de evidencias actual."""
    CARPETA.mkdir(parents=True, exist_ok=True)
    for f in CARPETA.iterdir():
        if f.is_file():
            f.unlink()


def _seguro(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", texto)[:60] or "x"


def guardar_evidencia(herramienta: str, objetivo: str, contenido: str,
                      extension: str = "txt") -> str:
    """Guarda la salida COMPLETA y devuelve su identificador, p. ej.
    'E03 (salida/ejecuciones/2026-11-19_2027/evidencias/E03-nmap_servicios-172.17.0.5.xml)'."""
    CARPETA.mkdir(parents=True, exist_ok=True)
    n = 1 + sum(1 for f in CARPETA.glob("E*") if f.is_file())
    eid = f"E{n:02d}"
    nombre = f"{eid}-{_seguro(herramienta)}-{_seguro(objetivo)}.{extension}"
    (CARPETA / nombre).write_text(contenido, encoding="utf-8")
    return f"{eid} ({_mostrar(CARPETA / nombre)})"


def guardar_servicios(host: str, servicios: list[dict]) -> None:
    """Recuerda los servicios de un host para que cve_lookup los use después."""
    CARPETA.mkdir(parents=True, exist_ok=True)
    (CARPETA / f"servicios-{_seguro(host)}.json").write_text(
        json.dumps(servicios, ensure_ascii=False, indent=1), encoding="utf-8")


def servicios_de(host: str) -> list[dict] | None:
    """Los servicios que nmap_servicios observó en ese host, o None si no se escaneó."""
    f = CARPETA / f"servicios-{_seguro(host)}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def resumen_previo(clave: str) -> str | None:
    """Si esta consulta ya se hizo en esta ejecución, su resumen (para no repetirla)."""
    f = CARPETA / "resumenes.json"
    return json.loads(f.read_text(encoding="utf-8")).get(clave) if f.exists() else None


def recordar_resumen(clave: str, resumen: str) -> None:
    f = CARPETA / "resumenes.json"
    datos = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    datos[clave] = resumen
    CARPETA.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


# ============================== Utilidades ===================================

def es_ip(texto: str) -> bool:
    """True si es UNA dirección IPv4 (no un rango, ni un nombre, ni IPv6)."""
    try:
        return ipaddress.ip_address(texto.strip()).version == 4
    except ValueError:
        return False


def red_ipv4(texto: str) -> str | None:
    """La red IPv4 escrita como CIDR (172.17.0.0/24), en su forma canónica.
    None si no es eso: un nombre, IPv6, una máscara o un rango mal escrito."""
    t = texto.strip()
    if not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}/\d{1,2}", t):
        return None
    try:
        return str(ipaddress.IPv4Network(t, strict=False))
    except ValueError:
        return None


def limpio(texto, maximo: int = 80) -> str:
    """Texto que viene del OBJETIVO (banners, versiones, descripciones): son
    DATOS, no instrucciones. Una sola línea, sin caracteres raros y acotado."""
    t = " ".join(str(texto or "").split())
    t = "".join(c for c in t if c.isprintable())
    return t if len(t) <= maximo else t[:maximo] + "…"


# ================================= nmap ======================================

def ejecutar_nmap(opciones: list[str], objetivo: str, tiempo: int) -> tuple[str | None, str]:
    """Lanza nmap con las opciones fijadas y salida XML. Devuelve (xml, error)."""
    objetivo = objetivo.strip()
    if not objetivo or objetivo.startswith("-") or any(c.isspace() for c in objetivo):
        return None, f"objetivo no válido: {objetivo!r}"
    orden = ["nmap", *opciones, "-oX", "-", objetivo]
    try:
        r = subprocess.run(orden, capture_output=True, text=True, timeout=tiempo)
    except FileNotFoundError:
        return None, "nmap no está instalado"
    except subprocess.TimeoutExpired:
        return None, f"nmap no terminó en {tiempo} segundos"
    if r.returncode != 0 or "<nmaprun" not in r.stdout:
        return None, limpio(r.stderr or "nmap no devolvió resultados", 300)
    return r.stdout, ""


def escaneo_incompleto(xml: str) -> str:
    """'' si nmap terminó bien; si no, qué pasó. Un escaneo incompleto NO dice que
    los puertos estén cerrados: dice que no se pudo comprobar."""
    raiz = ET.fromstring(xml)
    sin_terminar = [d.get("addr") for h in raiz.iter("host") if h.get("timedout") == "true"
                    for d in h.iter("address") if d.get("addrtype") == "ipv4"]
    if sin_terminar:
        return f"tiempo máximo agotado en {', '.join(sin_terminar)}"
    fin = raiz.find("runstats/finished")
    if fin is not None and fin.get("exit") not in (None, "success"):
        return limpio(fin.get("errormsg") or "nmap no terminó correctamente", 200)
    return ""


def equipos_vivos(xml: str) -> list[str]:
    """Las IP que nmap da por vivas."""
    vivos = []
    for host in ET.fromstring(xml).iter("host"):
        estado = host.find("status")
        if estado is None or estado.get("state") != "up":
            continue
        for d in host.iter("address"):
            if d.get("addrtype") in ("ipv4", "ipv6"):
                vivos.append(d.get("addr"))
    return vivos


def servicios_abiertos(xml: str) -> list[dict]:
    """Un diccionario por puerto ABIERTO: puerto, protocolo, servicio, producto,
    version, extra y cpe (lista). Los textos vienen del objetivo: van limpios."""
    servicios = []
    for puerto in ET.fromstring(xml).iter("port"):
        estado = puerto.find("state")
        if estado is None or estado.get("state") != "open":
            continue
        s = puerto.find("service")
        s = s if s is not None else ET.Element("service")
        servicios.append({
            "puerto": int(puerto.get("portid")),
            "protocolo": puerto.get("protocol"),
            "servicio": limpio(s.get("name"), 30),
            "producto": limpio(s.get("product"), 60),
            "version": limpio(s.get("version"), 40),
            "extra": limpio(s.get("extrainfo"), 60),
            "cpe": [limpio(c.text, 100) for c in s.iter("cpe") if c.text],
        })
    return servicios


def describir_servicio(s: dict) -> str:
    """'22/tcp ssh · OpenSSH 7.4p1 (protocol 2.0)'."""
    texto = f"{s['puerto']}/{s['protocolo']} {s['servicio'] or '?'}"
    detalle = " ".join(x for x in (s["producto"], s["version"]) if x)
    if detalle:
        texto += f" · {detalle}"
    if s["extra"]:
        texto += f" ({s['extra']})"
    return texto


# ======================= Vulnerabilidades (NVD/EPSS/KEV) ======================

def _json(url: str, timeout: int = 60, cabeceras: dict | None = None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(cabeceras or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


_ultima_nvd = 0.0


def _esperar_nvd() -> None:
    """NVD sin clave admite 5 peticiones cada 30 s. Con AAP_NVD_KEY, más."""
    global _ultima_nvd
    pausa = 0.7 if os.environ.get("AAP_NVD_KEY") else 6.5
    falta = _ultima_nvd + pausa - time.monotonic()
    if falta > 0:
        time.sleep(falta)
    _ultima_nvd = time.monotonic()


NVD_MAXIMO = 2000   # lo máximo que NVD devuelve de una vez


ESPERAS_NVD = (10, 30, 60)   # segundos entre reintentos si NVD nos frena


def _nvd(parametros: dict) -> tuple[list[dict], int]:
    """(vulnerabilidades, total que dice NVD). Si total > len, faltan resultados.
    Si NVD rechaza por exceso de peticiones (403/429/503), espera y reintenta: en el
    aula salís muchos por la misma conexión. Con AAP_NVD_KEY el límite es 10 veces mayor."""
    clave = os.environ.get("AAP_NVD_KEY")
    url = f"{NVD}?{urllib.parse.urlencode({**parametros, 'resultsPerPage': NVD_MAXIMO})}"
    for espera in (*ESPERAS_NVD, None):
        _esperar_nvd()
        try:
            datos = _json(url, timeout=90, cabeceras={"apiKey": clave} if clave else None)
            break
        except urllib.error.HTTPError as ex:
            if ex.code not in (403, 429, 503) or espera is None:
                raise
            time.sleep(espera)
        except (urllib.error.URLError, TimeoutError):
            if espera is None:
                raise
            time.sleep(espera)
    vulns = datos.get("vulnerabilities", [])
    return vulns, int(datos.get("totalResults", len(vulns)))


def _incompleta(vulns: list, total: int) -> str:
    return f"; INCOMPLETA: NVD devolvió {len(vulns)} de {total}" if total > len(vulns) else ""


def version_corta(s: dict) -> str:
    """'7.4p1 Debian 10+deb9u7' -> '7.4p1'. Vacía si nmap no dio versión."""
    m = re.match(r"\d[\w.\-]*", s.get("version") or "")
    return m.group(0) if m else ""


def cpe_de(s: dict) -> str | None:
    """CPE 2.3 con versión a partir de lo que vio nmap (cpe:/a:vendor:producto:versión)."""
    for c in s.get("cpe", []):
        partes = c.removeprefix("cpe:/").split(":")
        if len(partes) >= 3 and partes[0] == "a":
            version = partes[3] if len(partes) > 3 and partes[3] else version_corta(s)
            if version:
                return f"cpe:2.3:a:{partes[1]}:{partes[2]}:{version}"
    return None


def _cve(item: dict) -> dict:
    c = item["cve"]
    cvss = version_cvss = severidad = None
    for clave in ("cvssMetricV31", "cvssMetricV40", "cvssMetricV30", "cvssMetricV2"):
        metricas = c.get("metrics", {}).get(clave) or []
        if metricas:
            m = next((x for x in metricas if x.get("type") == "Primary"), metricas[0])
            datos = m.get("cvssData", {})
            cvss = datos.get("baseScore")
            version_cvss = datos.get("version")
            severidad = datos.get("baseSeverity") or m.get("baseSeverity")
            break
    cwe = sorted({d["value"] for w in c.get("weaknesses", [])
                  for d in w.get("description", []) if d.get("value", "").startswith("CWE-")})
    desc = next((d["value"] for d in c.get("descriptions", []) if d.get("lang") == "en"), "")
    return {"id": c["id"], "cvss": cvss, "cvss_version": version_cvss,
            "severidad": severidad, "cwe": cwe, "descripcion": limpio(desc, 300),
            "publicado": (c.get("published") or "")[:10]}


def buscar_cves(s: dict) -> tuple[list[dict], str]:
    """CVE candidatos para un servicio. Devuelve (lista, cómo se buscó).
    Primero por CPE con versión (más preciso); si no hay, por palabras clave
    (trae más RUIDO). Puede lanzar excepción si NVD no responde."""
    cpe = cpe_de(s)
    if cpe:
        encontrados, total = _nvd({"virtualMatchString": cpe})
        if encontrados:
            return [_cve(i) for i in encontrados], f"NVD por CPE {cpe}{_incompleta(encontrados, total)}"
    if not (s.get("producto") and version_corta(s)):
        motivo = "la búsqueda por CPE no dio resultados" if cpe else "sin CPE"
        return [], (f"{motivo} y sin versión clara: no se busca por palabras sueltas "
                    "(traería CVE de cualquier versión)")
    palabras = f"{s['producto']} {version_corta(s)}"
    encontrados, total = _nvd({"keywordSearch": palabras})
    return ([_cve(i) for i in encontrados],
            f"NVD por palabras clave «{palabras}» (más ruido){_incompleta(encontrados, total)}")


def epss(ids: list[str]) -> dict[str, float]:
    """Probabilidad EPSS (0-1) de cada CVE. Los que no aparezcan, sin dato."""
    resultado = {}
    for i in range(0, len(ids), 100):
        datos = _json(f"{EPSS}?cve={','.join(ids[i:i + 100])}", timeout=20)
        for d in datos.get("data", []):
            resultado[d["cve"]] = float(d["epss"])
    return resultado


def kev() -> dict[str, dict]:
    """Catálogo KEV de CISA: CVE con explotación conocida. Se guarda 24 h en caché."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / "kev.json"
    if not f.exists() or time.time() - f.stat().st_mtime > 86_400:
        f.write_text(json.dumps(_json(KEV, timeout=120)), encoding="utf-8")
    datos = json.loads(f.read_text(encoding="utf-8"))
    return {v["cveID"]: {"fecha": v.get("dateAdded"),
                         "ransomware": v.get("knownRansomwareCampaignUse")}
            for v in datos.get("vulnerabilities", [])}


def ordenar_candidatos(cves: list[dict]) -> list[dict]:
    """Orden para el RESUMEN (no es la priorización final, que haces tú):
    primero los que están en KEV, luego mayor EPSS, luego mayor CVSS.
    En cada CVE, c["kev"] es: un dict (está en KEV), False (no está) o None (sin dato)."""
    return sorted(cves, key=lambda c: (isinstance(c.get("kev"), dict),
                                       c.get("epss") or 0.0, c.get("cvss") or 0.0),
                  reverse=True)


def describir_cve(c: dict) -> str:
    """'CVE-2021-41773 · CVSS 7.5 (3.1) · EPSS 0.94 · KEV desde 2021-11-03 ·
    ransomware: sí · CWE-22'. Fuera de KEV: 'KEV: no'. Sin comprobar: 'KEV: sin dato'."""
    partes = [c["id"]]
    partes.append(f"CVSS {c['cvss']} ({c['cvss_version']})" if c.get("cvss") is not None
                  else "CVSS sin dato")
    partes.append(f"EPSS {c['epss']:.3f}" if c.get("epss") is not None else "EPSS sin dato")
    if isinstance(c.get("kev"), dict):
        partes.append(f"KEV desde {c['kev'].get('fecha') or '?'}")
        uso = (c["kev"].get("ransomware") or "").lower()
        partes.append("ransomware: " + {"known": "sí", "unknown": "no consta"}.get(uso, "?"))
    elif c.get("kev") is False:
        partes.append("KEV: no")
    else:
        partes.append("KEV: sin dato")
    if c.get("cwe"):
        partes.append(", ".join(c["cwe"]))
    return " · ".join(partes)
