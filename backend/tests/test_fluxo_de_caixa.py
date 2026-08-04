"""Formato 'Fluxo de Caixa' — Débito/Crédito, categoria concatenada, várias contas."""

from decimal import Decimal

from app.services.agregacao import CATEGORIA_FOLHA, extrair_linhas, montar_resumo
from app.services.inspecao import inspecionar
from app.services.leitura import ler_linhas
from tests.fixture_builder import QTD_FLUXO_ESPERADA, TOTAL_FLUXO_ESPERADO


def _processar(conteudo: bytes, nome: str = "fluxo.xlsx"):
    linhas, _aba = ler_linhas(conteudo, nome)
    cabecalho = inspecionar(linhas)
    detalhes, avisos = extrair_linhas(linhas, cabecalho.indice, cabecalho.mapeamento, nome_arquivo=nome)
    return montar_resumo(detalhes, avisos), detalhes


def test_cabecalho_e_mapeamento(fluxo_de_caixa):
    linhas, _aba = ler_linhas(fluxo_de_caixa, "fluxo.xlsx")
    cabecalho = inspecionar(linhas)

    assert cabecalho.indice == 8  # linha 9 da planilha
    mapa = cabecalho.mapeamento
    assert cabecalho.titulos[mapa.valor] == "Débito"
    assert cabecalho.titulos[mapa.categoria] == "Categoria / Subcategoria"
    assert cabecalho.titulos[mapa.conta] == "Banco/Conta Financeira"
    assert cabecalho.titulos[mapa.fornecedor] == "Fornecedor"
    # Não há coluna separada de subcategoria: ela sai da própria categoria.
    assert mapa.subcategoria is None
    assert mapa.somente_preenchidos is True


def test_so_entram_as_linhas_com_debito_preenchido(fluxo_de_caixa):
    resumo, _detalhes = _processar(fluxo_de_caixa)

    assert resumo.qtd_lancamentos == QTD_FLUXO_ESPERADA
    assert resumo.total_geral == Decimal(TOTAL_FLUXO_ESPERADO)

    # Os créditos (Honorários Recebidos) não podem aparecer em lugar nenhum.
    rotulos = {c.rotulo for c in resumo.categorias}
    assert "Honorários Recebidos" not in rotulos


def test_credito_nao_vira_aviso_de_erro(fluxo_de_caixa):
    resumo, _detalhes = _processar(fluxo_de_caixa)
    tipos = {a.tipo for a in resumo.avisos}

    assert "sem_debito" in tipos
    assert "valor_invalido" not in tipos

    aviso = next(a for a in resumo.avisos if a.tipo == "sem_debito")
    assert aviso.quantidade == 2


def test_categoria_com_tabulacao_e_espaco_antes_dos_dois_pontos(fluxo_de_caixa):
    resumo, _detalhes = _processar(fluxo_de_caixa)

    pessoal = next(c for c in resumo.categorias if c.chave == "despesas com pessoal")
    assert pessoal.rotulo == "Despesas com Pessoal"

    operacionais = next(c for c in resumo.categorias if c.chave == "despesas operacionais")
    assert [s.rotulo for s in operacionais.subcategorias] == [
        "Cursos e treinamentos",
        "Serviços contábeis",
        "Taxas bancárias",
    ]


def test_folha_sem_categoria_agrupa_com_o_beneficiario_como_subcategoria(fluxo_de_caixa):
    resumo, _detalhes = _processar(fluxo_de_caixa)

    pessoal = next(c for c in resumo.categorias if c.chave == "despesas com pessoal")
    subs = {s.rotulo: s.total for s in pessoal.subcategorias}

    assert subs["Aline Garbin"] == Decimal("-6603")
    assert subs["Lucas Caramés"] == Decimal("-3621")
    # As linhas que já tinham categoria continuam com a subcategoria da planilha.
    assert subs["Plano de saúde"] == Decimal("-1377.84")

    aviso = next(a for a in resumo.avisos if a.tipo == "folha_sem_categoria")
    assert aviso.quantidade == 1
    assert CATEGORIA_FOLHA.upper() in aviso.mensagem.upper()


def test_transferencia_entra_como_categoria_propria(fluxo_de_caixa):
    resumo, _detalhes = _processar(fluxo_de_caixa)

    transferencia = next(c for c in resumo.categorias if "transferencia" in c.chave)
    assert transferencia.total == Decimal("-40000")
    assert [s.rotulo for s in transferencia.subcategorias] == ["Investimentos"]


def test_totais_por_conta_bancaria(fluxo_de_caixa):
    resumo, _detalhes = _processar(fluxo_de_caixa)

    assert resumo.contas == ["Banco Bradesco", "Banco Itaú"]
    assert resumo.total_por_conta["Banco Bradesco"] == Decimal("-220")
    assert resumo.total_por_conta["Banco Itaú"] == Decimal("-53440.93")
    assert sum(resumo.total_por_conta.values()) == resumo.total_geral

    operacionais = next(c for c in resumo.categorias if c.chave == "despesas operacionais")
    assert operacionais.por_conta["Banco Bradesco"] == Decimal("-220")
    assert sum(operacionais.por_conta.values()) == operacionais.total


def test_conta_unica_nao_gera_coluna_por_conta(fluxo_conta_unica):
    resumo, _detalhes = _processar(fluxo_conta_unica)
    assert resumo.contas == ["Banco Itaú"]
    assert resumo.total_geral == Decimal(TOTAL_FLUXO_ESPERADO)


def test_periodo_vem_da_coluna_data(fluxo_de_caixa):
    resumo, _detalhes = _processar(fluxo_de_caixa)
    assert resumo.periodo_inicio.isoformat() == "2026-06-01"
    assert resumo.periodo_fim.isoformat() == "2026-06-12"


def test_detalhe_guarda_conta_e_arquivo_de_origem(fluxo_de_caixa):
    _resumo, detalhes = _processar(fluxo_de_caixa, nome="fluxo-junho.xlsx")
    assert {d.arquivo for d in detalhes} == {"fluxo-junho.xlsx"}
    assert {d.conta for d in detalhes} == {"Banco Itaú", "Banco Bradesco"}
