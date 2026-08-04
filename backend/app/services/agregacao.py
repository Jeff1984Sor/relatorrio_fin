"""Agrupamento por categoria/subcategoria e avisos de conferência."""

from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal

from .inspecao import Mapeamento
from .texto import chave_agrupamento, chave_ordenacao
from .valores import parse_data, parse_valor, texto_celula

SEM_CATEGORIA = "SEM CATEGORIA"
SEM_SUBCATEGORIA = "(sem subcategoria)"
SEM_CONTA = "(sem conta)"

# Lançamentos de folha vêm sem o prefixo `Categoria :` — trazem só a lista de
# benefícios separada por vírgula. Sem esta regra cada linha viraria uma
# categoria própria com um lançamento só.
CATEGORIA_FOLHA = "Despesas com Pessoal"

ORDEM_ALFABETICA = "alfabetica"
ORDEM_VALOR = "valor"


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
class LinhaDetalhe:
    """Uma linha da base analítica, já interpretada. Não é persistida."""

    arquivo: str
    linha_origem: int
    data: dt.date | None
    conta: str
    fornecedor: str
    categoria: str
    subcategoria: str
    categoria_key: str
    subcategoria_key: str
    valor: Decimal


@dataclass
class NoSubcategoria:
    rotulo: str
    chave: str
    total: Decimal
    qtd: int
    percentual: float
    por_conta: dict[str, Decimal] = field(default_factory=dict)


@dataclass
class NoCategoria:
    rotulo: str
    chave: str
    total: Decimal
    qtd: int
    percentual: float
    subcategorias: list[NoSubcategoria]
    por_conta: dict[str, Decimal] = field(default_factory=dict)


@dataclass
class Resumo:
    categorias: list[NoCategoria]
    total_geral: Decimal
    qtd_lancamentos: int
    periodo_inicio: dt.date | None
    periodo_fim: dt.date | None
    avisos: list[Aviso]
    detalhado: list[LinhaDetalhe]
    contas: list[str] = field(default_factory=list)
    total_por_conta: dict[str, Decimal] = field(default_factory=dict)
    arquivos: list[str] = field(default_factory=list)


class SemColunaValor(Exception):
    pass


def separar_categoria(texto: str) -> tuple[str, str]:
    """Separa `CATEGORIA:SUBCATEGORIA` numa célula só.

    O sistema de gestão exporta os dois níveis concatenados por `:` — por exemplo
    `Despesas com Pessoal : Plano de saúde`. Sem separar, cada combinação viraria
    uma categoria própria e não haveria consolidação nenhuma.

    Corta no primeiro `:` apenas. O que vier depois é subcategoria inteira, mesmo
    que contenha outro `:` — caso de erro de cadastro na origem, que o aviso de
    conferência já sinaliza.
    """
    if ":" not in texto:
        return texto, ""
    categoria, _, subcategoria = texto.partition(":")
    categoria, subcategoria = categoria.strip(), subcategoria.strip()
    # Um `:` solto na ponta não deve zerar a categoria.
    if not categoria:
        return texto, ""
    return categoria, subcategoria


def eh_lancamento_de_folha(categoria: str) -> bool:
    """Lista de benefícios separada por vírgula, sem o prefixo da categoria.

    Ex.: `Antecipação de dividendos, Auxílio Alimentação, INSS, Prolabore`.
    """
    return ":" not in categoria and "," in categoria


def _celula(linha: list[object], indice: int | None) -> object:
    if indice is None or indice < 0 or indice >= len(linha):
        return None
    return linha[indice]


