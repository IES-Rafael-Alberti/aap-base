"""Cliente mínimo para una API compatible con OpenAI (por defecto, OpenRouter).

Variables de entorno (o .env):
    AAP_API_KEY   clave del proveedor (vale también OPENROUTER_API_KEY)
    AAP_URL       endpoint de chat completions del proveedor
"""

import json
import os
import urllib.error
import urllib.request

URL_POR_DEFECTO = "https://openrouter.ai/api/v1/chat/completions"


class Modelo:
    def __init__(self, nombre: str, clave: str | None = None, timeout: int | None = None):
        self.nombre = nombre
        self.clave = (clave or os.environ.get("AAP_API_KEY")
                      or os.environ.get("OPENROUTER_API_KEY"))
        if not self.clave:
            raise RuntimeError("Falta la clave: define AAP_API_KEY en el entorno o en .env")
        self.url = os.environ.get("AAP_URL", URL_POR_DEFECTO)
        # Un modelo con razonamiento puede tardar: timeout amplio (configurable con AAP_TIMEOUT).
        self.timeout = timeout or int(os.environ.get("AAP_TIMEOUT", "300"))

    def responder(self, mensajes: list[dict], herramientas: list[dict]) -> dict:
        """Devuelve {"mensaje": {...}, "uso": {"entrada": n, "salida": n}}."""
        cuerpo = json.dumps({
            "model": self.nombre,
            "messages": mensajes,
            "tools": herramientas,
        }).encode()
        peticion = urllib.request.Request(self.url, data=cuerpo, headers={
            "Authorization": f"Bearer {self.clave}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout) as r:
                datos = json.load(r)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"El proveedor respondió {e.code}: {e.read()[:500]!r}") from e
        except TimeoutError as e:
            raise RuntimeError(f"El modelo no respondió en {self.timeout} s. "
                               "Súbelo con AAP_TIMEOUT.") from e
        uso = datos.get("usage", {})
        return {
            "mensaje": datos["choices"][0]["message"],
            "uso": {"entrada": uso.get("prompt_tokens", 0),
                    "salida": uso.get("completion_tokens", 0)},
        }
