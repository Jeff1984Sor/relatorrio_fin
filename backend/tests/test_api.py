import os
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    """App isolado: banco e arquivos vão para um diretório temporário."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "arquivos"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'teste.db'}")

    for modulo in [m for m in list(os.sys.modules) if m.startswith("app")]:
        del os.sys.modules[modulo]

    from app.main import app

    with TestClient(app) as cliente:
        yield cliente


def _upload(conteudo: bytes, nome: str = "base-suja.xlsx"):
    return {
        "arquivo": (
            nome,
            conteudo,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def test_inspecionar_devolve_mapeamento_e_amostra(cliente, base_suja):
    resposta = cliente.post("/api/despesas/inspecionar", files=_upload(base_suja))
    assert resposta.status_code == 200

    corpo = resposta.json()
    assert corpo["linha_cabecalho"] == 3
    assert corpo["colunas"][7] == "Valor Líquido"
    assert corpo["mapeamento"]["valor"] == 7
    assert len(corpo["amostra"]) == 10
    assert corpo["ja_processado_id"] is None


def test_fluxo_completo_processar_e_baixar(cliente, base_suja):
    resposta = cliente.post("/api/despesas/processar", files=_upload(base_suja))
    assert resposta.status_code == 200

    corpo = resposta.json()
    assert Decimal(str(corpo["total_geral"])) == Decimal("-11625.85")
    assert corpo["qtd_lancamentos"] == 11
    assert corpo["avisos"]

    processamento_id = corpo["processamento_id"]

    salvo = cliente.get(f"/api/despesas/{processamento_id}")
    assert salvo.status_code == 200
    assert Decimal(str(salvo.json()["total_geral"])) == Decimal("-11625.85")

    xlsx = cliente.get(f"/api/despesas/{processamento_id}/xlsx")
    assert xlsx.status_code == 200
    assert "resumo-base-suja.xlsx" in xlsx.headers["content-disposition"]
    assert xlsx.content[:2] == b"PK"


def test_arquivo_repetido_avisa_em_vez_de_duplicar(cliente, base_suja):
    primeiro = cliente.post("/api/despesas/processar", files=_upload(base_suja))
    anterior_id = primeiro.json()["processamento_id"]

    repetido = cliente.post("/api/despesas/processar", files=_upload(base_suja))
    assert repetido.status_code == 409
    assert repetido.json()["detail"]["processamento_id"] == anterior_id

    inspecao = cliente.post("/api/despesas/inspecionar", files=_upload(base_suja))
    assert inspecao.json()["ja_processado_id"] == anterior_id

    forcado = cliente.post(
        "/api/despesas/processar", files=_upload(base_suja), data={"forcar": "true"}
    )
    assert forcado.status_code == 200


def test_arquivo_corrompido_retorna_422_em_portugues_sem_traceback(cliente):
    resposta = cliente.post(
        "/api/despesas/processar", files=_upload(b"isto nao e uma planilha", "quebrado.xlsx")
    )
    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert "Traceback" not in detalhe
    assert detalhe.startswith("Não foi possível ler o arquivo")


def test_extensao_nao_aceita(cliente):
    resposta = cliente.post("/api/despesas/processar", files=_upload(b"abc", "foto.png"))
    assert resposta.status_code == 422
    assert "não é aceito" in resposta.json()["detail"]


def test_historico_e_comparacao(cliente, base_suja, base_sem_subcategoria):
    a = cliente.post("/api/despesas/processar", files=_upload(base_suja)).json()
    b = cliente.post(
        "/api/despesas/processar", files=_upload(base_sem_subcategoria, "limpa.xlsx")
    ).json()

    historico = cliente.get("/api/despesas").json()
    assert historico["total"] == 2
    assert historico["itens"][0]["id"] == b["processamento_id"]

    comparacao = cliente.get(
        "/api/despesas/comparar",
        params={"a": a["processamento_id"], "b": b["processamento_id"]},
    )
    assert comparacao.status_code == 200
    corpo = comparacao.json()
    assert Decimal(str(corpo["variacao"])) == Decimal("-3000.00") - Decimal("-11625.85")
    assert corpo["categorias"]


def test_processamento_inexistente(cliente):
    assert cliente.get("/api/despesas/9999").status_code == 404


def test_mapeamento_manual_sobrescreve_a_deteccao(cliente, base_suja):
    """Forçando a coluna Valor bruto (índice 4) o total deve mudar de coluna."""
    resposta = cliente.post(
        "/api/despesas/processar",
        files=_upload(base_suja),
        data={"mapeamento": '{"valor": 4, "categoria": 8, "subcategoria": 9, "data": 0}'},
    )
    assert resposta.status_code == 200
    assert resposta.json()["opcoes"]["mapeamento"]["valor"] == 4