def extrair_linhas(
    linhas: list[list[object]],
    indice_cabecalho: int,
    mapeamento: Mapeamento,
    unificar: bool = True,
    nome_arquivo: str = "",
) -> tuple[list[LinhaDetalhe], list[Aviso]]:
    if mapeamento.valor is None:
        raise SemColunaValor(
            "Não encontrei a coluna de valor na planilha. "
            "Selecione a coluna correta e processe de novo."
        )

    detalhes: list[LinhaDetalhe] = []
    linhas_sem_valor: list[int] = []
    qtd_sem_categoria = 0
    qtd_ignoradas_sem_debito = 0
    subcategorias_com_ponto_virgula: set[str] = set()
    lancamentos_de_folha: set[str] = set()

    for deslocamento, linha in enumerate(linhas[indice_cabecalho + 1 :]):
        numero_planilha = indice_cabecalho + 2 + deslocamento

        categoria_bruta = texto_celula(_celula(linha, mapeamento.categoria))
        subcategoria_bruta = texto_celula(_celula(linha, mapeamento.subcategoria))
        fornecedor = texto_celula(_celula(linha, mapeamento.fornecedor))
        valor_bruto = _celula(linha, mapeamento.valor)
        tem_texto = bool(categoria_bruta or subcategoria_bruta)

        # Linha totalmente vazia (rodapé, separador) é ignorada em silêncio.
        if not tem_texto and (valor_bruto is None or texto_celula(valor_bruto) == ""):
            continue

        valor = parse_valor(valor_bruto)
        if valor is None:
            if mapeamento.somente_preenchidos:
                # Débito vazio significa que a linha é um crédito (entrada), não
                # um erro. Fica de fora sem poluir os avisos.
                qtd_ignoradas_sem_debito += 1
            else:
                linhas_sem_valor.append(numero_planilha)
            continue

        if eh_lancamento_de_folha(categoria_bruta):
            lancamentos_de_folha.add(categoria_bruta)
            categoria_bruta, sub_embutida = CATEGORIA_FOLHA, fornecedor
        else:
            # A coluna de categoria pode trazer os dois níveis juntos.
            categoria_bruta, sub_embutida = separar_categoria(categoria_bruta)

        # A subcategoria da própria planilha, quando existe, tem prioridade.
        subcategoria_bruta = subcategoria_bruta or sub_embutida

        if not categoria_bruta:
            qtd_sem_categoria += 1
        if ";" in subcategoria_bruta:
            subcategorias_com_ponto_virgula.add(subcategoria_bruta)

        categoria = categoria_bruta or SEM_CATEGORIA
        subcategoria = subcategoria_bruta or SEM_SUBCATEGORIA

        if unificar:
            categoria_key = chave_agrupamento(categoria)
            subcategoria_key = chave_agrupamento(subcategoria)
        else:
            categoria_key = categoria
            subcategoria_key = subcategoria

        detalhes.append(
            LinhaDetalhe(
                arquivo=nome_arquivo,
                linha_origem=numero_planilha,
                data=parse_data(_celula(linha, mapeamento.data)),
                conta=texto_celula(_celula(linha, mapeamento.conta)) or SEM_CONTA,
                fornecedor=fornecedor,
                categoria=categoria,
                subcategoria=subcategoria,
                categoria_key=categoria_key,
                subcategoria_key=subcategoria_key,
                valor=valor,
            )
        )

    avisos: list[Aviso] = []
    prefixo = f"{nome_arquivo}: " if nome_arquivo else ""

    if qtd_ignoradas_sem_debito:
        avisos.append(
            Aviso(
                tipo="sem_debito",
                mensagem=f"{prefixo}{qtd_ignoradas_sem_debito} linha(s) sem valor na coluna "
                "Débito ficaram de fora — são créditos (entradas), não despesas.",
                quantidade=qtd_ignoradas_sem_debito,
            )
        )
    if lancamentos_de_folha:
        nomes = sorted(lancamentos_de_folha)
        avisos.append(
            Aviso(
                tipo="folha_sem_categoria",
                mensagem=f"{prefixo}Lançamento(s) de folha sem categoria cadastrada foram "
                f"agrupados em {CATEGORIA_FOLHA}, com o beneficiário como subcategoria.",
                quantidade=len(nomes),
                detalhes=nomes[:50],
            )
        )
    if qtd_sem_categoria:
        avisos.append(
            Aviso(
                tipo="sem_categoria",
                mensagem=f"{prefixo}{qtd_sem_categoria} lançamento(s) sem categoria "
                f"foram agrupados em {SEM_CATEGORIA}.",
                quantidade=qtd_sem_categoria,
            )
        )
    if linhas_sem_valor:
        avisos.append(
            Aviso(
                tipo="valor_invalido",
                mensagem=f"{prefixo}{len(linhas_sem_valor)} linha(s) com valor vazio ou não "
                "numérico foram ignoradas no total.",
                quantidade=len(linhas_sem_valor),
                detalhes=linhas_sem_valor[:200],
            )
        )
    if subcategorias_com_ponto_virgula:
        nomes = sorted(subcategorias_com_ponto_virgula)
        avisos.append(
            Aviso(
                tipo="subcategoria_com_ponto_virgula",
                mensagem=f"{prefixo}Subcategoria contendo ';' — provável erro de cadastro na "
                "base de origem. Corrija no sistema de gestão.",
                quantidade=len(nomes),
                detalhes=nomes,
            )
        )

    return detalhes, avisos


def _percentual(parte: Decimal, todo: Decimal) -> float:
    if todo == 0:
        return 0.0
    return float(parte / todo)


def _rotulo_mais_frequente(contador: Counter[str]) -> str:
    """Variante mais frequente no arquivo; empate resolvido alfabeticamente."""
    maior = max(contador.values())
    candidatos = sorted(r for r, n in contador.items() if n == maior)
    return candidatos[0]


