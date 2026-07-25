"""Geração da planilha consolidada com openpyxl."""

from __future__ import annotations

import datetime as dt
import io
import re
import unicodedata
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .agregacao import Resumo, aplicar_sinal

FORMATO_MOEDA = '"R$" #,##0.00_);[Red]("R$" #,##0.00)'
FORMATO_PERCENTUAL = "0.0%"

COR_ESCURA = "404040"
COR_CATEGORIA = "F8CBAD"
COR_BORDA = "BFBFBF"
COR_BORDA_SUAVE = "D9D9D9"

BORDA_FINA = Border(*(Side(style="thin", color=COR_BORDA),) * 4)
BORDA_INFERIOR_HAIR = Border(bottom=Side(style="hair", color=COR_BORDA_SUAVE))

LARGURAS = (46, 18, 10, 12)


def _preenchimento(cor: str) -> PatternFill:
    return PatternFill(start_color=cor, end_color=cor, fill_type="solid")


def nome_arquivo_saida(nome_original: str) -> str:
    base = re.sub(r"\.[^.]+$", "", nome_original) or "despesas"
    base = unicodedata.normalize("NFKD", base)
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-").lower()
    return f"resumo-{base or 'despesas'}.xlsx"


def _aba_resumo(ws: Worksheet, resumo: Resumo, contexto: dict, positivo: bool) -> None:
    ws.title = "Resumo"

    # `summaryBelow = False` põe o total ACIMA do grupo; sem isso o +/- da lateral
    # do Excel aparece na linha errada.
    ws.sheet_properties.outlinePr.summaryBelow = False

    ws.merge_cells("A1:D1")
    titulo = ws["A1"]
    titulo.value = "RESUMO DE DESPESAS POR CATEGORIA"
    titulo.font = Font(bold=True, size=14)
    titulo.alignment = Alignment(horizontal="left", vertical="center")

    periodo = _texto_periodo(resumo.periodo_inicio, resumo.periodo_fim)
    gerado_em = contexto.get("gerado_em") or dt.datetime.now()
    ws.merge_cells("A2:D2")
    subtitulo = ws["A2"]
    subtitulo.value = (
        f"{periodo}  •  Origem: {contexto.get('nome_arquivo', '-')}  •  "
        f"Gerado em {gerado_em.strftime('%d/%m/%Y %H:%M')}"
    )
    subtitulo.font = Font(size=9, color="808080")

    cabecalhos = ("Categoria / Subcategoria", "Valor", "%", "Lançamentos")
    for coluna, texto in enumerate(cabecalhos, start=1):
        celula = ws.cell(row=4, column=coluna, value=texto)
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = _preenchimento(COR_ESCURA)
        celula.alignment = Alignment(
            horizontal="left" if coluna == 1 else "right", vertical="center"
        )
    ws.freeze_panes = "A5"

    linha = 5
    for categoria in resumo.categorias:
        _escrever_categoria(ws, linha, categoria, positivo)
        linha += 1
        for sub in categoria.subcategorias:
            _escrever_subcategoria(ws, linha, sub, positivo)
            linha += 1

    _escrever_total(ws, linha, resumo, positivo)

    for indice, largura in enumerate(LARGURAS, start=1):
        ws.column_dimensions[get_column_letter(indice)].width = largura


def _escrever_categoria(ws: Worksheet, linha: int, categoria, positivo: bool) -> None:
    valores = (
        categoria.rotulo.upper(),
        aplicar_sinal(categoria.total, positivo),
        categoria.percentual,
        categoria.qtd,
    )
    for coluna, valor in enumerate(valores, start=1):
        celula = ws.cell(row=linha, column=coluna, value=valor)
        celula.font = Font(bold=True)
        celula.fill = _preenchimento(COR_CATEGORIA)
        celula.border = BORDA_FINA
        celula.alignment = Alignment(horizontal="left" if coluna == 1 else "right")
    ws.cell(row=linha, column=2).number_format = FORMATO_MOEDA
    ws.cell(row=linha, column=3).number_format = FORMATO_PERCENTUAL


