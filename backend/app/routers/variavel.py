"""Rotas do relatório de remuneração variável.

Recebe o cubo de recebimentos e o relatório de casos, cruza os dois e devolve o
cálculo. Sem estado: nada é guardado no servidor.
"""

from __future__ import annotations

import io
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from .. import schemas
from ..services import leitura, planilha_variavel, variavel
from ..services.leitura import ArquivoIlegivel
from ..services.variavel import ArquivoInesperado, ResumoVariavel

router = APIRouter(prefix="/api/variavel", tags=["variavel"])

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _erro_422(mensagem: str) -> HTTPException:
    return HTTPException(status_code=422, detail=mensagem)


async def _linhas(arquivo: UploadFile, rotulo: str) -> list[list[object]]:
    conteudo = await arquivo.read()
    nome = arquivo.filename or f"{rotulo}.xls"
    try:
        leitura.validar_upload(nome, len(conteudo))
        linhas, _aba = leitura.ler_linhas(conteudo, nome)
    except ArquivoIlegivel as exc:
        raise _erro_422(f"{rotulo} ({nome}): {exc.mensagem}") from exc

    if not linhas:
        raise _erro_422(f"{rotulo} ({nome}) está sem linhas. Exporte de novo e tente outra vez.")
    return linhas


def _aliquota(bruta: str | None) -> Decimal:
    if bruta is None or str(bruta).strip() == "":
        return variavel.ALIQUOTA_PADRAO
    try:
        valor = Decimal(str(bruta).replace("%", "").replace(",", ".").strip())
    except InvalidOperation as exc:
        raise _erro_422(
            "A alíquota do imposto está inválida. Informe algo como 17,5."
        ) from exc

    # Aceita tanto 17,5 quanto 0,175.
    if valor > 1:
        valor = valor / 100
    if not (0 <= valor < 1):
        raise _erro_422("A alíquota do imposto precisa estar entre 0 e 100%.")
    return valor


async def _montar(
    cubo: UploadFile, casos: UploadFile, aliquota: str | None
) -> ResumoVariavel:
    linhas_cubo = await _linhas(cubo, "Cubo de recebimentos")
    linhas_casos = await _linhas(casos, "Relatório de casos")

    try:
        return variavel.montar(
            linhas_cubo,
            linhas_casos,
            aliquota=_aliquota(aliquota),
            arquivos=[cubo.filename or "cubo", casos.filename or "casos"],
        )
    except ArquivoInesperado as exc:
        raise _erro_422(str(exc)) from exc


def _linha_out(linha: variavel.LinhaVariavel) -> dict:
    return {
        "grupo": linha.grupo,
        "pagador": linha.pagador,
        "cliente": linha.cliente,
        "nh": linha.nh,
        "nf": linha.nf,
        "situacao": linha.situacao,
        "data_vencimento": linha.data_vencimento,
        "data_pagamento": linha.data_pagamento,
        "numero_do_caso": linha.numero_do_caso,
        "titulo": linha.titulo,
        "area": linha.area,
        "responsavel": linha.responsavel,
        "valor_bruto": linha.valor_bruto,
        "valor_pago": linha.valor_pago,
        "aliquota": linha.aliquota,
        "valor_dos_impostos": linha.valor_dos_impostos,
        "valor_liquido": linha.valor_liquido,
        "participacao": linha.participacao,
        "variavel": linha.variavel,
        "casos_do_responsavel": linha.casos_do_responsavel,
        "casos_no_recebimento": linha.casos_no_recebimento,
    }


@router.post("/processar", response_model=schemas.VariavelOut)
async def processar(
    cubo: UploadFile = File(..., description="Visão cubo de recebimentos"),
    casos: UploadFile = File(..., description="Relatório de casos"),
    aliquota: str | None = Form(default=None),
) -> schemas.VariavelOut:
    resumo = await _montar(cubo, casos, aliquota)
    return schemas.VariavelOut(
        arquivos=resumo.arquivos,
        aliquota=resumo.aliquota,
        periodo_inicio=resumo.periodo_inicio,
        periodo_fim=resumo.periodo_fim,
        total_pago=resumo.total_pago,
        total_liquido=resumo.total_liquido,
        total_variavel=resumo.total_variavel,
        por_responsavel=resumo.por_responsavel,
        linhas=[_linha_out(linha) for linha in resumo.linhas],
        avisos=[aviso.to_dict() for aviso in resumo.avisos],
    )


@router.post("/xlsx")
async def baixar_xlsx(
    cubo: UploadFile = File(...),
    casos: UploadFile = File(...),
    aliquota: str | None = Form(default=None),
) -> StreamingResponse:
    resumo = await _montar(cubo, casos, aliquota)
    conteudo = planilha_variavel.gerar_xlsx(resumo)

    sufixo = ""
    if resumo.periodo_fim:
        sufixo = f"-{resumo.periodo_fim.strftime('%Y-%m')}"

    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="relatorio-variavel{sufixo}.xlsx"'},
    )
