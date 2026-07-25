"""Ponte entre o resumo calculado e o que fica guardado no banco."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..models import Processamento, ProcessamentoLinha
from .agregacao import Opcoes, Resumo


def salvar(
    db: Session,
    resumo: Resumo,
    nome_arquivo: str,
    hash_arquivo: str,
    opcoes: Opcoes,
    criado_por: str,
) -> Processamento:
    processamento = Processamento(
        criado_por=criado_por,
        nome_arquivo=nome_arquivo,
        hash_arquivo=hash_arquivo,
        periodo_inicio=resumo.periodo_inicio,
        periodo_fim=resumo.periodo_fim,
        total_geral=resumo.total_geral,
        qtd_lancamentos=resumo.qtd_lancamentos,
        opcoes=opcoes.to_dict(),
        avisos=[a.to_dict() for a in resumo.avisos],
    )

    # Guardamos uma linha por (categoria, subcategoria). O total da categoria é
    # a soma delas — não há dado redundante nem a base analítica no banco.
    for categoria in resumo.categorias:
        for sub in categoria.subcategorias:
            processamento.linhas.append(
                ProcessamentoLinha(
                    categoria=categoria.rotulo,
                    subcategoria=sub.rotulo,
                    categoria_key=categoria.chave,
                    subcategoria_key=sub.chave,
                    total=sub.total,
                    qtd=sub.qtd,
                )
            )

    db.add(processamento)
    db.commit()
    db.refresh(processamento)
    return processamento


def caminho_xlsx(processamento_id: int) -> Path:
    return config.STORAGE_DIR / f"{processamento_id}.xlsx"


def guardar_xlsx(processamento_id: int, conteudo: bytes) -> None:
    config.garantir_diretorios()
    caminho_xlsx(processamento_id).write_bytes(conteudo)


def buscar_por_hash(db: Session, hash_arquivo: str) -> Processamento | None:
    consulta = (
        select(Processamento)
        .where(Processamento.hash_arquivo == hash_arquivo)
        .order_by(Processamento.id.desc())
        .limit(1)
    )
    return db.scalars(consulta).first()


def montar_categorias(processamento: Processamento) -> list[dict]:
    """Reconstrói a árvore categoria → subcategorias a partir das linhas salvas."""
    ordem: list[str] = []
    agrupado: dict[str, dict] = {}

    for linha in processamento.linhas:
        if linha.categoria_key not in agrupado:
            ordem.append(linha.categoria_key)
            agrupado[linha.categoria_key] = {
                "rotulo": linha.categoria,
                "chave": linha.categoria_key,
                "total": Decimal("0"),
                "qtd": 0,
                "subcategorias": [],
            }
        no = agrupado[linha.categoria_key]
        no["total"] += linha.total
        no["qtd"] += linha.qtd
        no["subcategorias"].append(
            {
                "rotulo": linha.subcategoria or "",
                "chave": linha.subcategoria_key or "",
                "total": linha.total,
                "qtd": linha.qtd,
                "percentual": 0.0,
            }
        )

    total_geral = processamento.total_geral
    categorias = []
    for chave in ordem:
        no = agrupado[chave]
        no["percentual"] = float(no["total"] / total_geral) if total_geral else 0.0
        for sub in no["subcategorias"]:
            sub["percentual"] = float(sub["total"] / no["total"]) if no["total"] else 0.0
        categorias.append(no)
    return categorias
