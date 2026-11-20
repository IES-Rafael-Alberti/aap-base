"""El lanzador de la fase de enumeración: carpeta por ejecución e informe limpio."""

import sys
from pathlib import Path

RAIZ = Path(__file__).parents[1]
sys.path.insert(0, str(RAIZ))

import enumerar


def test_cada_ejecucion_en_su_carpeta(tmp_path, monkeypatch):
    monkeypatch.setattr(enumerar, "RAIZ", tmp_path)
    a, b = enumerar.nueva_carpeta(), enumerar.nueva_carpeta()
    assert a != b and a.parent == b.parent == tmp_path / "salida" / "ejecuciones"


def test_informe_empieza_por_el_titulo():
    texto = "Ahora tengo toda la información.\n\n---\n\n# Informe\n\nhola"
    assert enumerar.solo_informe(texto) == "# Informe\n\nhola\n"
    assert enumerar.solo_informe("sin título") == "sin título"
