# aap-base · First Agent

La primera pieza del **Auditor Agéntico Progresivo**: un agente de reconocimiento
**pasivo** que solo actúa dentro de lo que autorizas en `scope.txt`. Es el esqueleto
que vas a extender en el proyecto *Know Your Target* (UD1).

> Se ejecuta **dentro de tu Kali del laboratorio** y solo hace reconocimiento pasivo.
> No lo lances contra nada que no estés autorizado a investigar.

---

## 1. Descarga

Tu Kali ya trae lo necesario (`python3`, `whois`, `dig`, `subfinder`, `theHarvester`,
`curl`). Solo tienes que clonar el repositorio:

```bash
cd ~
git clone https://github.com/IES-Rafael-Alberti/aap-base.git
cd aap-base
```

## 2. Instalación

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest alcance motor      # debe salir "21 passed"
```

El motor no necesita ninguna librería (solo biblioteca estándar); `pytest` es solo
para las pruebas, que comprueban el `scope-guard` y el motor sin usar Internet.

## 3. Configuración

### 3.1 El modelo (obligatorio)

El agente habla con un modelo de lenguaje. Guarda sus datos con el asistente:

```bash
./configurar.sh
```

Te pide el **endpoint**, el **modelo** (serving name), la **clave** y, opcionalmente,
las claves de Hunter.io y Shodan. Todo queda en el fichero `.env` (que **nunca** se
sube a git). Si prefieres hacerlo a mano, copia `.env.ejemplo` a `.env` y rellénalo.

> Pon un **límite de gasto** en la clave del modelo antes de lanzar nada.

### 3.2 El objetivo y el alcance

Edita **`scope.txt`**: la lista blanca de lo que el agente puede tocar. Una entrada
por línea:

```
nextcloud.com          # dominio exacto
*.nextcloud.com        # subdominios (no incluye nextcloud.com)
10.10.0.0/24           # un rango de IPs (para labs)
!blog.nextcloud.com    # exclusión: lo de ! queda SIEMPRE fuera
```

Compruébalo antes de lanzar:

```bash
.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "alcance")
from alcance import cargar, en_alcance
s = cargar("scope.txt")
for o in ["www.nextcloud.com", "github.com"]:
    print(o, "->", "DENTRO" if en_alcance(o, s) else "fuera")
PY
```

### 3.3 Las herramientas

El agente trae 12 herramientas de recon pasivo. Dos necesitan una clave gratuita
(`hunter_io` → [hunter.io](https://hunter.io), `shodan_host` → [shodan.io](https://shodan.io));
sin ella avisan y las demás siguen funcionando. La lista de herramientas activas está
en `HERRAMIENTAS`, dentro de `lanzar.py`.

## 4. Uso

```bash
.venv/bin/python lanzar.py "Haz un reconocimiento pasivo completo de nextcloud.com usando todas las herramientas. Termina con un informe."
```

Opciones útiles: `--max-pasos N`, `--max-tokens N`, y la variable `AAP_TIMEOUT`
(segundos de espera al modelo) si el modelo es lento:

```bash
AAP_TIMEOUT=600 .venv/bin/python lanzar.py "..." --max-pasos 25
```

### Resultados

Todo queda en `salida/`:

- **`informe.md`** — el informe que redactó el agente.
- **`traza.jsonl`** — todo lo que hizo, paso a paso (para auditarlo).

Para leer la traza cómodamente:

```bash
.venv/bin/python ver_traza.py
cat salida/traza.log
```

---

## Qué hay en cada carpeta

| Carpeta / fichero | Qué es | ¿Lo tocas? |
|---|---|---|
| `motor/` | El bucle, el cliente del modelo y la traza | No |
| `alcance/` | `en_alcance` (reglas de `scope.txt`) y `protegida` (el `scope-guard`) | Sí |
| `herramientas/` | `whois.py` de ejemplo y tus herramientas | Sí |
| `scope.txt` | El alcance autorizado | Sí |
| `instrucciones.md` | El *prompt* de sistema del agente | Sí |
| `lanzar.py` | Arranca el agente (lista `HERRAMIENTAS`) | La lista |
| `ver_traza.py` | Convierte la traza en un log legible | No |

El motor **rechaza cualquier herramienta que no esté protegida** por el `scope-guard`.

## Si algo falla

| Síntoma | Qué hacer |
|---|---|
| `Falta la clave: define AAP_API_KEY` | Ejecuta `./configurar.sh` |
| `El modelo no respondió en 300 s` | Relanza con `AAP_TIMEOUT=600` |
| Un dominio no entra y debería | Revisa `scope.txt` con el comando del paso 3.2 |
| `BLOQUEADO: ...` en la traza | Es correcto: el `scope-guard` hizo su trabajo |
| `hunter_io`/`shodan_host` dicen "falta clave" | Es opcional; añade la clave al `.env` |

## Buenas prácticas

- **Límite de gasto** en la clave del modelo, siempre.
- Respeta el **ritmo** de peticiones del objetivo.
- **Datos personales**: enseña el patrón y el tipo de dato, no publiques listas de
  correos ni nombres.
- **No te fíes del informe**: contrástalo con la traza antes de darlo por bueno.
- El `.env` con tus claves **nunca** va a git.
