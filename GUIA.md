# Guía del First Agent · paso a paso

Esta guía te lleva desde encender tu Kali hasta lanzar tu agente de reconocimiento
contra un objetivo y leer su informe. Es la Parte 2 del proyecto *Know Your Target*.

> **Antes de empezar.** Todo esto se ejecuta **dentro de tu Kali del laboratorio**.
> El agente solo hace reconocimiento **pasivo** y solo contra lo que esté en tu
> `scope.txt`. No lo lances contra nada que no estés autorizado a investigar.

---

## 0. Qué es esto y qué hace

El *First Agent* es la primera pieza del Auditor Agéntico. Es un programa que:

1. Recibe un **objetivo** (un dominio) y unas **instrucciones**.
2. Un **modelo de lenguaje** decide qué herramienta de recon usar en cada momento
   (whois, dns, subdominios, shodan…).
3. **Tu código** ejecuta esa herramienta —siempre pasando por el `scope-guard`— y
   le devuelve el resultado al modelo.
4. El modelo repite hasta tener suficiente y **redacta un informe**.

La idea clave: **el modelo nunca ejecuta nada, solo pide**. Quien ejecuta es el
código, y por eso el código puede decir que no (el `scope-guard`).

---

## 1. Requisitos

Tu Kali del laboratorio ya trae instaladas las herramientas de línea de comandos que
usa el agente: `whois`, `dig`, `subfinder`, `theHarvester`, `curl` y `python3`.
No tienes que instalar ninguna. Solo necesitas:

- Conexión a Internet desde el Kali (el agente consulta fuentes públicas).
- Una **clave del modelo** (te la da el profesor o la creas en el proveedor).
- Opcional: claves gratuitas de **Hunter.io** y **Shodan** para dos herramientas extra.

---

## 2. Conseguir el sistema

Clona el repositorio en tu Kali (tu profesor te dará la dirección exacta):

```bash
cd ~
git clone <URL-del-repositorio> aap-base
cd aap-base
```

Dentro verás esta estructura:

```
aap-base/
├── lanzar.py          # arranca el agente  ← lo que ejecutas
├── configurar.sh      # guarda tus claves en .env
├── ver_traza.py       # convierte la traza a un log legible
├── scope.txt          # EL ALCANCE: qué puede tocar el agente  ← lo editas
├── instrucciones.md   # el prompt de sistema del agente        ← puedes editarlo
├── requirements.txt   # dependencias (solo pytest, para las pruebas)
├── .env.ejemplo       # plantilla de configuración
├── alcance/           # el scope-guard (en_alcance + protegida)
├── motor/             # el bucle del agente, cliente del modelo, traza  (no lo tocas)
├── herramientas/      # las herramientas de recon                        ← las amplías
└── salida/            # aquí aparecen el informe y la traza (se crea sola)
```

**Qué tocas y qué no:**

| Tocas tú | Viene hecho (no lo tocas) |
|---|---|
| `scope.txt`, `instrucciones.md` | `motor/` (el bucle, el cliente del modelo, la traza) |
| `herramientas/` (añadir tools) | `alcance/alcance.py` (si el profesor lo da hecho) |
| La lista `HERRAMIENTAS` de `lanzar.py` | |

---

## 3. Instalar

