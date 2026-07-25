from app.services.texto import chave_agrupamento, chave_ordenacao, normalizar

VARIANTES_GUIAS = [
    "Guias / Custas Judiciais",
    "Guias/Custas Judiciais",
    "GUIAS / CUSTAS JUDICIAIS",
]


def test_tres_variantes_de_guias_caem_na_mesma_chave():
    chaves = {chave_agrupamento(v) for v in VARIANTES_GUIAS}
    assert chaves == {"guias/custas judiciais"}


def test_normalizar_tira_acento_caixa_e_espaco_repetido():
    assert normalizar("  DESPESAS   NÃO   REEMBOLSÁVEIS ") == "despesas nao reembolsaveis"


def test_chave_agrupamento_tambem_colapsa_em_volta_do_hifen():
    assert chave_agrupamento("Multa - Juros") == chave_agrupamento("Multa-Juros")


def test_ordenacao_ptbr_poe_a_com_acento_antes_de_b():
    rotulos = ["Bônus", "Água e Luz", "Aluguel"]
    assert sorted(rotulos, key=chave_ordenacao) == ["Água e Luz", "Aluguel", "Bônus"]
