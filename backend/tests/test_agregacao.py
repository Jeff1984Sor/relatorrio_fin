from decimal import Decimal

from app.services.agregacao import (
    ORDEM_VALOR,
    SEM_CATEGORIA,
    SEM_SUBCATEGORIA,
    extrair_linhas,
    montar_resumo,
)
from app.services.inspecao import inspecionar
from app.services.leitura import ler_linhas
from tests.fixture_builder import QTD_ESPERADA, TOTAL_ESPERADO


def _processar(conteudo: bytes, unificar: bool = True, ordem: str = "alfabetica"):
    linhas, _aba = ler_linhas(conteudo, "base.xlsx")
    cabecalho = inspecionar(linhas)
    detalhes, avisos = extrair_linhas(linhas, cabecalho.indice, cabecalho.mapeamento, unificar)
    return montar_resumo(detalhes, avisos, ordem)


def test_invariante_principal_soma_do_resumo_bate_com_a_base(base_suja):
    """Se este teste falhar, nada mais importa."""
    resumo = _processar(base_suja)

    soma_categorias = sum((c.total for c in resumo.categorias), Decimal("0"))
    soma_subcategorias = sum(
        (s.total for c in resumo.categorias for s in c.subcategorias), Decimal("0")
    )

    assert resumo.total_geral == Decimal(TOTAL_ESPERADO)
    assert soma_categorias == Decimal(TOTAL_ESPERADO)
    assert soma_subcategorias == Decimal(TOTAL_ESPERADO)
    assert resumo.qtd_lancamentos == QTD_ESPERADA


def test_guias_custas_judiciais_vira_uma_linha_so(base_suja):
    resumo = _processar(base_suja)
    administrativas = next(
        c for c in resumo.categorias if c.chave == "despesas administrativas"
    )
    guias = [s for s in administrativas.subcategorias if s.chave == "guias/custas judiciais"]

    assert len(guias) == 1
    assert guias[0].qtd == 3
    assert guias[0].total == Decimal("-2485.06")


def test_rotulo_exibido_e_a_variante_mais_frequente(base_suja):
    resumo = _processar(base_suja)
    administrativas = next(
        c for c in resumo.categorias if c.chave == "despesas administrativas"
    )
    # "DESPESAS ADMINISTRATIVAS" aparece 3x contra 1x de "Despesas Administrativas".
    assert administrativas.rotulo == "DESPESAS ADMINISTRATIVAS"


def test_sem_unificacao_as_variantes_se_separam(base_suja):
    resumo = _processar(base_suja, unificar=False)
    subcategorias = [s.rotulo for c in resumo.categorias for s in c.subcategorias]
    guias = [s for s in subcategorias if "uias" in s or "UIAS" in s]
    assert len(guias) == 3


def test_categoria_e_subcategoria_vazias_recebem_rotulo_proprio(base_suja):
    resumo = _processar(base_suja)
    chaves = {c.rotulo for c in resumo.categorias}
    assert SEM_CATEGORIA in chaves

    financeiras = next(c for c in resumo.categorias if c.chave == "despesas financeiras")
    assert SEM_SUBCATEGORIA in {s.rotulo for s in financeiras.subcategorias}


def test_linha_com_valor_vazio_vira_aviso_e_fica_fora_do_total(base_suja):
    resumo = _processar(base_suja)
    aviso = next(a for a in resumo.avisos if a.tipo == "valor_invalido")
    assert aviso.quantidade == 1
    assert aviso.detalhes == [10]  # linha 10 da planilha


def test_avisos_de_conferencia(base_suja):
    resumo = _processar(base_suja)
    tipos = {a.tipo for a in resumo.avisos}
    assert "sem_categoria" in tipos
    assert "subcategoria_com_ponto_virgula" in tipos

    ponto_virgula = next(a for a in resumo.avisos if a.tipo == "subcategoria_com_ponto_virgula")
    assert ponto_virgula.detalhes == ["BPO Financeiro; DESPESAS ADMINISTRATIVAS"]


def test_percentuais(base_suja):
    resumo = _processar(base_suja)
    for categoria in resumo.categorias:
        soma_sub = sum(s.percentual for s in categoria.subcategorias)
        assert abs(soma_sub - 1.0) < 1e-9
    soma_cat = sum(c.percentual for c in resumo.categorias)
    assert abs(soma_cat - 1.0) < 1e-9


def test_ordenacao_alfabetica_ptbr(base_suja):
    resumo = _processar(base_suja)
    pessoal = next(c for c in resumo.categorias if c.chave == "despesa com pessoal")
    assert [s.rotulo for s in pessoal.subcategorias] == ["Água e Luz", "Bônus"]


def test_ordenacao_por_maior_valor_absoluto(base_suja):
    resumo = _processar(base_suja, ordem=ORDEM_VALOR)
    totais = [abs(c.total) for c in resumo.categorias]
    assert totais == sorted(totais, reverse=True)


def test_periodo_vem_das_datas_de_pagamento(base_suja):
    resumo = _processar(base_suja)
    assert resumo.periodo_inicio.isoformat() == "2026-01-05"
    assert resumo.periodo_fim.isoformat() == "2026-01-16"


def test_planilha_sem_subcategoria_agrupa_em_sem_subcategoria(base_sem_subcategoria):
    resumo = _processar(base_sem_subcategoria)
    assert resumo.total_geral == Decimal("-3000.00")
    for categoria in resumo.categorias:
        assert [s.rotulo for s in categoria.subcategorias] == [SEM_SUBCATEGORIA]
