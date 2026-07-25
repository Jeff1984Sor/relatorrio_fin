"""Schemas Pydantic da API."""

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
    hash_arquivo: str
    ja_processado_id: int | None = None


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


class OpcoesOut(BaseModel):
    unificar: bool = True
    positivo: bool = False
    ordem: str = "alfabetica"
    mapeamento: dict = {}


class ResumoOut(BaseModel):
    processamento_id: int
    nome_arquivo: str
    criado_em: dt.datetime
    criado_por: str
    periodo_inicio: dt.date | None
    periodo_fim: dt.date | None
    total_geral: Decimal
    qtd_lancamentos: int
    opcoes: OpcoesOut
    categorias: list[CategoriaOut]
    avisos: list[AvisoOut]


class ProcessamentoResumidoOut(BaseModel):
    id: int
    nome_arquivo: str
    criado_em: dt.datetime
    criado_por: str
    periodo_inicio: dt.date | None
    periodo_fim: dt.date | None
    total_geral: Decimal
    qtd_lancamentos: int


class HistoricoOut(BaseModel):
    itens: list[ProcessamentoResumidoOut]
    total: int
    pagina: int
    por_pagina: int


class VariacaoOut(BaseModel):
    rotulo: str
    chave: str
    total_a: Decimal
    total_b: Decimal
    variacao: Decimal
    variacao_percentual: float | None


class VariacaoCategoriaOut(VariacaoOut):
    subcategorias: list[VariacaoOut]


class ComparacaoOut(BaseModel):
    a: ProcessamentoResumidoOut
    b: ProcessamentoResumidoOut
    total_a: Decimal
    total_b: Decimal
    variacao: Decimal
    variacao_percentual: float | None
    categorias: list[VariacaoCategoriaOut]


class ArquivoDuplicadoOut(BaseModel):
    detalhe: str
    processamento_id: int
