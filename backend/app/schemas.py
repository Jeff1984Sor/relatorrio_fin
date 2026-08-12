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


class LinhaVariavelOut(BaseModel):
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
    area: str
    responsavel: str
    valor_bruto: Decimal
    valor_pago: Decimal
    aliquota: Decimal
    valor_dos_impostos: Decimal
    valor_liquido: Decimal
    participacao: Decimal | None
    variavel: Decimal
    casos_do_responsavel: int
    casos_no_recebimento: int


class VariavelOut(BaseModel):
    arquivos: list[str]
    aliquota: Decimal
    periodo_inicio: dt.date | None
    periodo_fim: dt.date | None
    total_pago: Decimal
    total_liquido: Decimal
    total_variavel: Decimal
    por_responsavel: dict[str, Decimal]
    linhas: list[LinhaVariavelOut]
    avisos: list[AvisoOut]


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
