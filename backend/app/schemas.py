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


class InspecaoOut(BaseModel):
    abas: list[str]
    aba: str
    linha_cabecalho: int | None = Field(
        default=None, description="Índice (base 0) da linha detectada como cabeçalho"
    )
    colunas: list[str]
    mapeamento: MapeamentoOut
    amostra: list[list[str]] = Field(description="10 primeiras linhas de dados")


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


class CategoriaOut(BaseModel):
    rotulo: str
    chave: str
    total: Decimal
    qtd: int
    percentual: float
    subcategorias: list[SubcategoriaOut]


class ResumoOut(BaseModel):
    nome_arquivo: str
    periodo_inicio: dt.date | None
    periodo_fim: dt.date | None
    total_geral: Decimal
    qtd_lancamentos: int
    categorias: list[CategoriaOut]
    avisos: list[AvisoOut]
