"""Herramientas iniciales: proceso y HTTP simulados, sin red ni tokens."""

import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

RAIZ = Path(__file__).parents[1]
for carpeta in ("", "alcance", "motor", "herramientas"):
    sys.path.insert(0, str(RAIZ / carpeta))

import guard
import lanzar
import tus_herramientas as tools
from prompt import construir


@pytest.fixture(autouse=True)
def scope(monkeypatch):
    monkeypatch.setattr(guard, "SCOPE", (["empresa.com", "*.empresa.com"], ["blog.empresa.com"]))


def test_tres_herramientas_disponibles_en_prompt_y_motor(tmp_path):
    assert [h.__name__ for h in lanzar.HERRAMIENTAS] == [
        "whois_dominio", "dns_registros", "subdominios_crtsh",
    ]
    instrucciones = construir("{alcance}\n{herramientas}", guard.SCOPE, lanzar.HERRAMIENTAS)
    agente = lanzar.Agente(object(), instrucciones, lanzar.HERRAMIENTAS, guard.SCOPE,
                          lanzar.Traza(tmp_path / "traza.jsonl"))
    assert len(agente.esquemas) == 3
    assert all(h.__name__ in instrucciones for h in lanzar.HERRAMIENTAS)


@pytest.mark.parametrize("herramienta", [tools.dns_registros, tools.subdominios_crtsh])
@pytest.mark.parametrize("dominio", ["otraempresa.com", "blog.empresa.com"])
def test_scope_bloquea_antes_de_cualquier_consulta(monkeypatch, herramienta, dominio):
    proceso = Mock(side_effect=AssertionError("No debe ejecutar un proceso"))
    http = Mock(side_effect=AssertionError("No debe acceder a la red"))
    monkeypatch.setattr(tools.subprocess, "run", proceso)
    monkeypatch.setattr(tools.urllib.request, "urlopen", http)
    assert herramienta(dominio=dominio).startswith("BLOQUEADO")
    proceso.assert_not_called()
    http.assert_not_called()


def test_dns_consulta_sin_shell_y_con_timeout(monkeypatch):
    proceso = Mock(return_value=subprocess.CompletedProcess([], 0, "ns1.empresa.com.\n", ""))
    monkeypatch.setattr(tools.subprocess, "run", proceso)
    assert tools.dns_registros(dominio="empresa.com", tipo="ns") == "ns1.empresa.com."
    proceso.assert_called_once_with(["dig", "+short", "NS", "empresa.com"],
                                    capture_output=True, text=True, timeout=20)


def test_dns_rechaza_tipo_no_permitido(monkeypatch):
    proceso = Mock()
    monkeypatch.setattr(tools.subprocess, "run", proceso)
    assert tools.dns_registros(dominio="empresa.com", tipo="AXFR").startswith("ERROR")
    proceso.assert_not_called()


@pytest.mark.parametrize("error", [FileNotFoundError("dig"), subprocess.TimeoutExpired("dig", 20)])
def test_dns_errores_como_texto(monkeypatch, error):
    monkeypatch.setattr(tools.subprocess, "run", Mock(side_effect=error))
    assert tools.dns_registros(dominio="empresa.com").startswith("ERROR")


def test_dns_no_confunde_error_del_proceso_con_ausencia_de_registros(monkeypatch):
    monkeypatch.setattr(tools.subprocess, "run", Mock(return_value=
                        subprocess.CompletedProcess([], 9, "", "consulta fallida")))
    assert "consulta fallida" in tools.dns_registros(dominio="empresa.com")


@pytest.mark.parametrize("salida", ["", "x" * 5000])
def test_dns_sin_registros_o_salida_recortada(monkeypatch, salida):
    monkeypatch.setattr(tools.subprocess, "run", Mock(return_value=
                        subprocess.CompletedProcess([], 0, salida, "")))
    resultado = tools.dns_registros(dominio="empresa.com")
    assert "Sin registros" in resultado if not salida else "recortado" in resultado


def test_crtsh_consulta_publica_deduplica_y_filtra(monkeypatch):
    datos = [{"name_value": "*.empresa.com\nAPI.empresa.com\napi.empresa.com"},
             {"name_value": "blog.empresa.com\notro.net\nwww.empresa.com"}]
    http = Mock(return_value=io.BytesIO(json.dumps(datos).encode()))
    monkeypatch.setattr(tools.urllib.request, "urlopen", http)
    resultado = tools.subdominios_crtsh(dominio="empresa.com")
    assert resultado.splitlines() == [
        "3 subdominios en alcance (2 filtrados por estar fuera):",
        "api.empresa.com", "empresa.com", "www.empresa.com",
    ]
    req = http.call_args.args[0]
    assert req.full_url == "https://crt.sh/?q=%25.empresa.com&output=json"
    assert http.call_args.kwargs == {"timeout": 90}


@pytest.mark.parametrize("datos", [[], [{"name_value": "x.empresa.com\ny.empresa.com"}]])
def test_crtsh_respeta_scope_sin_comodin(monkeypatch, datos):
    monkeypatch.setattr(guard, "SCOPE", (["empresa.com"], []))
    monkeypatch.setattr(tools.urllib.request, "urlopen", Mock(return_value=
                        io.BytesIO(json.dumps(datos).encode())))
    resultado = tools.subdominios_crtsh(dominio="empresa.com")
    assert resultado.startswith("0 subdominios en alcance")
    assert "x.empresa.com" not in resultado


@pytest.mark.parametrize("contenido", [b"<html>error</html>", b'{}', b'[null]', b'[{"name_value": null}]'])
def test_crtsh_respuesta_invalida_como_texto(monkeypatch, contenido):
    monkeypatch.setattr(tools.urllib.request, "urlopen", Mock(return_value=io.BytesIO(contenido)))
    assert tools.subdominios_crtsh(dominio="empresa.com").startswith("ERROR")


def test_crtsh_caido_sin_recomendar_herramienta_inexistente(monkeypatch):
    monkeypatch.setattr(tools.urllib.request, "urlopen", Mock(side_effect=TimeoutError("agotado")))
    resultado = tools.subdominios_crtsh(dominio="empresa.com")
    assert resultado.startswith("ERROR")
    assert "subdominios_subfinder" not in resultado


def test_crtsh_recorta_resultados_largos(monkeypatch):
    datos = [{"name_value": "\n".join(f"host{i:04}.empresa.com" for i in range(1000))}]
    monkeypatch.setattr(tools.urllib.request, "urlopen", Mock(return_value=
                        io.BytesIO(json.dumps(datos).encode())))
    assert "recortado" in tools.subdominios_crtsh(dominio="empresa.com")
