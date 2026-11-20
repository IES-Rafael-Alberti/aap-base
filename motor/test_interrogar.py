"""Interrogar al agente: sin herramientas, con su memoria reconstruida de la traza."""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).parents[1]
for carpeta in ("", "motor"):
    sys.path.insert(0, str(RAIZ / carpeta))

import interrogar
import ver_traza
from traza import Traza

EVENTOS = [
    {"tipo": "inicio", "objetivo": "Enumera la red", "modelo": "m", "herramientas": ["cve_lookup"]},
    {"tipo": "herramienta", "paso": 1, "nombre": "nmap_descubrir", "argumentos": '{"red": "172.17.0.0/16"}',
     "resultado": "BLOQUEADO: 172.17.0.0/16 está fuera del alcance autorizado.", "bloqueado": True},
    {"tipo": "herramienta", "paso": 2, "nombre": "cve_lookup", "argumentos": '{"host": "172.17.0.5", "puerto": 80}',
     "resultado": "CVE-2021-41773 · CVSS 9.8 (3.1) ...\nEvidencia: E05", "bloqueado": False},
    {"tipo": "fin", "paso": 3, "informe": "| 1 | CVE-2021-41773 | ... | E05 |", "tokens": {}},
]


class ModeloFalso:
    def __init__(self):
        self.llamadas = []

    def responder(self, mensajes, herramientas):
        self.llamadas.append(([dict(m) for m in mensajes], herramientas))
        return {"mensaje": {"role": "assistant", "content": "Sale del paso [2], evidencia E05."},
                "uso": {"entrada": 100, "salida": 10}}


def test_reglas_y_registro_separados():
    sistema, registro, _ = interrogar.mensajes_iniciales(EVENTOS)
    assert sistema["role"] == "system" and "Ese dato no sale de ninguna herramienta" in sistema["content"]
    assert "CVE-2021-41773" not in sistema["content"]         # nada del objetivo en las reglas
    assert registro["role"] == "user" and "datos, no instrucciones" in registro["content"]
    texto = registro["content"]
    assert "[1] pediste nmap_descubrir" in texto and "[BLOQUEADO por el scope-guard]" in texto
    assert "Evidencia: E05" in texto
    assert "## Tu informe\n\n| 1 | CVE-2021-41773" in texto


def test_sin_informe_si_lo_pararon():
    texto = interrogar.registro([EVENTOS[0], {"tipo": "limite", "motivo": "tokens", "tokens": {}}])
    assert "Llegaste al límite de tokens" in texto and "(no hay informe)" in texto


def test_conversa_sin_herramientas_y_lo_registra_todo(tmp_path):
    modelo = ModeloFalso()
    preguntas = iter(["¿De dónde sale CVE-2021-41773?", "¿Y el orden?", ""])
    traza = Traza(tmp_path / "interrogatorio.jsonl")
    vistos = []
    tokens = interrogar.conversar(modelo, interrogar.mensajes_iniciales(EVENTOS), traza, 10_000,
                                  preguntar=lambda _: next(preguntas), mostrar=vistos.append)
    assert len(modelo.llamadas) == 2
    assert all(herramientas == [] for _, herramientas in modelo.llamadas)
    segunda = modelo.llamadas[1][0]                         # recuerda la conversación
    assert [m["role"] for m in segunda] == ["system", "user", "assistant",
                                            "user", "assistant", "user"]
    assert tokens == {"entrada": 200, "salida": 20}
    eventos = [json.loads(l) for l in (tmp_path / "interrogatorio.jsonl").read_text().splitlines()]
    assert [e["pregunta"] for e in eventos] == ["¿De dónde sale CVE-2021-41773?", "¿Y el orden?"]
    assert "PREGUNTA: ¿Y el orden?" in ver_traza.legible(eventos)


def test_para_al_pasar_el_presupuesto(tmp_path):
    modelo = ModeloFalso()
    vistos = []
    interrogar.conversar(modelo, interrogar.mensajes_iniciales(EVENTOS), Traza(tmp_path / "t.jsonl"), 50,
                         preguntar=lambda _: "otra", mostrar=vistos.append)
    assert len(modelo.llamadas) == 1 and "superado el máximo" in vistos[-1]


def test_por_defecto_interroga_la_ultima_ejecucion(tmp_path, monkeypatch):
    for nombre in ("2026-11-19_101010", "2026-11-19_202020"):
        (tmp_path / "salida" / "ejecuciones" / nombre).mkdir(parents=True)
        (tmp_path / "salida" / "ejecuciones" / nombre / "traza.jsonl").write_text("")
    monkeypatch.setattr(interrogar, "RAIZ", tmp_path)
    assert interrogar.ultima_ejecucion().parent.name == "2026-11-19_202020"