Crea el entorno de Python y comprueba que todo está bien con las pruebas:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest alcance motor
```

Debe salir algo como `21 passed`. Estas pruebas no usan Internet ni gastan dinero:
comprueban el `scope-guard` y el motor con un modelo simulado.

> El motor en sí **no necesita ninguna librería** (solo usa la biblioteca estándar de
> Python). `pytest` es únicamente para ejecutar las pruebas.

---

## 4. Configurar el modelo (la clave de la IA)

El agente habla con un modelo de lenguaje a través de una API compatible con OpenAI.
La configuración vive en un fichero llamado **`.env`** (nunca se sube a git).

La forma más fácil es el asistente:

```bash
./configurar.sh
```

Te preguntará:

1. **Endpoint**: la URL del proveedor (Enter para el valor por defecto, QDivZero).
2. **Modelo (serving name)**: el nombre del modelo desplegado, p. ej.
   `kyaky/Qwen3.6-35B-A3B-Uncensored-NVFP4`.
3. **Clave del modelo**: no se ve al escribirla.
4. **HUNTER_API_KEY y SHODAN_API_KEY** (opcionales): Enter para saltarlas.

Esto crea el `.env` con permisos `600` (solo tú puedes leerlo). Si prefieres hacerlo
a mano, copia `.env.ejemplo` a `.env` y rellénalo.

> **Pon un límite de gasto** en la clave del proveedor del modelo **antes** de lanzar
> nada. El límite del prompt es una recomendación; el límite de gasto es el freno real.

El `.env` final tiene esta pinta:

```
AAP_API_KEY=...            # clave del modelo (obligatoria)
AAP_URL=https://api.qdiv0.com/v1/chat/completions
AAP_MODELO=kyaky/Qwen3.6-35B-A3B-Uncensored-NVFP4
HUNTER_API_KEY=...         # opcional (herramienta de correos)
SHODAN_API_KEY=...         # opcional (herramienta de servicios)
AAP_TIMEOUT=600            # opcional: segundos de espera al modelo
```

---

## 5. Configurar el objetivo y el alcance

Hay **dos cosas distintas**:

- **El objetivo** es lo que le pides al agente cuando lo lanzas (ver paso 7).
- **El alcance** es `scope.txt`: la lista blanca de lo que el agente puede tocar.
  Aunque el modelo "quiera" salirse, el `scope-guard` se lo impide.

Edita `scope.txt`. Una entrada por línea:

```
# Comentarios con almohadilla
nextcloud.com          # dominio exacto
*.nextcloud.com        # cualquier subdominio (NO incluye nextcloud.com)
10.10.0.0/24           # un rango de IPs (para labs)
192.168.56.20          # una IP exacta
!blog.nextcloud.com    # exclusión: lo de ! queda SIEMPRE fuera
```

**Reglas, en orden:** se normaliza el objetivo → las exclusiones (`!`) ganan siempre →
coincidencia exacta → comodines y rangos → todo lo demás, **fuera**.

Comprueba tu `scope.txt` antes de lanzar nada (como pide la Parte 2.1):

```bash
.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "alcance")
from alcance import cargar, en_alcance
s = cargar("scope.txt")
for objetivo in ["www.nextcloud.com", "blog.nextcloud.com", "github.com"]:
    print(objetivo, "->", "DENTRO" if en_alcance(objetivo, s) else "fuera")
