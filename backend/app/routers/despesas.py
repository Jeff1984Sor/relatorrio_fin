"""Rotas da feature de agrupamento de despesas.

O processamento é sem estado: o arquivo entra, o resumo sai, nada é guardado.
O mesmo arquivo pode ser enviado quantas vezes for, e o resultado é sempre o
mesmo — não há trava de duplicado nem histórico.
"""

from __future__ import annotations

import io
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from .. import schemas
from ..services import inspecao, leitura, planilha
from ..services.agregacao import (
    ORDEM_ALFABETICA,
    Resumo,
    SemColunaValor,
    extrair_linhas,
    montar_resumo,
)
from ..services.leitura import ArquivoIlegivel
from ..services.valores import texto_celula

router = APIRouter(prefix="/api/despesas", tags=["despesas"])

QTD_AMOSTRA = 10

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _erro_422(mensagem: str) -> HTTPException:
    return HTTPException(status_code=422, detail=mensagem)


async def _ler_upload(arquivo: UploadFile) -> bytes:
    conteudo = await arquivo.read()
    try:
        leitura.validar_upload(arquivo.filename or "", len(conteudo))
    except ArquivoIlegivel as exc:
        raise _erro_422(exc.mensagem) from exc
    return conteudo


def _mapeamento_escolhido(
    cabecalho: inspecao.Cabecalho, mapeamento_json: str | None
) -> inspecao.Mapeamento:
    if not mapeamento_json:
        return cabecalho.mapeamento
    try:
        return inspecao.Mapeamento.from_dict(json.loads(mapeamento_json))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _erro_422(
            "O mapeamento de colunas enviado está inválido. "
            "Selecione as colunas na tela e tente de novo."
        ) from exc


def _consolidar(
    conteudo: bytes, nome_arquivo: str, aba: str | None, mapeamento_json: str | None
) -> Resumo:
    """Caminho único de processamento, usado pela prévia e pelo download."""
    try:
        linhas, _aba = leitura.ler_linhas(conteudo, nome_arquivo, aba)
    except ArquivoIlegivel as exc:
        raise _erro_422(exc.mensagem) from exc

    cabecalho = inspecao.inspecionar(linhas)
    if cabecalho.indice < 0:
        raise _erro_422(
            "Não encontrei o cabeçalho da planilha nas 30 primeiras linhas. "
            "Confira se a exportação inclui as colunas Categoria e Valor."
        )

    mapa = _mapeamento_escolhido(cabecalho, mapeamento_json)

    try:
        detalhes, avisos = extrair_linhas(linhas, cabecalho.indice, mapa, unificar=True)
    except SemColunaValor as exc:
        raise _erro_422(str(exc)) from exc

    if not detalhes:
        raise _erro_422(
            "Nenhum lançamento com valor foi encontrado. "
            "Confira se a coluna de valor selecionada é a correta."
        )

    return montar_resumo(detalhes, avisos, ORDEM_ALFABETICA)


@router.post("/inspecionar", response_model=schemas.InspecaoOut)
async def inspecionar_arquivo(
    arquivo: UploadFile = File(...),
    aba: str | None = Form(default=None),
) -> schemas.InspecaoOut:
    try:
        conteudo = await _ler_upload(arquivo)
        abas = leitura.listar_abas(conteudo, arquivo.filename or "")
        linhas, aba_usada = leitura.ler_linhas(conteudo, arquivo.filename or "", aba)
    except ArquivoIlegivel as exc:
        raise _erro_422(exc.mensagem) from exc

    if not linhas:
        raise _erro_422(
            "A planilha está sem linhas. Confira se exportou a aba certa e tente de novo."
        )

    cabecalho = inspecao.inspecionar(linhas)
    if cabecalho.indice < 0:
        raise _erro_422(
            "Não encontrei o cabeçalho da planilha nas 30 primeiras linhas. "
            "Confira se a exportação inclui as colunas Categoria e Valor."
        )

    inicio = cabecalho.indice + 1
    amostra = [
        [texto_celula(celula) for celula in linha]
        for linha in linhas[inicio : inicio + QTD_AMOSTRA]
    ]

    return schemas.InspecaoOut(
        abas=abas,
        aba=aba_usada,
        linha_cabecalho=cabecalho.indice,
        colunas=cabecalho.titulos,
        mapeamento=schemas.MapeamentoOut(**cabecalho.mapeamento.to_dict()),
        amostra=amostra,
    )


@router.post("/processar", response_model=schemas.ResumoOut)
async def processar_arquivo(
    arquivo: UploadFile = File(...),
    aba: str | None = Form(default=None),
    mapeamento: str | None = Form(default=None),
) -> schemas.ResumoOut:
    conteudo = await _ler_upload(arquivo)
    nome = arquivo.filename or "planilha.xlsx"
    resumo = _consolidar(conteudo, nome, aba, mapeamento)

    return schemas.ResumoOut(
        nome_arquivo=nome,
        periodo_inicio=resumo.periodo_inicio,
        periodo_fim=resumo.periodo_fim,
        total_geral=resumo.total_geral,
        qtd_lancamentos=resumo.qtd_lancamentos,
        categorias=[
            {
                "rotulo": c.rotulo,
                "chave": c.chave,
                "total": c.total,
                "qtd": c.qtd,
                "percentual": c.percentual,
                "subcategorias": [vars(s) for s in c.subcategorias],
            }
            for c in resumo.categorias
        ],
        avisos=[a.to_dict() for a in resumo.avisos],
    )


@router.post("/xlsx")
async def baixar_xlsx(
    arquivo: UploadFile = File(...),
    aba: str | None = Form(default=None),
    mapeamento: str | None = Form(default=None),
) -> StreamingResponse:
    """Refaz a consolidação e devolve o .xlsx. Nada fica no servidor."""
    conteudo = await _ler_upload(arquivo)
    nome = arquivo.filename or "planilha.xlsx"
    resumo = _consolidar(conteudo, nome, aba, mapeamento)

    conteudo_xlsx = planilha.gerar_xlsx(resumo, contexto={"nome_arquivo": nome})
    nome_saida = planilha.nome_arquivo_saida(nome)

    return StreamingResponse(
        io.BytesIO(conteudo_xlsx),
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{nome_saida}"'},
    )
