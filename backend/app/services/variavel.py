"""Relatório de remuneração variável.

Cruza o cubo de recebimentos com o relatório de casos e calcula, por lançamento:

    Valor dos Impostos = Valor Pago × alíquota
    Valor Líquido      = Valor Pago − Valor dos Impostos
    Variável           = Valor Líquido × Participação do responsável

O NH nunca se repete para o mesmo responsável: sai **uma linha por recebimento
e responsável**. Quando um recebimento cobre vários casos, o valor é dividido
entre os responsáveis na proporção de casos de cada um — quem tem 29 dos 33
casos leva 29/33 do valor. Assim ninguém fica sem a sua parte e o total do
recebimento é preservado, sem repetir o mesmo dinheiro em várias linhas.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from .texto import chave_ordenacao, normalizar
from .valores import parse_data, parse_valor, texto_celula

ALIQUOTA_PADRAO = Decimal("0.175")
CENTAVO = Decimal("0.01")

BRANCO = "(blank)"
LINHAS_VARRIDAS = 20

# O cubo é exportado sem cabeçalho, sempre na mesma ordem de colunas.
COLUNAS_CUBO_PADRAO = {
    "nh": 0,
    "pagador": 1,
    "cliente": 2,
    "grupo": 3,
    "nf": 4,
    "situacao": 5,
    "valor_bruto": 6,
    "data_vencimento": 7,
    "data_pagamento": 8,
    "valor_pago": 9,
    "numero_do_caso": 10,
}

TITULOS_CUBO = {
    "nh": ("nh",),
    "pagador": ("pagador",),
    "cliente": ("cliente",),
    "grupo": ("grupo",),
    "nf": ("nf",),
    "situacao": ("situacao",),
    "valor_bruto": ("valor bruto",),
    "data_vencimento": ("data de vencimento",),
    "data_pagamento": ("data de pagamento",),
    "valor_pago": ("valor pago",),
    "numero_do_caso": ("numero do caso",),
}

TITULOS_CASOS = {
    "numero_do_caso": ("numero do caso",),
    "titulo": ("titulo",),
    "responsavel": ("responsavel",),
    "participacao": ("participacao",),
    # Coluna opcional: se o relatório de casos não tiver Área, sai em branco.
    "area": ("area",),
}


class ArquivoInesperado(Exception):
    """Mensagem pronta para a tela quando o arquivo não tem o formato esperado."""


@dataclass
class Caso:
    numero: int
    titulo: str
    responsavel: str
    participacao: Decimal
    area: str = ""


@dataclass
class LinhaVariavel:
    grupo: str
    pagador: str
    cliente: str
    nh: str
    nf: str
    situacao: str
    data_vencimento: dt.date | None
    data_pagamento: dt.date | None
    numero_do_caso: int | None
    titulo: str
    responsavel: str
    area: str
    valor_bruto: Decimal
    valor_pago: Decimal
    aliquota: Decimal
    valor_dos_impostos: Decimal
    valor_liquido: Decimal
    participacao: Decimal | None
    variavel: Decimal
    casos_do_responsavel: int = 1
    casos_no_recebimento: int = 1


@dataclass
class Aviso:
    tipo: str
    mensagem: str
    quantidade: int = 0
    detalhes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "mensagem": self.mensagem,
            "quantidade": self.quantidade,
            "detalhes": self.detalhes,
        }


@dataclass
class ResumoVariavel:
    linhas: list[LinhaVariavel]
    aliquota: Decimal
    total_pago: Decimal
    total_liquido: Decimal
    total_variavel: Decimal
    por_responsavel: dict[str, Decimal]
    periodo_inicio: dt.date | None
    periodo_fim: dt.date | None
    avisos: list[Aviso]
    arquivos: list[str] = field(default_factory=list)


def limpar(bruto: object) -> str:
    """Texto da célula, tratando `(Blank)` do cubo como vazio."""
    texto = texto_celula(bruto)
    return "" if normalizar(texto) == BRANCO else texto


def parse_valor_cubo(bruto: object) -> Decimal | None:
    """O cubo exporta valores como texto: `valor: 3000.00`."""
    if isinstance(bruto, str):
        texto = limpar(bruto)
        if not texto:
            return None
        texto = re.sub(r"(?i)^\s*valor\s*:\s*", "", texto)
        return parse_valor(texto)
    return parse_valor(bruto)


def parse_numero_do_caso(bruto: object) -> int | None:
    texto = limpar(bruto)
    if not texto:
        return None
    try:
        return int(float(texto.replace(",", ".")))
    except ValueError:
        return None


def somente_digitos(bruto: object) -> str:
    return re.sub(r"\D", "", texto_celula(bruto))


def _casar_titulos(linha: list[object], titulos: dict[str, tuple[str, ...]]) -> dict[str, int]:
    """Mapa campo → índice, comparando o texto normalizado do cabeçalho."""
    encontrados: dict[str, int] = {}
    for indice, celula in enumerate(linha):
        texto = normalizar(celula)
        for campo, aceitos in titulos.items():
            if campo not in encontrados and texto in aceitos:
                encontrados[campo] = indice
    return encontrados


def mapear_cubo(linhas: list[list[object]]) -> tuple[dict[str, int], int]:
    """Devolve (mapa de colunas, índice da primeira linha de dados).

    O cubo normalmente vem sem cabeçalho — nesse caso vale a ordem fixa das
    colunas. Se alguém exportar com cabeçalho, ele é reconhecido e usado.
    """
    for indice, linha in enumerate(linhas[:LINHAS_VARRIDAS]):
        encontrados = _casar_titulos(linha, TITULOS_CUBO)
        if len(encontrados) >= 6:
            return encontrados, indice + 1
    return dict(COLUNAS_CUBO_PADRAO), 0


def mapear_casos(linhas: list[list[object]]) -> tuple[dict[str, int], int]:
    for indice, linha in enumerate(linhas[:LINHAS_VARRIDAS]):
        encontrados = _casar_titulos(linha, TITULOS_CASOS)
        if "numero_do_caso" in encontrados and "responsavel" in encontrados:
            return encontrados, indice + 1
    raise ArquivoInesperado(
        "Não encontrei as colunas do relatório de casos. Ele precisa ter "
        "Número do Caso, Título, Responsável e Participação."
    )


def _celula(linha: list[object], mapa: dict[str, int], campo: str) -> object:
    indice = mapa.get(campo)
    if indice is None or indice >= len(linha):
        return None
    return linha[indice]


def ler_casos(linhas: list[list[object]]) -> dict[int, Caso]:
    mapa, inicio = mapear_casos(linhas)
    casos: dict[int, Caso] = {}

    for linha in linhas[inicio:]:
        numero = parse_numero_do_caso(_celula(linha, mapa, "numero_do_caso"))
        if numero is None:
            continue
        participacao = parse_valor(_celula(linha, mapa, "participacao"))
        casos[numero] = Caso(
            numero=numero,
            titulo=limpar(_celula(linha, mapa, "titulo")),
            responsavel=limpar(_celula(linha, mapa, "responsavel")),
            participacao=participacao if participacao is not None else Decimal("0"),
            area=limpar(_celula(linha, mapa, "area")),
        )
    if not casos:
        raise ArquivoInesperado(
            "O relatório de casos não tem nenhuma linha com número de caso válido."
        )
    return casos


@dataclass
class _Recebimento:
    """Uma linha do cubo, antes do rateio entre os casos."""

    ordem: int
    nh: str
    dados: dict[str, object]
    numero_do_caso: int | None


def _agrupar_por_nh(linhas: list[list[object]], mapa: dict[str, int], inicio: int):
    recebimentos: dict[str, list[_Recebimento]] = defaultdict(list)
    ordem_nh: list[str] = []

    for posicao, linha in enumerate(linhas[inicio:]):
        nh = limpar(_celula(linha, mapa, "nh"))
        valor_pago = parse_valor_cubo(_celula(linha, mapa, "valor_pago"))
        if not nh and valor_pago is None:
            continue

        chave = somente_digitos(nh) or nh
        if chave not in recebimentos:
            ordem_nh.append(chave)

        recebimentos[chave].append(
            _Recebimento(
                ordem=posicao,
                nh=nh,
                dados={campo: _celula(linha, mapa, campo) for campo in mapa},
                numero_do_caso=parse_numero_do_caso(_celula(linha, mapa, "numero_do_caso")),
            )
        )
    return recebimentos, ordem_nh


def _ratear(valor: Decimal, pesos: list[int]) -> list[Decimal]:
    """Divide `valor` na proporção de `pesos`, em centavos exatos.

    A sobra da divisão é distribuída um centavo por vez, começando pelos maiores
    pesos, então a soma das fatias é sempre igual ao valor original — nenhum
    centavo é criado nem perdido.
    """
    if len(pesos) <= 1:
        return [valor]

    total_pesos = sum(pesos)
    if total_pesos == 0:
        return [Decimal("0") for _ in pesos]

    centavos = int((valor * 100).to_integral_value(rounding="ROUND_HALF_UP"))
    sinal = -1 if centavos < 0 else 1
    absolutos = abs(centavos)

    fatias = [absolutos * peso // total_pesos for peso in pesos]
    sobra = absolutos - sum(fatias)

    # Quem tem mais casos recebe o centavo que sobrou; empate resolvido pela ordem.
    for indice in sorted(range(len(pesos)), key=lambda i: (-pesos[i], i))[:sobra]:
        fatias[indice] += 1

    return [Decimal(sinal * fatia) / 100 for fatia in fatias]


def montar(
    linhas_cubo: list[list[object]],
    linhas_casos: list[list[object]],
    aliquota: Decimal = ALIQUOTA_PADRAO,
    arquivos: list[str] | None = None,
) -> ResumoVariavel:
    casos = ler_casos(linhas_casos)
    mapa, inicio = mapear_cubo(linhas_cubo)
    recebimentos, ordem_nh = _agrupar_por_nh(linhas_cubo, mapa, inicio)

    resultado: list[LinhaVariavel] = []
    sem_caso: list[str] = []
    caso_nao_encontrado: set[int] = set()
    rateados: list[str] = []

    for chave in ordem_nh:
        grupo = recebimentos[chave]
        base = grupo[0]
        valor_pago = parse_valor_cubo(base.dados.get("valor_pago")) or Decimal("0")
        valor_bruto = parse_valor_cubo(base.dados.get("valor_bruto")) or Decimal("0")

        # Um responsável por linha: os casos dele no recebimento viram o peso.
        por_responsavel: dict[str, list[Caso]] = {}
        ordem_responsavel: list[str] = []
        for recebimento in grupo:
            if recebimento.numero_do_caso is None:
                sem_caso.append(recebimento.nh)
                continue
            caso = casos.get(recebimento.numero_do_caso)
            if caso is None:
                caso_nao_encontrado.add(recebimento.numero_do_caso)
                continue
            if caso.responsavel not in por_responsavel:
                por_responsavel[caso.responsavel] = []
                ordem_responsavel.append(caso.responsavel)
            por_responsavel[caso.responsavel].append(caso)

        if not por_responsavel:
            # Recebimento sem nenhum caso identificado: entra na tabela para o
            # total bater, mas sem responsável e sem variável.
            resultado.append(
                _linha(base, None, None, valor_bruto, valor_pago, aliquota, 0, 1)
            )
            continue

        pesos = [len(por_responsavel[r]) for r in ordem_responsavel]
        if len(ordem_responsavel) > 1 or pesos[0] > 1:
            rateados.append(
                f"{base.nh}: {sum(pesos)} casos entre {len(ordem_responsavel)} responsável(is)"
            )

        fatias_pagas = _ratear(valor_pago, pesos)
        fatias_brutas = _ratear(valor_bruto, pesos)

        for indice, responsavel in enumerate(ordem_responsavel):
            casos_do_responsavel = por_responsavel[responsavel]
            resultado.append(
                _linha(
                    base,
                    casos_do_responsavel[0],
                    responsavel,
                    fatias_brutas[indice],
                    fatias_pagas[indice],
                    aliquota,
                    len(casos_do_responsavel),
                    sum(pesos),
                )
            )

    return _resumir(resultado, aliquota, sem_caso, caso_nao_encontrado, rateados, arquivos or [])


def _linha(
    recebimento: _Recebimento,
    caso: Caso | None,
    responsavel: str | None,
    valor_bruto: Decimal,
    valor_pago: Decimal,
    aliquota: Decimal,
    casos_do_responsavel: int,
    casos_no_recebimento: int,
) -> LinhaVariavel:
    impostos = (valor_pago * aliquota).quantize(CENTAVO)
    liquido = valor_pago - impostos
    participacao = caso.participacao if caso else None
    variavel = (
        (liquido * participacao).quantize(CENTAVO) if participacao is not None else Decimal("0")
    )

    return LinhaVariavel(
        grupo=limpar(recebimento.dados.get("grupo")),
        pagador=limpar(recebimento.dados.get("pagador")),
        cliente=limpar(recebimento.dados.get("cliente")),
        nh=recebimento.nh,
        nf=limpar(recebimento.dados.get("nf")),
        situacao=limpar(recebimento.dados.get("situacao")),
        data_vencimento=parse_data(limpar(recebimento.dados.get("data_vencimento"))),
        data_pagamento=parse_data(limpar(recebimento.dados.get("data_pagamento"))),
        numero_do_caso=caso.numero if caso else None,
        titulo=caso.titulo if caso else "",
        responsavel=responsavel or "",
        area=caso.area if caso else "",
        valor_bruto=valor_bruto,
        valor_pago=valor_pago,
        aliquota=aliquota,
        valor_dos_impostos=impostos,
        valor_liquido=liquido,
        participacao=participacao,
        variavel=variavel,
        casos_do_responsavel=casos_do_responsavel,
        casos_no_recebimento=casos_no_recebimento,
    )


def _resumir(
    linhas: list[LinhaVariavel],
    aliquota: Decimal,
    sem_caso: list[str],
    caso_nao_encontrado: set[int],
    rateados: list[str],
    arquivos: list[str],
) -> ResumoVariavel:
    por_responsavel: dict[str, Decimal] = {}
    for linha in linhas:
        if not linha.responsavel:
            continue
        atual = por_responsavel.get(linha.responsavel, Decimal("0"))
        por_responsavel[linha.responsavel] = atual + linha.variavel

    datas = [linha.data_pagamento for linha in linhas if linha.data_pagamento]

    avisos: list[Aviso] = []
    if rateados:
        avisos.append(
            Aviso(
                tipo="rateio",
                mensagem="Recebimento(s) cobrindo mais de um caso: o valor foi dividido entre "
                "os responsáveis na proporção de casos de cada um, para não contar o mesmo "
                "dinheiro duas vezes.",
                quantidade=len(rateados),
                detalhes=rateados[:50],
            )
        )
    if sem_caso:
        avisos.append(
            Aviso(
                tipo="sem_caso",
                mensagem=f"{len(sem_caso)} recebimento(s) sem número de caso — ficam na "
                "tabela sem responsável e sem variável. Vincule o caso no sistema.",
                quantidade=len(sem_caso),
                detalhes=sem_caso[:50],
            )
        )
    if caso_nao_encontrado:
        numeros = sorted(caso_nao_encontrado)
        avisos.append(
            Aviso(
                tipo="caso_nao_encontrado",
                mensagem="Caso citado no cubo que não existe no relatório de casos — sem "
                "responsável, a variável fica zerada. Confira se os dois relatórios "
                "são do mesmo período.",
                quantidade=len(numeros),
                detalhes=numeros[:50],
            )
        )

    return ResumoVariavel(
        linhas=linhas,
        aliquota=aliquota,
        total_pago=sum((linha.valor_pago for linha in linhas), Decimal("0")),
        total_liquido=sum((linha.valor_liquido for linha in linhas), Decimal("0")),
        total_variavel=sum((linha.variavel for linha in linhas), Decimal("0")),
        por_responsavel=dict(
            sorted(por_responsavel.items(), key=lambda item: chave_ordenacao(item[0]))
        ),
        periodo_inicio=min(datas) if datas else None,
        periodo_fim=max(datas) if datas else None,
        avisos=avisos,
        arquivos=arquivos,
    )