PY
```

---

## 6. Las herramientas

El agente solo puede usar las herramientas que estén en la lista `HERRAMIENTAS` de
`lanzar.py`. Las que vienen de serie:

| Herramienta | Qué hace | ¿Necesita clave? |
|---|---|---|
| `whois_dominio` | Registro del dominio (WHOIS/RDAP) | No |
| `dns_registros` | Registros DNS: A, AAAA, MX, NS, TXT, CNAME, SOA | No |
| `subdominios_crtsh` | Subdominios por transparencia de certificados | No |
| `subdominios_subfinder` | Subdominios con subfinder | No |
| `ficheros_expuestos` | robots.txt y security.txt | No |
| `wayback_urls` | URLs históricas (Wayback Machine) | No |
| `correos_personas` | Correos y hosts con theHarvester | No |
| `hunter_io` | Correos y patrón de correo | **Hunter.io** |
| `infraestructura_ip` | Quién aloja la IP (ASN, red, país) | No |
| `correo_postura` | SPF, DMARC, MTA-STS, CAA | No |
| `urlscan_busqueda` | Escaneos públicos de terceros (urlscan.io) | No |
| `shodan_host` | Puertos y servicios ya expuestos | **Shodan** |

Las dos que piden clave **funcionan sin ella también**: simplemente avisan de que
falta y el resto del recon sigue. Para activarlas, consigue las claves gratuitas en
[hunter.io](https://hunter.io) y [shodan.io](https://shodan.io) y métela en el `.env`
(con `./configurar.sh` o a mano).

Toda herramienta está **protegida por el `scope-guard`**: el motor **rechaza al
arrancar** cualquier herramienta que no lo esté. Para escribir las tuyas, copia el
patrón de `herramientas/whois.py` y añádelas a `HERRAMIENTAS` en `lanzar.py`.

---

## 7. Lanzar el agente

```bash
.venv/bin/python lanzar.py "Haz un reconocimiento pasivo completo de nextcloud.com usando todas las herramientas. Termina con un informe."
```

El texto entre comillas es **el objetivo / la orden**. Opciones útiles:

| Opción | Para qué | Por defecto |
|---|---|---|
| `--modelo <nombre>` | Usar otro modelo que el del `.env` | el de `AAP_MODELO` |
| `--max-pasos <n>` | Máximo de vueltas del bucle | 15 |
| `--max-tokens <n>` | Corta si se superan los tokens | 60000 |

Y la variable `AAP_TIMEOUT` (en el `.env` o delante del comando) sube la espera al
modelo si es lento:

```bash
AAP_TIMEOUT=600 .venv/bin/python lanzar.py "..." --max-pasos 25 --max-tokens 200000
```

Mientras corre, verás en pantalla el informe final y, abajo, los tokens gastados.

---

## 8. Ver los resultados

Todo queda en la carpeta `salida/`:

- **`salida/informe.md`** — el informe que redactó el agente.
- **`salida/traza.jsonl`** — todo lo que hizo, paso a paso, en formato para máquinas.
- Para leerla cómodamente:

```bash
.venv/bin/python ver_traza.py
cat salida/traza.log
```

La traza es lo que te permite **auditar** al agente: ver qué consultó, qué datos del
informe no salen de ninguna herramienta (**invenciones**), qué se dejó sin mirar
(**omisiones**) y qué intentó fuera de alcance (**bloqueos del scope-guard**). Es la
materia prima de la Parte 3 del proyecto.

---

## 9. Cómo funciona por dentro (resumen)

```
   TÚ                el MODELO (IA)              TU CÓDIGO (motor)         el SISTEMA
   │  objetivo + scope   │                           │                         │
   ├────────────────────►│                           │                         │
   │                     │  "usa whois_dominio(...)"  │                         │
   │                     ├──────────────────────────►│  scope-guard: ¿en        │
   │                     │                            │  alcance? sí ──► ejecuta ├──► whois
   │                     │       resultado (texto)    │◄────────────────────────┤
   │                     │◄───────────────────────────┤                         │
   │                     │  (repite con otra tool)    │                         │
   │     informe.md      │                            │                         │
   │◄────────────────────┤  (cuando tiene bastante)   │                         │
```

- **`motor/agente.py`**: el bucle. Rechaza herramientas sin `scope-guard` y corta por
  `--max-pasos` / `--max-tokens`.
- **`motor/modelo.py`**: habla con la API del modelo.
- **`motor/traza.py`**: escribe la traza JSONL.
- **`alcance/`**: `en_alcance` (las reglas de `scope.txt`) y `protegida` (la envoltura
  que protege cada herramienta).

---

## 10. Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `Falta la clave: define AAP_API_KEY` | No hay `.env` o está vacío | Ejecuta `./configurar.sh` |
| `El modelo no respondió en 300 s` | Modelo lento o despliegue reiniciándose | Relanza con `AAP_TIMEOUT=600` |
| Un dominio no entra y debería | `scope.txt` mal escrito | Revísalo con el comando del paso 5 |
| `BLOQUEADO: ...` en la traza | El objetivo está fuera de alcance | Es correcto: el scope-guard hizo su trabajo |
| `hunter_io`/`shodan_host` dicen "falta clave" | No pusiste esa clave | Es opcional; añádela al `.env` si la quieres |
| `wayback` da 503 | Fallo temporal de la fuente | Vuelve a lanzar más tarde |
| Datos raros tipo `2f...` en hosts | Dato "sucio" de la fuente | Anótalo: es justo lo que hay que detectar y revisar |

---

## 11. Buenas prácticas

- **Límite de gasto** en la clave del modelo, siempre, antes de lanzar.
- **Respeta el ritmo**: si el programa del objetivo limita peticiones, tu agente también.
- **Datos personales**: las herramientas de correos devuelven personas reales. En tu
  informe y tu entrega, enseña el **patrón** y el tipo de dato, pero **no publiques
  listas de correos ni nombres**.
- **No te fíes del informe**: revísalo contra la traza antes de darlo por bueno.
- El `.env` con tus claves **nunca** va a git (ya está en `.gitignore`).
