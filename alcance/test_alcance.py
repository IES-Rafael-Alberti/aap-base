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


@pytest.mark.parametrize("entrada, salida", [
    ("https://API.Empresa.com:443/login", "api.empresa.com"),
    ("empresa.com.", "empresa.com"),
    ("user:pass@host.empresa.com", "host.empresa.com"),
    ("[2001:db8::1]:443", "2001:db8::1"),
])
def test_normalizar(entrada, salida):
    assert normalizar(entrada) == salida
