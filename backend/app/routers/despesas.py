"""Rotas da feature de agrupamento de despesas."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config, schemas
from ..database import get_db
from ..models import Processamento
from ..services import inspecao, leitura, persistencia, planilha
from ..services.agregacao import (
    ORDEM_ALFABETICA,
    ORDEM_VALOR,
    Opcoes,
    SemColunaValor,
    extrair_linhas,
    montar_resumo,
)
from ..services.leitura import ArquivoIlegivel
from ..services.valores import texto_celula

router = APIRouter(prefix="/api/despesas", tags=["despesas"])

QTD_AMOSTRA = 10


async def _ler_upload(arquivo: UploadFile) -> bytes:
    conteudo = await arquivo.read()
    leitura.validar_upload(arquivo.filename or "", len(conteudo))
    return conteudo


def _hash(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def _erro_422(mensagem: str) -> HTTPException:
    return HTTPException(status_code=422, detail=mensagem)


@router.post("/inspecionar", response_model=schemas.InspecaoOut)
async def inspecionar_arquivo(
    arquivo: UploadFile = File(...),
    aba: str | None = Form(default=None),
    db: Session = Depends(get_db),
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
            "Confira se a exportação inclui as colunas Categoria, Subcategoria e Valor."
        )

    inicio = cabecalho.indice + 1
    amostra = [
        [texto_celula(celula) for celula in linha]
        for linha in linhas[inicio : inicio + QTD_AMOSTRA]
    ]

    hash_arquivo = _hash(conteudo)
    anterior = persistencia.buscar_por_hash(db, hash_arquivo)

    return schemas.InspecaoOut(
        abas=abas,
        aba=aba_usada,
        linha_cabecalho=cabecalho.indice,
        colunas=cabecalho.titulos,
        mapeamento=schemas.MapeamentoOut(**cabecalho.mapeamento.to_dict()),
        amostra=amostra,
        hash_arquivo=hash_arquivo,
        ja_processado_id=anterior.id if anterior else None,
    )


@router.post("/processar", response_model=schemas.ResumoOut)
async def processar_arquivo(
    arquivo: UploadFile = File(...),
    aba: str | None = Form(default=None),
    unificar: bool = Form(default=True),
    positivo: bool = Form(default=False),
    ordem: str = Form(default=ORDEM_ALFABETICA),
    mapeamento: str | None = Form(default=None),
    forcar: bool = Form(default=False),
    db: Session = Depends(get_db),
) -> schemas.ResumoOut:
    try:
        conteudo = await _ler_upload(arquivo)
        linhas, _aba = leitura.ler_linhas(conteudo, arquivo.filename or "", aba)
    except ArquivoIlegivel as exc:
        raise _erro_422(exc.mensagem) from exc

    hash_arquivo = _hash(conteudo)
    if not forcar:
        anterior = persistencia.buscar_por_hash(db, hash_arquivo)
        if anterior is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "detalhe": "Este arquivo já foi processado. "
                    "Abra o resultado anterior ou processe novamente assim mesmo.",
                    "processamento_id": anterior.id,
                },
            )

    if ordem not in (ORDEM_ALFABETICA, ORDEM_VALOR):
        ordem = ORDEM_ALFABETICA

    cabecalho = inspecao.inspecionar(linhas)
    if cabecalho.indice < 0:
        raise _erro_422(
            "Não encontrei o cabeçalho da planilha nas 30 primeiras linhas. "
            "Confira a exportação e tente de novo."
        )

    mapa = cabecalho.mapeamento
    if mapeamento:
        try:
            mapa = inspecao.Mapeamento.from_dict(json.loads(mapeamento))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise _erro_422(
                "O mapeamento de colunas enviado está inválido. "
                "Selecione as colunas na tela e tente de novo."
            ) from exc

    try:
        detalhes, avisos = extrair_linhas(linhas, cabecalho.indice, mapa, unificar)
    except SemColunaValor as exc:
        raise _erro_422(str(exc)) from exc

    if not detalhes:
        raise _erro_422(
            "Nenhum lançamento com valor foi encontrado. "
            "Confira se a coluna de valor selecionada é a correta."
        )

    resumo = montar_resumo(detalhes, avisos, ordem)

    opcoes = Opcoes(
        unificar=unificar, positivo=positivo, ordem=ordem, mapeamento=mapa.to_dict()
    )
    processamento = persistencia.salvar(
        db,
        resumo,
        nome_arquivo=arquivo.filename or "planilha.xlsx",
        hash_arquivo=hash_arquivo,
        opcoes=opcoes,
        criado_por=config.USUARIO_PADRAO,
    )

    conteudo_xlsx = planilha.gerar_xlsx(
        resumo,
        contexto={
            "nome_arquivo": processamento.nome_arquivo,
            "gerado_em": processamento.criado_em,
        },
        positivo=positivo,
    )
    persistencia.guardar_xlsx(processamento.id, conteudo_xlsx)

    return _resumo_out(processamento)


def _buscar(db: Session, processamento_id: int) -> Processamento:
    processamento = db.get(Processamento, processamento_id)
    if processamento is None:
        raise HTTPException(
            status_code=404, detail="Processamento não encontrado. Ele pode ter sido removido."
        )
    return processamento


def _resumo_out(processamento: Processamento) -> schemas.ResumoOut:
    return schemas.ResumoOut(
        processamento_id=processamento.id,
        nome_arquivo=processamento.nome_arquivo,
        criado_em=processamento.criado_em,
        criado_por=processamento.criado_por,
        periodo_inicio=processamento.periodo_inicio,
        periodo_fim=processamento.periodo_fim,
        total_geral=processamento.total_geral,
        qtd_lancamentos=processamento.qtd_lancamentos,
        opcoes=schemas.OpcoesOut(**(processamento.opcoes or {})),
        categorias=persistencia.montar_categorias(processamento),
        avisos=processamento.avisos or [],
    )


def _resumido(processamento: Processamento) -> schemas.ProcessamentoResumidoOut:
    return schemas.ProcessamentoResumidoOut(
        id=processamento.id,
        nome_arquivo=processamento.nome_arquivo,
        criado_em=processamento.criado_em,
        criado_por=processamento.criado_por,
        periodo_inicio=processamento.periodo_inicio,
        periodo_fim=processamento.periodo_fim,
        total_geral=processamento.total_geral,
        qtd_lancamentos=processamento.qtd_lancamentos,
    )


@router.get("", response_model=schemas.HistoricoOut)
def historico(
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> schemas.HistoricoOut:
    total = db.scalar(select(func.count()).select_from(Processamento)) or 0
    consulta = (
        select(Processamento)
        .order_by(Processamento.id.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    )
    itens = [_resumido(p) for p in db.scalars(consulta).all()]
    return schemas.HistoricoOut(
        itens=itens, total=total, pagina=pagina, por_pagina=por_pagina
    )


@router.get("/comparar", response_model=schemas.ComparacaoOut)
def comparar(
    a: int = Query(...),
    b: int = Query(...),
    db: Session = Depends(get_db),
) -> schemas.ComparacaoOut:
    proc_a, proc_b = _buscar(db, a), _buscar(db, b)
    return _montar_comparacao(proc_a, proc_b)


@router.get("/{processamento_id}", response_model=schemas.ResumoOut)
def obter(processamento_id: int, db: Session = Depends(get_db)) -> schemas.ResumoOut:
    return _resumo_out(_buscar(db, processamento_id))


@router.get("/{processamento_id}/xlsx")
def baixar_xlsx(processamento_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    processamento = _buscar(db, processamento_id)
    caminho = persistencia.caminho_xlsx(processamento_id)
    if not caminho.exists():
        raise _erro_422(
            "O arquivo consolidado não está mais disponível no servidor. "
            "Processe a planilha novamente."
        )

    nome = planilha.nome_arquivo_saida(processamento.nome_arquivo)
    return StreamingResponse(
        caminho.open("rb"),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


def _variacao_percentual(anterior: Decimal, atual: Decimal) -> float | None:
    if anterior == 0:
        return None
    return float((atual - anterior) / abs(anterior))


def _indexar(processamento: Processamento) -> tuple[dict, dict]:
    categorias = {}
    subcategorias = {}
    for categoria in persistencia.montar_categorias(processamento):
        categorias[categoria["chave"]] = categoria
        for sub in categoria["subcategorias"]:
            subcategorias[(categoria["chave"], sub["chave"])] = sub
    return categorias, subcategorias


def _montar_comparacao(a: Processamento, b: Processamento) -> schemas.ComparacaoOut:
    cat_a, sub_a = _indexar(a)
    cat_b, sub_b = _indexar(b)

    linhas = []
    for chave in sorted(set(cat_a) | set(cat_b)):
        na, nb = cat_a.get(chave), cat_b.get(chave)
        total_a = na["total"] if na else Decimal("0")
        total_b = nb["total"] if nb else Decimal("0")
        rotulo = (na or nb)["rotulo"]

        chaves_sub = {k[1] for k in sub_a if k[0] == chave} | {
            k[1] for k in sub_b if k[0] == chave
        }
        subs = []
        for sub_chave in sorted(chaves_sub):
            sa, sb = sub_a.get((chave, sub_chave)), sub_b.get((chave, sub_chave))
            sub_total_a = sa["total"] if sa else Decimal("0")
            sub_total_b = sb["total"] if sb else Decimal("0")
            subs.append(
                schemas.VariacaoOut(
                    rotulo=(sa or sb)["rotulo"],
                    chave=sub_chave,
                    total_a=sub_total_a,
                    total_b=sub_total_b,
                    variacao=sub_total_b - sub_total_a,
                    variacao_percentual=_variacao_percentual(sub_total_a, sub_total_b),
                )
            )

        linhas.append(
            schemas.VariacaoCategoriaOut(
                rotulo=rotulo,
                chave=chave,
                total_a=total_a,
                total_b=total_b,
                variacao=total_b - total_a,
                variacao_percentual=_variacao_percentual(total_a, total_b),
                subcategorias=subs,
            )
        )

    return schemas.ComparacaoOut(
        a=_resumido(a),
        b=_resumido(b),
        total_a=a.total_geral,
        total_b=b.total_geral,
        variacao=b.total_geral - a.total_geral,
        variacao_percentual=_variacao_percentual(a.total_geral, b.total_geral),
        categorias=linhas,
    )
