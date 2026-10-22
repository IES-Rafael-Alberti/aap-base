# aap-base · First Agent

Base del **Auditor Agéntico Progresivo** (UD1 · *Know Your Target*, Parte 2): un agente
de reconocimiento pasivo que solo actúa dentro de `scope.txt`.

| Carpeta / fichero | Qué es | ¿Lo tocas? |
|---|---|---|
| `motor/` | El bucle, el cliente del modelo (OpenRouter), la traza JSONL y los límites | No |
| `alcance/` | `en_alcance` (reglas de `scope.txt`) y la envoltura `protegida` | Sí |
| `herramientas/` | `whois.py` de ejemplo y `tus_herramientas.py` para las tuyas | Sí |
| `instrucciones.md` | El prompt de sistema del agente | Sí |
| `scope.txt` | El alcance autorizado: dominios, `*.comodines`, IPs, rangos CIDR y `!exclusiones` | Sí |
| `lanzar.py` | Arranca el agente | Solo la lista `HERRAMIENTAS` |
| `ver_traza.py` | Convierte `salida/traza.jsonl` en `salida/traza.log` | No |

El motor **rechaza cualquier herramienta que no esté protegida** por el `scope-guard`.

## Uso

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest alcance motor     # sin red ni tokens

echo 'AAP_API_KEY=...' > .env && chmod 600 .env   # con límite de gasto; AAP_URL si no es OpenRouter
.venv/bin/python lanzar.py "Investiga empresa.com"
.venv/bin/python ver_traza.py
```

El motor solo usa la biblioteca estándar de Python: no hay dependencias ocultas.
