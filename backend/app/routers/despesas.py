"""Rotas da feature de agrupamento de despesas.

O processamento é sem estado: os arquivos entram, o resumo sai, nada é guardado.
Podem ser enviados quantos arquivos quiser de uma vez — os lançamentos de todos
entram num consolidado único, com uma coluna de valor por conta bancária.
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
    Aviso,
    LinhaDetalhe,
    Resumo,
    SemColunaValor,
    extrair_linhas,
    montar_resumo,
)
from ..services.leitura import ArquivoIlegivel
from ..services.valores import texto_celula

router = APIRouter(prefix="/api/despesas", tags=["despesas"])

QTD_AMOSTRA = 10
MAX_ARQUIVOS = 24

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _erro_422(mensagem: str) -> HTTPException:
    return HTTPException(status_code=422, detail=mensagem)


def _validar_quantidade(arquivos: list[UploadFile]) -> None:
    if not arquivos:
        raise _erro_422("Envie ao menos uma planilha.")
    if len(arquivos) > MAX_ARQUIVOS:
        raise _erro_422(
            f"São aceitos até {MAX_ARQUIVOS} arquivos por vez. "
            f"Você enviou {len(arquivos)}; divida em lotes menores."
        )


async def _ler_upload(arquivo: UploadFile) -> bytes:
    conteudo = await arquivo.read()
    try:
        leitura.validar_upload(arquivo.filename or "", len(conteudo))
    except ArquivoIlegivel as exc:
        raise _erro_422(exc.mensagem) from exc
    return conteudo


def _com_nome(nome: str, mensagem: str) -> str:
    """Prefixa a mensagem com o arquivo — sem isso, num lote de 12, o usuário não
    sabe qual planilha deu problema."""
    return f"{nome}: {mensagem}"


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


def _linhas_do_arquivo(conteudo: bytes, nome: str, aba: str | None) -> list[list[object]]:
    try:
        linhas, _aba = leitura.ler_linhas(conteudo, nome, aba)
    except ArquivoIlegivel as exc:
        raise _erro_422(_com_nome(nome, exc.mensagem)) from exc

    if not linhas:
        raise _erro_422(
            _com_nome(nome, "a planilha está sem linhas. Confira se exportou a aba certa.")
        )
    return linhas


def _cabecalho_do_arquivo(linhas: list[list[object]], nome: str) -> inspecao.Cabecalho:
    cabecalho = inspecao.inspecionar(linhas)
    if cabecalho.indice < 0:
        raise _erro_422(
            _com_nome(
                nome,
                "não encontrei o cabeçalho nas 30 primeiras linhas. Confira se a "
                "exportação inclui as colunas de categoria e de valor.",
            )
        )
    return cabecalho


async def _consolidar(
    arquivos: list[UploadFile], aba: str | None, mapeamento_json: str | None
) -> Resumo:
    """Caminho único de processamento, usado pela prévia e pelo download."""
    _validar_quantidade(arquivos)

    detalhes: list[LinhaDetalhe] = []
    avisos: list[Aviso] = []

    for arquivo in arquivos:
        nome = arquivo.filename or "planilha.xlsx"
        conteudo = await _ler_upload(arquivo)

        linhas = _linhas_do_arquivo(conteudo, nome, aba)
        cabecalho = _cabecalho_do_arquivo(linhas, nome)
        mapa = _mapeamento_escolhido(cabecalho, mapeamento_json)

        try:
            do_arquivo, avisos_do_arquivo = extrair_linhas(
                linhas, cabecalho.indice, mapa, nome_arquivo=nome
            )
        except SemColunaValor as exc:
            raise _erro_422(_com_nome(nome, str(exc))) from exc

        detalhes.extend(do_arquivo)
        avisos.extend(avisos_do_arquivo)

    if not detalhes:
        raise _erro_422(
            "Nenhum lançamento com valor foi encontrado. "
            "Confira se a coluna de valor selecionada é a correta."
        )

    return montar_resumo(detalhes, avisos, ORDEM_ALFABETICA)


@router.post("/inspecionar", response_model=schemas.InspecaoOut)
async def inspecionar_arquivos(
    arquivos: list[UploadFile] = File(...),
    aba: str | None = Form(default=None),
) -> schemas.InspecaoOut:
    _validar_quantidade(arquivos)

    inspecionados = []
    for arquivo in arquivos:
        nome = arquivo.filename or "planilha.xlsx"
        conteudo = await _ler_upload(arquivo)

        try:
            abas = leitura.listar_abas(conteudo, nome)
            _linhas, aba_usada = leitura.ler_linhas(conteudo, nome, aba)
        except ArquivoIlegivel as exc:
            raise _erro_422(_com_nome(nome, exc.mensagem)) from exc

        linhas = _linhas_do_arquivo(conteudo, nome, aba)
        cabecalho = _cabecalho_do_arquivo(linhas, nome)

        inicio = cabecalho.indice + 1
        amostra = [
            [texto_celula(celula) for celula in linha]
            for linha in linhas[inicio : inicio + QTD_AMOSTRA]
        ]

        inspecionados.append(
            schemas.ArquivoInspecionadoOut(
                nome=nome,
                abas=abas,
                aba=aba_usada,
                linha_cabecalho=cabecalho.indice,
                colunas=cabecalho.titulos,
                mapeamento=schemas.MapeamentoOut(**cabecalho.mapeamento.to_dict()),
                amostra=amostra,
            )
        )

    return schemas.InspecaoOut(arquivos=inspecionados)


def _no_para_dict(no) -> dict:
    dados = {
        "rotulo": no.rotulo,
        "chave": no.chave,
        "total": no.total,
        "qtd": no.qtd,
        "percentual": no.percentual,
        "por_conta": no.por_conta,
    }
    if hasattr(no, "subcategorias"):
        dados["subcategorias"] = [_no_para_dict(s) for s in no.subcategorias]
    return dados


@router.post("/processar", response_model=schemas.ResumoOut)
async def processar_arquivos(
    arquivos: list[UploadFile] = File(...),
    aba: str | None = Form(default=None),
    mapeamento: str | None = Form(default=None),
) -> schemas.ResumoOut:
    resumo = await _consolidar(arquivos, aba, mapeamento)

    return schemas.ResumoOut(
        arquivos=resumo.arquivos,
        periodo_inicio=resumo.periodo_inicio,
        periodo_fim=resumo.periodo_fim,
        total_geral=resumo.total_geral,
        qtd_lancamentos=resumo.qtd_lancamentos,
        contas=resumo.contas,
        total_por_conta=resumo.total_por_conta,
        categorias=[_no_para_dict(c) for c in resumo.categorias],
        avisos=[a.to_dict() for a in resumo.avisos],
    )


@router.post("/xlsx")
async def baixar_xlsx(
    arquivos: list[UploadFile] = File(...),
    aba: str | None = Form(default=None),
    mapeamento: str | None = Form(default=None),
) -> StreamingResponse:
    """Refaz a consolidação e devolve o .xlsx. Nada fica no servidor."""
    resumo = await _consolidar(arquivos, aba, mapeamento)

    origem = ", ".join(resumo.arquivos) if resumo.arquivos else "-"
    conteudo_xlsx = planilha.gerar_xlsx(resumo, contexto={"nome_arquivo": origem})

    base = resumo.arquivos[0] if len(resumo.arquivos) == 1 else "despesas-consolidado"
    nome_saida = planilha.nome_arquivo_saida(base)

    return StreamingResponse(
        io.BytesIO(conteudo_xlsx),
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{nome_saida}"'},
    )