def montar_resumo(
    detalhes: list[LinhaDetalhe],
    avisos: list[Aviso],
    ordem: str = ORDEM_ALFABETICA,
) -> Resumo:
    total_geral = sum((d.valor for d in detalhes), Decimal("0"))

    rotulos_categoria: dict[str, Counter[str]] = {}
    rotulos_subcategoria: dict[tuple[str, str], Counter[str]] = {}
    somas_categoria: dict[str, Decimal] = {}
    contagens_categoria: dict[str, int] = {}
    somas_sub: dict[tuple[str, str], Decimal] = {}
    contagens_sub: dict[tuple[str, str], int] = {}
    conta_categoria: dict[str, dict[str, Decimal]] = {}
    conta_sub: dict[tuple[str, str], dict[str, Decimal]] = {}
    total_por_conta: dict[str, Decimal] = {}

    for detalhe in detalhes:
        ck, sk = detalhe.categoria_key, detalhe.subcategoria_key
        rotulos_categoria.setdefault(ck, Counter())[detalhe.categoria] += 1
        rotulos_subcategoria.setdefault((ck, sk), Counter())[detalhe.subcategoria] += 1

        somas_categoria[ck] = somas_categoria.get(ck, Decimal("0")) + detalhe.valor
        contagens_categoria[ck] = contagens_categoria.get(ck, 0) + 1
        somas_sub[(ck, sk)] = somas_sub.get((ck, sk), Decimal("0")) + detalhe.valor
        contagens_sub[(ck, sk)] = contagens_sub.get((ck, sk), 0) + 1

        conta = detalhe.conta
        total_por_conta[conta] = total_por_conta.get(conta, Decimal("0")) + detalhe.valor
        por_cat = conta_categoria.setdefault(ck, {})
        por_cat[conta] = por_cat.get(conta, Decimal("0")) + detalhe.valor
        por_sub = conta_sub.setdefault((ck, sk), {})
        por_sub[conta] = por_sub.get(conta, Decimal("0")) + detalhe.valor

    categorias: list[NoCategoria] = []
    for ck, soma in somas_categoria.items():
        subs = [
            NoSubcategoria(
                rotulo=_rotulo_mais_frequente(rotulos_subcategoria[(c, s)]),
                chave=s,
                total=valor,
                qtd=contagens_sub[(c, s)],
                percentual=_percentual(valor, soma),
                por_conta=conta_sub[(c, s)],
            )
            for (c, s), valor in somas_sub.items()
            if c == ck
        ]
        categorias.append(
            NoCategoria(
                rotulo=_rotulo_mais_frequente(rotulos_categoria[ck]),
                chave=ck,
                total=soma,
                qtd=contagens_categoria[ck],
                percentual=_percentual(soma, total_geral),
                subcategorias=subs,
                por_conta=conta_categoria[ck],
            )
        )

    _ordenar(categorias, ordem)

    datas = [d.data for d in detalhes if d.data is not None]
    contas = sorted(total_por_conta, key=chave_ordenacao)
    arquivos = sorted({d.arquivo for d in detalhes if d.arquivo}, key=chave_ordenacao)

    return Resumo(
        categorias=categorias,
        total_geral=total_geral,
        qtd_lancamentos=len(detalhes),
        periodo_inicio=min(datas) if datas else None,
        periodo_fim=max(datas) if datas else None,
        avisos=avisos + _avisos_cruzados(categorias),
        detalhado=_ordenar_detalhado(detalhes, categorias),
        contas=contas,
        total_por_conta=total_por_conta,
        arquivos=arquivos,
    )


def _ordenar(categorias: list[NoCategoria], ordem: str) -> None:
    if ordem == ORDEM_VALOR:
        categorias.sort(key=lambda c: (-abs(c.total), chave_ordenacao(c.rotulo)))
        for categoria in categorias:
            categoria.subcategorias.sort(
                key=lambda s: (-abs(s.total), chave_ordenacao(s.rotulo))
            )
    else:
        categorias.sort(key=lambda c: chave_ordenacao(c.rotulo))
        for categoria in categorias:
            categoria.subcategorias.sort(key=lambda s: chave_ordenacao(s.rotulo))


def _ordenar_detalhado(
    detalhes: list[LinhaDetalhe], categorias: list[NoCategoria]
) -> list[LinhaDetalhe]:
    """Base analítica na mesma sequência do resumo (regra da aba `Detalhado`)."""
    posicao: dict[tuple[str, str], int] = {}
    for i, categoria in enumerate(categorias):
        for j, sub in enumerate(categoria.subcategorias):
            posicao[(categoria.chave, sub.chave)] = i * 10_000 + j
    return sorted(
        detalhes,
        key=lambda d: (
            posicao.get((d.categoria_key, d.subcategoria_key), 10**9),
            d.data or dt.date.min,
            d.linha_origem,
        ),
    )


def _avisos_cruzados(categorias: list[NoCategoria]) -> list[Aviso]:
    """Subcategoria com nome idêntico ao de uma categoria."""
    chaves_categoria = {c.chave for c in categorias}
    colisoes = sorted(
        {
            sub.rotulo
            for categoria in categorias
            for sub in categoria.subcategorias
            if sub.chave in chaves_categoria
        }
    )
    if not colisoes:
        return []
    return [
        Aviso(
            tipo="subcategoria_igual_categoria",
            mensagem="Subcategoria com o mesmo nome de uma categoria — confira se o "
            "lançamento está classificado no nível certo.",
            quantidade=len(colisoes),
            detalhes=colisoes,
        )
    ]
