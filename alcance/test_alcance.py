import pytest

from alcance import cargar, en_alcance, normalizar


@pytest.fixture
def scope(tmp_path):
    f = tmp_path / "scope.txt"
    f.write_text(
        "# Programa de ejemplo\n"
        "*.empresa.com\n"
        "!blog.empresa.com\n"
        "10.10.0.0/24\n"
        "!10.10.0.1\n"
        "192.168.56.20\n",
        encoding="utf-8",
    )
    return cargar(f)


# La batería de la Parte 2.1 del proyecto
@pytest.mark.parametrize("objetivo, esperado", [
    ("api.empresa.com", True),
    ("https://API.Empresa.com/login", True),
    ("blog.empresa.com", False),
    ("empresa.com", False),
    ("empresa.com.evil.net", False),
    ("otraempresa.com", False),
])
def test_dominios(scope, objetivo, esperado):
    assert en_alcance(objetivo, scope) is esperado


@pytest.mark.parametrize("objetivo, esperado", [
    ("10.10.0.7", True),
    ("http://10.10.0.7:8080/admin", True),
    ("10.10.0.1", False),        # excluida dentro del rango
    ("10.10.1.7", False),        # fuera del rango
    ("192.168.56.20", True),     # IP exacta
    ("192.168.56.21", False),
    ("", False),
])
def test_ips(scope, objetivo, esperado):
    assert en_alcance(objetivo, scope) is esperado


# Rangos pedidos (p. ej. por nmap): lo de tras la barra es el tamaño de la red
@pytest.mark.parametrize("objetivo, esperado", [
    ("10.10.0.128/25", True),    # .128–.255: cabe y no contiene la excluida
    ("10.10.0.0/24", False),     # cabe, pero contiene 10.10.0.1 (excluida)
    ("10.10.0.0/16", False),     # más grande que el alcance
    ("10.10.0.0/8", False),
    ("10.10.0.7/0", False),      # «todo internet»
    ("10.10.0.7/32", True),      # una sola IP dentro
    ("10.10.0.1/32", False),     # la excluida
    ("192.168.56.20/32", True),  # IP exacta autorizada
    ("192.168.56.0/24", False),  # solo .20 está autorizada
    ("10.10.0.0/99", False),     # rango mal escrito
    ("api.empresa.com/24", False),
    # formas raras de escribir un rango: todas fuera
    ("10.10.0.0/ 16", False),
    ("10.10.0.0/+16", False),
    ("10.10.0.0/16x", False),
    ("10.10.0.0/255.255.0.0", False),
    ("10.10.0.7/admin", False),  # IP con ruta sin esquema: ambigua, fuera
])
def test_rangos(scope, objetivo, esperado):
    assert en_alcance(objetivo, scope) is esperado


def test_rango_entero_sin_exclusiones(tmp_path):
    f = tmp_path / "scope.txt"
    f.write_text("172.17.0.0/24\n", encoding="utf-8")   # el del proyecto
    s = cargar(f)
    assert en_alcance("172.17.0.0/24", s) is True
    assert en_alcance("172.17.0.0/25", s) is True
    assert en_alcance("172.17.0.0/16", s) is False
    assert en_alcance("172.17.0.5/0", s) is False


@pytest.mark.parametrize("entrada, salida", [
    ("https://API.Empresa.com:443/login", "api.empresa.com"),
    ("empresa.com.", "empresa.com"),
    ("user:pass@host.empresa.com", "host.empresa.com"),
    ("[2001:db8::1]:443", "2001:db8::1"),
])
def test_normalizar(entrada, salida):
    assert normalizar(entrada) == salida
