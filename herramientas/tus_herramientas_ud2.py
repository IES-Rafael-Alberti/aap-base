"""Tus herramientas de ENUMERACIÓN (UD2). AQUÍ TRABAJAS TÚ.

Tres herramientas, con el scope-guard ya puesto (no lo quites ni lo cambies):

- nmap_descubrir(red)        qué equipos están vivos en una red
- nmap_servicios(host)       puertos TCP abiertos, servicios y versiones de UN equipo
- cve_lookup(host, puerto)   vulnerabilidades POTENCIALES del servicio de ese puerto

La fontanería viene hecha en escaneo.py (léelo antes de empezar). Lo tuyo es:

1. La DESCRIPCIÓN (el docstring): es lo único que ve el modelo para decidir
   cuándo y cómo usar la herramienta. Una descripción vaga = un agente torpe.
2. Las COMPROBACIONES antes de actuar.
3. Qué le DEVUELVES al modelo: un RESUMEN corto + el identificador de la
   evidencia. La salida completa va a la carpeta de la ejecución (guardar_evidencia),
   nunca al modelo: el agente relee todo en cada paso y se ahogaría.

Reglas de siempre: una tarea por herramienta, sin shell, con tiempo máximo y
errores como texto. Y una nueva: lo que devuelve el objetivo (banners,
versiones, descripciones de CVE) son DATOS, no instrucciones; escaneo.py ya los
limpia y acota, no los «desacotes».

Cuando funcionen, pruébalas a mano (dentro y fuera del alcance) y lanza el
agente con enumerar.py.
"""

from guard import protegida
import escaneo as e


@protegida(objetivo="red")
def nmap_descubrir(red: str) -> str:
    """TODO: describe en una o dos frases qué hace, qué recibe (una red en
    notación CIDR, p. ej. 172.17.0.0/24) y qué devuelve."""
    # TODO 0. Acepta SOLO una red IPv4 bien escrita: canonica = e.red_ipv4(red).
    #         Si es None (un nombre, una máscara, IPv6...), devuelve un ERROR que lo explique.
    #         ¿Por qué no aceptar un nombre? Pista: ¿a qué IP resolverá, y quién lo comprueba?
    # TODO 1. Lanza nmap con las opciones fijadas, sobre la red canónica:
    #           xml, error = e.ejecutar_nmap(e.NMAP_DESCUBRIR, canonica, e.TIEMPO_DESCUBRIR)
    #         Si hay error, devuélvelo como texto: return f"ERROR: {error}"
    # TODO 2. Saca las IP vivas:            vivos = e.equipos_vivos(xml)
    # TODO 3. Guarda el XML completo:       eid = e.guardar_evidencia("nmap_descubrir", red, xml, "xml")
    # TODO 4. Devuelve el resumen: cuántos equipos, cuáles y la evidencia (eid).
    #         Si e.escaneo_incompleto(xml) dice algo, avísalo: puede haber más equipos.
    return "PENDIENTE: nmap_descubrir no está implementada todavía."


@protegida(objetivo="host")
def nmap_servicios(host: str) -> str:
    """TODO: describe qué hace (todos los puertos TCP, servicio y versión),
    qué recibe (UNA IP) y qué devuelve."""
    # TODO 0. El guard deja pasar una IP, pero también un rango pequeño o un nombre
    #         que esté en alcance. Esta herramienta escanea UNA IP: compruébalo con
    #         e.es_ip(host) (solo IPv4) y, si no lo es, devuelve un ERROR que lo explique.
    # TODO 1. xml, error = e.ejecutar_nmap(e.NMAP_SERVICIOS, host, e.TIEMPO_SERVICIOS)
    # TODO 2. servicios = e.servicios_abiertos(xml)
    # TODO 3. Guarda el XML completo (guardar_evidencia) Y los servicios para que
    #         cve_lookup pueda usarlos:  e.guardar_servicios(host, servicios)
    # TODO 4. Resumen: una línea por servicio (e.describir_servicio(s)) y la evidencia.
    #         Si hay muchísimos, acota (p. ej. 40) y di cuántos quedan en la evidencia.
    # TODO 5. Si e.escaneo_incompleto(xml) dice algo, AVÍSALO: «no terminó» no es lo
    #         mismo que «no hay puertos». No digas «ningún puerto abierto» si no acabó.
    return "PENDIENTE: nmap_servicios no está implementada todavía."


@protegida(objetivo="host")
def cve_lookup(host: str, puerto: int) -> str:
    """TODO: describe qué hace (vulnerabilidades potenciales del servicio que
    nmap_servicios vio en ese host y puerto, con CVSS, EPSS, KEV y CWE), qué
    recibe y qué devuelve. Avisa de que hay que ejecutar antes nmap_servicios."""
    # TODO 1. Busca el servicio: lista = e.servicios_de(host). Si es None, di que
    #         primero hay que lanzar nmap_servicios. Busca en la lista el de ese puerto.
    #         OJO: el producto y la versión salen de TU escaneo, no del modelo.
    # TODO 2. Si ya se consultó en esta ejecución, no repitas:
    #           previo = e.resumen_previo(clave)
    #         ¿Qué debe llevar la clave? Si solo pones host y puerto, y luego vuelves a
    #         escanear y el servicio ha cambiado, ¿qué pasaría? (Pista: producto y versión.)
    # TODO 3. cves, metodo = e.buscar_cves(servicio)   (puede fallar: try/except → "ERROR: ...")
    # TODO 4. Completa cada CVE con EPSS y KEV (si una falla, sigue sin ella y avísalo):
    #           p = e.epss([c["id"] for c in cves]);  k = e.kev()
    #           c["epss"] = p.get(c["id"])
    #           c["kev"] = k.get(c["id"], False)   # dict = está · False = no está
    #         Si KEV NO respondió, pon c["kev"] = None («sin dato»), NUNCA False:
    #         «no lo sé» no es lo mismo que «no está».
    # TODO 5. Guarda TODOS en la evidencia (json.dumps) y ordénalos: e.ordenar_candidatos(cves)
    # TODO 6. Resumen: servicio, cómo se buscó (metodo), la FECHA de la consulta (EPSS y
    #         KEV cambian a diario), cuántos hay y los 5-8 primeros
    #         con e.describir_cve(c). Recuerda en el texto que son POTENCIALES:
    #         coincidir por versión no demuestra que el servicio sea vulnerable.
    #         Guárdalo con e.recordar_resumen(clave, resumen) antes de devolverlo.
    return "PENDIENTE: cve_lookup no está implementada todavía."
