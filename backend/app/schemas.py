"""Schemas Pydantic da API. Nada aqui é persistido — só trafega."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, Field


class MapeamentoOut(BaseModel):
    valor: int | None = None
    categoria: int | None = None
    subcategoria: int | None = None
    data: int | None = None
    fornecedor: int | None = None
    conta: int | None = None
    somente_preenchidos: bool = False


class ArquivoInspecionadoOut(BaseModel):
    nome: str
    abas: list[str]
    aba: str
    linha_cabecalho: int | None = Field(
        default=None, description="Índice (base 0) da linha detectada como cabeçalho"
    )
    colunas: list[str]
    mapeamento: MapeamentoOut
    amostra: list[list[str]] = Field(description="10 primeiras linhas de dados")


class InspecaoOut(BaseModel):
    arquivos: list[ArquivoInspecionadoOut]


class AvisoOut(BaseModel):
    tipo: str
    mensagem: str
    quantidade: int
    detalhes: list = []


class SubcategoriaOut(BaseModel):
    rotulo: str
    chave: str
    total: Decimal
    qtd: int
    percentual: float
    por_conta: dict[str, Decimal] = {}


class CategoriaOut(SubcategoriaOut):
    subcategorias: list[SubcategoriaOut]


class ResumoOut(BaseModel):
    arquivos: list[str]
    periodo_inicio: dt.date | None
    periodo_fim: dt.date | None
    total_geral: Decimal
    qtd_lancamentos: int
    contas: list[str]
    total_por_conta: dict[str, Decimal]
    categorias: list[CategoriaOut]
    avisos: list[AvisoOut]
