import io
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.main import app


@pytest.fixture()
def cliente():
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


def test_processar_devolve_o_resumo(cliente, base_suja):
    resposta = cliente.post("/api/despesas/processar", files=_upload(base_suja))
    assert resposta.status_code == 200

    corpo = resposta.json()
    assert Decimal(str(corpo["total_geral"])) == Decimal("-11625.85")
    assert corpo["qtd_lancamentos"] == 11
    assert corpo["nome_arquivo"] == "base-suja.xlsx"
    assert corpo["avisos"]
    assert corpo["categorias"]


def test_baixar_xlsx_sem_reprocessar_pela_tela(cliente, base_suja):
    resposta = cliente.post("/api/despesas/xlsx", files=_upload(base_suja))
    assert resposta.status_code == 200
    assert "resumo-base-suja.xlsx" in resposta.headers["content-disposition"]
    assert resposta.content[:2] == b"PK"

    wb = load_workbook(io.BytesIO(resposta.content))
    ws = wb["Resumo"]
    assert ws.cell(row=ws.max_row, column=1).value == "TOTAL GERAL"
    assert Decimal(str(ws.cell(row=ws.max_row, column=2).value)) == Decimal("-11625.85")


def test_mesmo_arquivo_pode_subir_quantas_vezes_quiser(cliente, base_suja):
    """Não há trava de duplicado nem estado: o resultado é sempre idêntico."""
    respostas = [
        cliente.post("/api/despesas/processar", files=_upload(base_suja)) for _ in range(5)
    ]
    assert [r.status_code for r in respostas] == [200] * 5
    assert len({r.text for r in respostas}) == 1


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


def test_mapeamento_manual_sobrescreve_a_deteccao(cliente, base_suja):
    """Forçando a coluna Valor bruto (índice 4) em vez do Valor Líquido detectado."""
    resposta = cliente.post(
        "/api/despesas/processar",
        files=_upload(base_suja),
        data={"mapeamento": '{"valor": 4, "categoria": 8, "subcategoria": 9, "data": 0}'},
    )
    assert resposta.status_code == 200
    assert Decimal(str(resposta.json()["total_geral"])) == Decimal("-11625.85")


def test_mapeamento_invalido(cliente, base_suja):
    resposta = cliente.post(
        "/api/despesas/processar",
        files=_upload(base_suja),
        data={"mapeamento": "isto nao e json"},
    )
    assert resposta.status_code == 422
    assert "mapeamento" in resposta.json()["detail"].lower()


def test_categoria_concatenada_pela_api(cliente, base_categoria_concatenada):
    resposta = cliente.post(
        "/api/despesas/processar", files=_upload(base_categoria_concatenada, "junho.xlsx")
    )
    assert resposta.status_code == 200

    rotulos = [c["rotulo"] for c in resposta.json()["categorias"]]
    assert rotulos == ["CERTIDÕES", "DESPESA COM PESSOAL", "DESPESAS ADMINISTRATIVAS"]


def test_rotas_de_estado_nao_existem_mais(cliente):
    assert cliente.get("/api/despesas").status_code == 404
    assert cliente.get("/api/despesas/1").status_code == 404
    assert cliente.get("/api/despesas/comparar?a=1&b=2").status_code == 404


def test_saude(cliente):
    assert cliente.get("/api/saude").json() == {"status": "ok"}
