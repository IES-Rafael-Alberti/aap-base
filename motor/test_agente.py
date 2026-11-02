"""Pruebas del motor con un modelo simulado: no gastan tokens ni salen a la red."""

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).parents[1]
for carpeta in ("alcance", "motor"):
    sys.path.insert(0, str(RAIZ / carpeta))

from agente import Agente, LimiteAlcanzado  # noqa: E402
from guard import protegida                 # noqa: E402
from traza import Traza                     # noqa: E402
from modelo import Modelo                   # noqa: E402

import os
import unittest
import uuid

SCOPE = (["*.empresa.com"], ["blog.empresa.com"])


@protegida(objetivo="dominio")
def eco(dominio: str) -> str:
    """Devuelve el dominio."""
    return f"ok {dominio}"


def sin_proteger(dominio: str) -> str:
    return dominio


class ModeloGuionizado:
    """Devuelve, en orden, las respuestas que le pasamos."""
    nombre = "simulado"

    def __init__(self, guion):
        self.guion = list(guion)

    def responder(self, mensajes, herramientas):
        return {"mensaje": self.guion.pop(0), "uso": {"entrada": 10, "salida": 5}}


def pide(nombre, **args):
    return {"role": "assistant", "content": None, "tool_calls": [{
        "id": f"c{len(args)}", "type": "function",
        "function": {"name": nombre, "arguments": json.dumps(args)}}]}


def responde(texto):
    return {"role": "assistant", "content": texto}


def agente(tmp_path, guion, **kw):
    return Agente(ModeloGuionizado(guion), "instrucciones", [eco], SCOPE,
                  Traza(tmp_path / "t.jsonl"), **kw)


def eventos(tmp_path):
    return [json.loads(l) for l in (tmp_path / "t.jsonl").read_text().splitlines()]


def test_rechaza_herramientas_sin_proteger(tmp_path):
    with pytest.raises(ValueError, match="no está protegida"):
        Agente(ModeloGuionizado([]), "", [sin_proteger], SCOPE, Traza(tmp_path / "t.jsonl"))


def test_ejecuta_en_alcance_y_bloquea_fuera(tmp_path):
    a = agente(tmp_path, [pide("eco", dominio="api.empresa.com"),
                          pide("eco", dominio="blog.empresa.com"),
                          responde("informe")])
    assert a.ejecutar("Investiga empresa.com") == "informe"
    llamadas = [e for e in eventos(tmp_path) if e["tipo"] == "herramienta"]
    assert llamadas[0]["resultado"] == "ok api.empresa.com"
    assert llamadas[1]["bloqueado"] is True


def test_limite_de_pasos(tmp_path):
    a = agente(tmp_path, [pide("eco", dominio="api.empresa.com")] * 5, max_pasos=3)
    with pytest.raises(LimiteAlcanzado):
        a.ejecutar("x")
    assert eventos(tmp_path)[-1] == {**eventos(tmp_path)[-1], "tipo": "limite", "motivo": "pasos"}


def test_herramienta_inexistente_vuelve_como_texto(tmp_path):
    a = agente(tmp_path, [pide("rm_rf", ruta="/"), responde("fin")])
    a.ejecutar("x")
    assert eventos(tmp_path)[1]["resultado"].startswith("ERROR: no existe")


class MarcaDeEjecucionTests(unittest.TestCase):
    """La marca agrupa en el gateway las vueltas de una misma ejecución; solo con la IA del aula."""

    def modelo(self, url):
        from unittest import mock
        with mock.patch.dict(os.environ, {"AAP_URL": url}):
            return Modelo("corsario-1", clave="sk-" + "x" * 20)

    def test_una_ejecucion_misma_marca_y_paso_creciente(self):
        m = self.modelo("http://10.30.0.6:4000/v1/chat/completions")
        inicio = [{"role": "system", "content": "i"}, {"role": "user", "content": "o"}]
        a = m._marca(inicio)["metadata"]["aap"]
        vuelta = inicio + [{"role": "assistant", "tool_calls": []}, {"role": "tool", "content": "r"}]
        b = m._marca(vuelta)["metadata"]["aap"]
        self.assertEqual((a["app"], a["version"], a["paso"], b["paso"]), ("corsario", 1, 1, 2))
        self.assertEqual(a["ejecucion"], b["ejecucion"])
        self.assertEqual(str(uuid.UUID(a["ejecucion"], version=4)), a["ejecucion"])
        self.assertEqual(m._marca(vuelta)["metadata"]["aap"]["paso"], 2)  # un reintento no avanza
        self.assertNotEqual(m._marca(inicio)["metadata"]["aap"]["ejecucion"], a["ejecucion"])  # otra ejecución

    def test_sin_marca_fuera_del_aula(self):
        m = self.modelo("https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(m._marca([{"role": "user", "content": "o"}]), {})
