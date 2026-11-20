"""probar.py: una herramienta a mano, con el scope-guard real y el scope.txt."""

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).parents[1]
sys.path.insert(0, str(RAIZ))

import probar


@pytest.fixture
def proyecto(tmp_path, monkeypatch):
    (tmp_path / "scope.txt").write_text("10.88.0.0/24\n", encoding="utf-8")
    monkeypatch.setattr(probar, "RAIZ", tmp_path)
    return tmp_path


def test_bloquea_una_red_mas_grande(proyecto, capsys):
    assert probar.main(["nmap_descubrir", "red=10.88.0.0/16"]).startswith("BLOQUEADO")


def test_dentro_llega_a_la_herramienta(proyecto):
    assert probar.main(["nmap_servicios", "host=10.88.0.20"]).startswith("PENDIENTE")


def test_convierte_el_puerto_a_numero(proyecto):
    import tus_herramientas_ud2 as t
    assert probar.argumentos(t.cve_lookup, ["host=10.88.0.20", "puerto=9200"]) == \
        {"host": "10.88.0.20", "puerto": 9200}


@pytest.mark.parametrize("args", [["host"], ["ip=10.88.0.20"]])
def test_argumentos_mal_escritos_explican_el_error(proyecto, args):
    with pytest.raises(SystemExit):
        probar.main(["nmap_servicios", *args])


def test_herramienta_inexistente(proyecto):
    with pytest.raises(SystemExit, match="No existe"):
        probar.main(["escanea_todo"])
