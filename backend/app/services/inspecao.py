"""Detecção do cabeçalho e casamento das colunas."""

from __future__ import annotations

from dataclasses import dataclass, field

from .texto import normalizar
from .valores import texto_celula

LINHAS_VARRIDAS = 30

PESO_CATEGORIA = 4
PESO_SUBCATEGORIA = 3
PESO_VALOR = 2
PESO_APOIO = 1


def pontuar_celula(titulo: str) -> int:
    """Pontos de uma célula como parte de um cabeçalho.

    `Categoria / Subcategoria` numa coluna só — como o fluxo de caixa exporta —
    pontua pelos dois níveis, por isso a busca é por conteúdo e não por igualdade.
    """
    if not titulo:
        return 0

    pontos = 0
    if "subcategoria" in titulo:
        pontos += PESO_SUBCATEGORIA
    if "categoria" in titulo.replace("subcategoria", ""):
        pontos += PESO_CATEGORIA
    if pontos:
        return pontos

    if titulo.startswith("valor") or titulo in ("debito", "credito"):
        return PESO_VALOR
    if titulo == "fornecedor" or titulo.startswith("data"):
        return PESO_APOIO
    return 0


def pontuar_linha(linha: list[object]) -> int:
    return sum(pontuar_celula(normalizar(celula)) for celula in linha)


def detectar_cabecalho(linhas: list[list[object]]) -> tuple[int, int]:
    """Devolve (índice da linha de cabeçalho, pontuação). Índice -1 se nada pontuar."""
    melhor_indice, melhor_pontos = -1, 0
    for indice, linha in enumerate(linhas[:LINHAS_VARRIDAS]):
        pontos = pontuar_linha(linha)
        if pontos > melhor_pontos:
            melhor_indice, melhor_pontos = indice, pontos
    return melhor_indice, melhor_pontos


@dataclass
class Mapeamento:
    """Índice da coluna de cada campo. None = coluna ausente na planilha."""

    valor: int | None = None
    categoria: int | None = None
    subcategoria: int | None = None
    data: int | None = None
    fornecedor: int | None = None
    conta: int | None = None
    # Ligado quando a coluna de valor é a de Débito: as linhas sem débito são
    # créditos (entradas), e ficam de fora sem virar aviso de erro.
    somente_preenchidos: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "valor": self.valor,
            "categoria": self.categoria,
            "subcategoria": self.subcategoria,
            "data": self.data,
            "fornecedor": self.fornecedor,
            "conta": self.conta,
            "somente_preenchidos": self.somente_preenchidos,
        }

    @classmethod
    def from_dict(cls, dados: dict | None) -> "Mapeamento":
        dados = dados or {}
        campos: dict[str, object] = {}
        for campo in ("valor", "categoria", "subcategoria", "data", "fornecedor", "conta"):
            bruto = dados.get(campo)
            campos[campo] = int(bruto) if bruto is not None and bruto != "" else None
        campos["somente_preenchidos"] = bool(dados.get("somente_preenchidos", False))
        return cls(**campos)  # type: ignore[arg-type]


@dataclass
class Cabecalho:
    indice: int
    titulos: list[str] = field(default_factory=list)
    mapeamento: Mapeamento = field(default_factory=Mapeamento)


def _primeiro(titulos_norm: list[str], predicado) -> int | None:
    for indice, titulo in enumerate(titulos_norm):
        if predicado(titulo):
            return indice
    return None


def mapear_colunas(titulos: list[str]) -> Mapeamento:
    """Casa cada campo com uma coluna do cabeçalho, na ordem de preferência."""
    norm = [normalizar(t) for t in titulos]

    debito = _primeiro(norm, lambda t: t.startswith("debito"))

    # Valor: `valor líquido` → `débito` → `valor bruto` → primeira que comece com `valor`.
    valor = _primeiro(norm, lambda t: t == "valor liquido")
    if valor is None:
        valor = _primeiro(norm, lambda t: t.startswith("valor liquido"))
    if valor is None:
        valor = debito
    if valor is None:
        valor = _primeiro(norm, lambda t: t.startswith("valor bruto"))
    if valor is None:
        valor = _primeiro(norm, lambda t: t.startswith("valor"))

    categoria = _primeiro(norm, lambda t: t == "categoria")
    if categoria is None:
        categoria = _primeiro(norm, lambda t: "categoria" in t)

    # Numa coluna só (`Categoria / Subcategoria`) não há coluna separada a casar:
    # a separação acontece no agrupamento.
    subcategoria = _primeiro(norm, lambda t: t == "subcategoria")
    if subcategoria == categoria:
        subcategoria = None

    data = _primeiro(norm, lambda t: t.startswith("data de pagamento"))
    if data is None:
        data = _primeiro(norm, lambda t: t.startswith("data de vencimento"))
    if data is None:
        data = _primeiro(norm, lambda t: t.startswith("data"))

    fornecedor = _primeiro(norm, lambda t: t.startswith("fornecedor"))

    conta = _primeiro(norm, lambda t: "conta financeira" in t or t.startswith("banco"))

    return Mapeamento(
        valor=valor,
        categoria=categoria,
        subcategoria=subcategoria,
        data=data,
        fornecedor=fornecedor,
        conta=conta,
        somente_preenchidos=valor is not None and valor == debito,
    )


def inspecionar(linhas: list[list[object]]) -> Cabecalho:
    indice, _pontos = detectar_cabecalho(linhas)
    if indice < 0:
        return Cabecalho(indice=-1)

    titulos = [texto_celula(c) for c in linhas[indice]]
    # Colunas sem título mas com dado abaixo continuam existindo; nomeia para a tela.
    titulos = [t if t else f"Coluna {i + 1}" for i, t in enumerate(titulos)]
    return Cabecalho(indice=indice, titulos=titulos, mapeamento=mapear_colunas(titulos))
