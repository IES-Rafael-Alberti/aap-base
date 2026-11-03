# aap-base · First Agent

La primera pieza del **Auditor Agéntico Progresivo**: un agente de reconocimiento
**pasivo** que solo actúa dentro de lo que autorizas en `scope.txt`.

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

Clónalo en tu carpeta personal: queda en `~/aap-base`, que es donde el profesor
actualiza tus datos de IA. Para recibir mejoras más adelante: `git pull` dentro de
`~/aap-base` (no toca tus archivos).

**El repositorio es privado** (equipo de ciber): necesitas tu cuenta de GitHub en la
organización. GitHub no acepta tu contraseña al clonar; la forma más sencilla es
iniciar sesión una vez con `gh`:

```bash
sudo apt install -y gh       # si tu Kali no lo tiene
gh auth login                # GitHub.com → HTTPS → Login with a web browser
gh auth setup-git            # git usará esa sesión para clone y pull
```

`gh auth login` te da un código: ábrelo en `github.com/login/device` desde cualquier
navegador. Alternativa sin `gh`: al clonar, escribe tu usuario y, como contraseña, un
*fine-grained token* (GitHub → Settings → Developer settings) con acceso **solo de
lectura** a este repositorio y con caducidad.

## 2. Instalación

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest alcance motor herramientas
```

El motor no necesita ninguna librería (solo biblioteca estándar); `pytest` es solo
para las pruebas, que comprueban el `scope-guard`, el motor y las herramientas sin usar Internet.

## 3. Configuración

### 3.1 El modelo

**En el Kali del aula no tienes que hacer nada.** Si no tocas nada, el agente usa la
IA del aula; si configuras tu `.env`, usa lo que pongas ahí.

- La IA del aula la pone el profesor al entregarte la clave: queda en `~/.aula-ia.env`
  (el agente la lee de ahí) y tienes una copia legible en `Acceso-IA.txt`, en el escritorio.
- Para verla o guardarla en tu `.env`, o para usar **otro proveedor** fuera del aula,
  ejecuta el asistente:

```bash
./configurar.sh
```

Te pide el **endpoint**, el **modelo** (serving name) y la **clave**. En el Kali del
aula, **Enter** deja los datos del aula. Todo queda en el fichero `.env` (que **nunca**
se sube a git), sin tocar las demás líneas que tengas. Si prefieres hacerlo a mano,
copia `.env.ejemplo` a `.env` y rellénalo.

Orden de preferencia: variables de la terminal → `.env` → `~/.aula-ia.env`. Si `.env`
tiene clave, de ahí salen también el endpoint y el modelo.

> Con un proveedor propio, pon un **límite de gasto** en la clave antes de lanzar nada.

### 3.2 Elige tu objetivo y pon su alcance

El agente solo tocará lo que autorices en **`scope.txt`**. Prepáralo en tres pasos:

1. **Elige un objetivo que te autorice a investigarlo.** Lo normal es un **programa
   público de bug bounty** (HackerOne, Bugcrowd, Intigriti…), donde la empresa invita
   por escrito a investigar lo que esté dentro de su alcance. También vale tu
   laboratorio.

2. **Mira el alcance en la página del programa.** Verás dos listas:
   - **In scope** (autorizado) → va tal cual en `scope.txt`.
   - **Out of scope** (excluido) → va con `!` delante.

3. **Tradúcelo** al formato de `scope.txt` (una entrada por línea):

   ```
   empresa.com          # dominio exacto
   *.empresa.com        # subdominios (no incluye empresa.com)
   10.10.0.0/24         # un rango de IPs (para labs)
   !blog.empresa.com    # exclusión: lo de ! queda SIEMPRE fuera
   ```

El propio `scope.txt` trae estas instrucciones y un sitio marcado para escribir.
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

El sistema incluye **tres herramientas implementadas y activas de partida**:

| Herramienta | Qué obtiene | Archivo |
|---|---|---|
| `whois_dominio` | Registro del dominio (WHOIS, con respaldo RDAP) | `herramientas/whois.py` |
| `dns_registros` | Registros A, AAAA, MX, NS, TXT, CNAME y SOA | `herramientas/tus_herramientas.py` |
| `subdominios_crtsh` | Subdominios de certificados públicos, filtrados por alcance | `herramientas/tus_herramientas.py` |

No necesitan claves de APIs adicionales. Para consultar subdominios, incluye
`*.empresa.com` en `scope.txt` solo si están autorizados, además del dominio raíz;
las exclusiones con `!` se respetan siempre. Si crt.sh no responde, la herramienta
devuelve el error para que el agente reconozca esa limitación.

Usa estas funciones como ejemplos para añadir herramientas en
`herramientas/tus_herramientas.py`. En su cabecera tienes ideas. Cuando termines una:

1. Escríbela siguiendo el modelo de `whois.py` (una tarea, protegida, sin shell, con
   timeout, salida recortada, errores como texto).
2. Impórtala en `lanzar.py` y añádela a la lista `HERRAMIENTAS`.

Muchas herramientas de recon no necesitan clave. Si construyes alguna que sí (por
ejemplo, una que use una API con registro), añade su clave al `.env` con el formato
`NOMBRE_API_KEY=valor` y léela en tu herramienta con
`os.environ.get("NOMBRE_API_KEY")`. Así la clave no queda escrita en el código.

## 4. Uso

Con las tres herramientas iniciales, ya puedes lanzarlo:

```bash
.venv/bin/python lanzar.py "Investiga el dominio <tu-objetivo>. Termina con un informe."
```

El informe inicial cubre registro, DNS y subdominios de certificados. No es un
reconocimiento exhaustivo: amplía las fuentes con tus herramientas (paso 3.3) y
comprueba que cada dato del informe está respaldado por la traza.

**El prompt se construye solo** a partir de tu `scope.txt` y de las herramientas
activas (lo fijo está en `instrucciones.md`, que normalmente no necesitas tocar).
Para ver el prompt ya montado, sin llamar al modelo ni gastar nada:

```bash
.venv/bin/python lanzar.py --ver-prompt
```

Cambia tu `scope.txt` o añade una herramienta y vuelve a ejecutarlo: verás cómo
cambia el prompt.

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
| `alcance/` | `en_alcance` (reglas de `scope.txt`) y `protegida` (el `scope-guard`) | No (viene hecho) |
| `herramientas/` | WHOIS, DNS, crt.sh y tus nuevas herramientas | Sí |
| `scope.txt` | El alcance autorizado | Sí |
| `instrucciones.md` | Plantilla del *prompt*; el alcance y las herramientas se rellenan solos | Opcional |
| `lanzar.py` | Arranca el agente (lista `HERRAMIENTAS`) | La lista |
| `ver_traza.py` | Convierte la traza en un log legible | No |

El motor **rechaza cualquier herramienta que no esté protegida** por el `scope-guard`.

## Si algo falla

| Problema | Qué hacer |
|---|---|
| `Tu Kali no tiene la IA del aula configurada` | En el aula: pide al profesor que te entregue la clave IA |
| `Falta la clave: define AAP_API_KEY` | Fuera del aula: ejecuta `./configurar.sh` |
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


## IA del aula desde el Kali

Al entregarte la clave, el profesor deja en tu Kali `~/.aula-ia.env` (servidor, modelo
`corsario-N` y clave) y su copia legible `Acceso-IA.txt` en el escritorio. Si ya tienes
`~/aap-base/.env`, también actualiza ahí `AAP_URL`, `AAP_MODELO` y `AAP_API_KEY`, y
conserva tus otras líneas. No ejecutes `~/.aula-ia.env` como shell ni compartas esos ficheros.

Con la clave del aula solo valen los modelos de tu aula: `aula-N` y `corsario-N`.
`ia-cupo` muestra tu gasto y cuándo se renueva, sin enseñar la clave.

| Mensaje | Qué hacer |
|---|---|
| Sin configuración | Pide al profesor que te entregue la clave IA |
| Clave no válida (401) | Pide al profesor que revise la entrega o la rotación |
| Modelo no disponible (403) | Usa el modelo de tu aula (`corsario-N` o `aula-N`) |
| Cupo agotado (422) | Espera a la renovación; consúltala con `ia-cupo` |
| 404/429 | Se consulta tu cupo: puede estar agotado, o es un límite de ritmo (espera un minuto) |
| Sin conexión o tiempo agotado | Avisa al profesor |

La consulta del cupo usa solo `http://10.30.0.6:4001/cupo` con tu clave; ninguna clave
de administración llega al Kali. Rotar la clave no reinicia el cupo. Si el servicio no
responde, no se inventa un saldo: reintenta más tarde o avisa al profesor.
