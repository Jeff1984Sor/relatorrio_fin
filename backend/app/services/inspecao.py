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


def pontuar_linha(linha: list[object]) -> int:
    """Pontuação da linha como candidata a cabeçalho (regra 4.1 do escopo)."""
    total = 0
    for celula in linha:
        texto = normalizar(celula)
        if not texto:
            continue
        if texto == "subcategoria":
            total += PESO_SUBCATEGORIA
        elif texto == "categoria":
            total += PESO_CATEGORIA
        elif texto.startswith("valor"):
            total += PESO_VALOR
        elif texto == "fornecedor" or texto.startswith("data de"):
            total += PESO_APOIO
    return total


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

    def to_dict(self) -> dict[str, int | None]:
        return {
            "valor": self.valor,
            "categoria": self.categoria,
            "subcategoria": self.subcategoria,
            "data": self.data,
            "fornecedor": self.fornecedor,
        }

    @classmethod
    def from_dict(cls, dados: dict | None) -> "Mapeamento":
        dados = dados or {}
        campos = {}
        for campo in ("valor", "categoria", "subcategoria", "data", "fornecedor"):
            bruto = dados.get(campo)
            campos[campo] = int(bruto) if bruto is not None and bruto != "" else None
        return cls(**campos)


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
    """Casa cada campo com uma coluna do cabeçalho, na ordem de preferência do escopo."""
    norm = [normalizar(t) for t in titulos]

    # Valor: `valor líquido` → `valor bruto` → primeira coluna que comece com `valor`.
    valor = _primeiro(norm, lambda t: t == "valor liquido")
    if valor is None:
        valor = _primeiro(norm, lambda t: t.startswith("valor liquido"))
    if valor is None:
        valor = _primeiro(norm, lambda t: t.startswith("valor bruto"))
    if valor is None:
        valor = _primeiro(norm, lambda t: t.startswith("valor"))

    categoria = _primeiro(norm, lambda t: t == "categoria")
    if categoria is None:
        categoria = _primeiro(norm, lambda t: t.startswith("categoria"))

    subcategoria = _primeiro(norm, lambda t: t == "subcategoria")
    if subcategoria is None:
        subcategoria = _primeiro(norm, lambda t: t.startswith("subcategoria"))

    data = _primeiro(norm, lambda t: t.startswith("data de pagamento"))
    if data is None:
        data = _primeiro(norm, lambda t: t.startswith("data de vencimento"))
    if data is None:
        data = _primeiro(norm, lambda t: t.startswith("data"))

    fornecedor = _primeiro(norm, lambda t: t.startswith("fornecedor"))

    return Mapeamento(
        valor=valor,
        categoria=categoria,
        subcategoria=subcategoria,
        data=data,
        fornecedor=fornecedor,
    )


def inspecionar(linhas: list[list[object]]) -> Cabecalho:
    indice, _pontos = detectar_cabecalho(linhas)
    if indice < 0:
        return Cabecalho(indice=-1)

    titulos = [texto_celula(c) for c in linhas[indice]]
    # Colunas sem título mas com dado abaixo continuam existindo; nomeia para a tela.
    titulos = [t if t else f"Coluna {i + 1}" for i, t in enumerate(titulos)]
    return Cabecalho(indice=indice, titulos=titulos, mapeamento=mapear_colunas(titulos))