def _escrever_subcategoria(ws: Worksheet, linha: int, sub, positivo: bool) -> None:
    valores = (
        sub.rotulo,
        aplicar_sinal(sub.total, positivo),
        sub.percentual,
        sub.qtd,
    )
    for coluna, valor in enumerate(valores, start=1):
        celula = ws.cell(row=linha, column=coluna, value=valor)
        celula.border = BORDA_INFERIOR_HAIR
        celula.alignment = Alignment(
            horizontal="left" if coluna == 1 else "right", indent=2 if coluna == 1 else 0
        )
    ws.cell(row=linha, column=2).number_format = FORMATO_MOEDA
    ws.cell(row=linha, column=3).number_format = FORMATO_PERCENTUAL
    ws.row_dimensions[linha].outline_level = 1


def _escrever_total(ws: Worksheet, linha: int, resumo: Resumo, positivo: bool) -> None:
    valores = (
        "TOTAL GERAL",
        aplicar_sinal(resumo.total_geral, positivo),
        1.0 if resumo.total_geral else 0.0,
        resumo.qtd_lancamentos,
    )
    for coluna, valor in enumerate(valores, start=1):
        celula = ws.cell(row=linha, column=coluna, value=valor)
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = _preenchimento(COR_ESCURA)
        celula.alignment = Alignment(horizontal="left" if coluna == 1 else "right")
    ws.cell(row=linha, column=2).number_format = FORMATO_MOEDA
    ws.cell(row=linha, column=3).number_format = FORMATO_PERCENTUAL


def _aba_detalhado(ws: Worksheet, resumo: Resumo, positivo: bool) -> None:
    cabecalhos = (
        "Data",
        "Fornecedor",
        "Categoria",
        "Subcategoria",
        "Valor",
        "Linha na origem",
    )
    for coluna, texto in enumerate(cabecalhos, start=1):
        celula = ws.cell(row=1, column=coluna, value=texto)
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = _preenchimento(COR_ESCURA)

    for indice, detalhe in enumerate(resumo.detalhado, start=2):
        ws.cell(row=indice, column=1, value=detalhe.data).number_format = "DD/MM/YYYY"
        ws.cell(row=indice, column=2, value=detalhe.fornecedor)
        ws.cell(row=indice, column=3, value=detalhe.categoria)
        ws.cell(row=indice, column=4, value=detalhe.subcategoria)
        valor = ws.cell(row=indice, column=5, value=aplicar_sinal(detalhe.valor, positivo))
        valor.number_format = FORMATO_MOEDA
        ws.cell(row=indice, column=6, value=detalhe.linha_origem)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:F{max(1, len(resumo.detalhado) + 1)}"
    for coluna, largura in enumerate((14, 38, 30, 30, 18, 16), start=1):
        ws.column_dimensions[get_column_letter(coluna)].width = largura


def _aba_conferencia(ws: Worksheet, resumo: Resumo) -> None:
    for coluna, texto in enumerate(("Tipo", "O que verificar", "Quantidade", "Detalhes"), 1):
        celula = ws.cell(row=1, column=coluna, value=texto)
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = _preenchimento(COR_ESCURA)

    for indice, aviso in enumerate(resumo.avisos, start=2):
        ws.cell(row=indice, column=1, value=aviso.tipo)
        ws.cell(row=indice, column=2, value=aviso.mensagem).alignment = Alignment(
            wrap_text=True, vertical="top"
        )
        ws.cell(row=indice, column=3, value=aviso.quantidade)
        ws.cell(
            row=indice,
            column=4,
            value=", ".join(str(d) for d in aviso.detalhes) if aviso.detalhes else "",
        )

    ws.freeze_panes = "A2"
    for coluna, largura in enumerate((32, 60, 12, 60), start=1):
        ws.column_dimensions[get_column_letter(coluna)].width = largura


def _texto_periodo(inicio: dt.date | None, fim: dt.date | None) -> str:
    if inicio and fim:
        return f"Período: {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
    return "Período não identificado"


def gerar_xlsx(resumo: Resumo, contexto: dict, positivo: bool = False) -> bytes:
    wb = Workbook()
    _aba_resumo(wb.active, resumo, contexto, positivo)
    _aba_detalhado(wb.create_sheet("Detalhado"), resumo, positivo)
    if resumo.avisos:
        _aba_conferencia(wb.create_sheet("Conferência"), resumo)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def total_como_decimal(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"))
