"""El bucle del agente.

1. El modelo recibe instrucciones, objetivo y la lista de herramientas.
2. Pide una herramienta con unos argumentos.
3. El código la ejecuta (siempre a través del scope-guard) y le devuelve el resultado.
4. Vuelta al paso 2, hasta que el modelo responde sin pedir herramientas
   o se alcanza un límite. Si se alcanza, el modelo tiene UNA última vuelta,
   ya sin herramientas, para redactar el informe con lo que tenga (parcial).

El modelo nunca ejecuta nada: solo pide.
"""

import inspect
import json

from guard import fijar_scope

TIPOS = {str: "string", int: "integer", float: "number", bool: "boolean"}


def describir(herramienta) -> dict:
    """Lo único que el modelo ve de una herramienta: nombre, descripción y parámetros."""
    firma = inspect.signature(herramienta)
    propiedades = {
        nombre: {"type": TIPOS.get(p.annotation, "string")}
        for nombre, p in firma.parameters.items()
    }
    obligatorios = [n for n, p in firma.parameters.items() if p.default is p.empty]
    return {"type": "function", "function": {
        "name": herramienta.__name__,
        "description": inspect.getdoc(herramienta) or "",
        "parameters": {"type": "object", "properties": propiedades,
                       "required": obligatorios},
    }}


class LimiteAlcanzado(Exception):
    pass


CIERRE = ("Has alcanzado el límite de {motivo} de esta ejecución. Ya NO puedes usar "
          "herramientas. Redacta AHORA el informe final con lo que tengas, con el formato "
          "pedido, y di al principio que es PARCIAL y qué quedó sin hacer.")


class Agente:
    def __init__(self, modelo, instrucciones, herramientas, scope, traza,
                 max_pasos=15, max_tokens=60_000):
        for h in herramientas:
            if not getattr(h, "protegida", False):
                raise ValueError(f"{h.__name__} no está protegida por el scope-guard")
        fijar_scope(scope)
        self.modelo = modelo
        self.instrucciones = instrucciones
        self.herramientas = {h.__name__: h for h in herramientas}
        self.esquemas = [describir(h) for h in herramientas]
        self.traza = traza
        self.max_pasos = max_pasos
        self.max_tokens = max_tokens
        self.tokens = {"entrada": 0, "salida": 0}

    def _ejecutar(self, llamada: dict) -> str:
        nombre = llamada["function"]["name"]
        herramienta = self.herramientas.get(nombre)
        if herramienta is None:
            return f"ERROR: no existe la herramienta {nombre}."
        try:
            args = json.loads(llamada["function"]["arguments"] or "{}")
            return str(herramienta(**args))
        except TypeError as e:
            return f"ERROR: argumentos no válidos para {nombre}: {e}"
        except Exception as e:  # los errores vuelven al modelo como texto
            return f"ERROR: {nombre} falló: {e}"

    def ejecutar(self, objetivo: str) -> str:
        mensajes = [{"role": "system", "content": self.instrucciones},
                    {"role": "user", "content": objetivo}]
        self.traza.evento("inicio", objetivo=objetivo, modelo=self.modelo.nombre,
                          herramientas=list(self.herramientas))
        for paso in range(1, self.max_pasos + 1):
            r = self.modelo.responder(mensajes, self.esquemas)
            for k in self.tokens:
                self.tokens[k] += r["uso"][k]
            mensaje = r["mensaje"]
            mensajes.append(mensaje)
            llamadas = mensaje.get("tool_calls") or []

            if not llamadas:
                informe = mensaje.get("content") or ""
                self.traza.evento("fin", paso=paso, informe=informe, tokens=self.tokens)
                return informe

            for llamada in llamadas:
                resultado = self._ejecutar(llamada)
                self.traza.evento(
                    "herramienta", paso=paso,
                    nombre=llamada["function"]["name"],
                    argumentos=llamada["function"]["arguments"],
                    resultado=resultado,
                    bloqueado=resultado.startswith("BLOQUEADO"),
                )
                mensajes.append({"role": "tool", "tool_call_id": llamada["id"],
                                 "content": resultado})

            if sum(self.tokens.values()) > self.max_tokens:
                return self._informe_de_cierre(mensajes, "tokens", paso,
                                               f"Superado el máximo de {self.max_tokens} tokens")

        return self._informe_de_cierre(mensajes, "pasos", self.max_pasos,
                                       f"Superado el máximo de {self.max_pasos} pasos")

    def _informe_de_cierre(self, mensajes, motivo, paso, aviso) -> str:
        """Última vuelta SIN herramientas para que siempre haya informe, aunque sea parcial."""
        self.traza.evento("limite", motivo=motivo, tokens=self.tokens)
        mensajes.append({"role": "user", "content": CIERRE.format(motivo=motivo)})
        try:
            r = self.modelo.responder(mensajes, [])
        except Exception as e:
            raise LimiteAlcanzado(f"{aviso} y el informe de cierre falló: {e}") from e
        for k in self.tokens:
            self.tokens[k] += r["uso"][k]
        informe = (r["mensaje"].get("content") or "").strip()
        if not informe or r["mensaje"].get("tool_calls"):
            raise LimiteAlcanzado(f"{aviso} y el modelo no redactó informe")
        self.traza.evento("fin", paso=paso + 1, informe=informe, tokens=self.tokens, parcial=True)
        return informe
