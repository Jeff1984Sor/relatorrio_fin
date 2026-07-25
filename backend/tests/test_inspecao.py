from app.services.inspecao import detectar_cabecalho, inspecionar, mapear_colunas
from app.services.leitura import ler_linhas


def test_detecta_cabecalho_fora_da_primeira_linha(base_suja):
    linhas, _aba = ler_linhas(base_suja, "base-suja.xlsx")
    indice, pontos = detectar_cabecalho(linhas)
    assert indice == 3  # linha 4 da planilha
    assert pontos > 0


def test_mapeamento_prefere_valor_liquido_sobre_valor_bruto(base_suja):
    linhas, _aba = ler_linhas(base_suja, "base-suja.xlsx")
    cabecalho = inspecionar(linhas)
    assert cabecalho.titulos[cabecalho.mapeamento.valor] == "Valor Líquido"
    assert cabecalho.titulos[cabecalho.mapeamento.categoria] == "Categoria"
    assert cabecalho.titulos[cabecalho.mapeamento.subcategoria] == "Subcategoria"
    assert cabecalho.titulos[cabecalho.mapeamento.data] == "Data de Pagamento"


def test_cai_para_valor_bruto_quando_nao_ha_liquido():
    mapa = mapear_colunas(["Data de Pagamento", "Valor bruto", "Categoria"])
    assert mapa.valor == 1


def test_cai_para_primeira_coluna_que_comeca_com_valor():
    mapa = mapear_colunas(["Categoria", "Valor Pago", "Valor Estimado"])
    assert mapa.valor == 1


def test_planilha_sem_coluna_de_subcategoria(base_sem_subcategoria):
    linhas, _aba = ler_linhas(base_sem_subcategoria, "sem-sub.xlsx")
    cabecalho = inspecionar(linhas)
    assert cabecalho.indice == 0
    assert cabecalho.mapeamento.subcategoria is None
    assert cabecalho.mapeamento.valor is not None
