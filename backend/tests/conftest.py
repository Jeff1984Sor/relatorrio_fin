import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import fixture_builder  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def caminho_base_suja() -> Path:
    caminho = FIXTURES / "base-suja.xlsx"
    if not caminho.exists():
        fixture_builder.construir(caminho)
    return caminho


@pytest.fixture(scope="session")
def base_suja(caminho_base_suja: Path) -> bytes:
    return caminho_base_suja.read_bytes()


@pytest.fixture(scope="session")
def base_sem_subcategoria(tmp_path_factory) -> bytes:
    destino = tmp_path_factory.mktemp("fixtures") / "sem-subcategoria.xlsx"
    fixture_builder.construir_sem_subcategoria(destino)
    return destino.read_bytes()
