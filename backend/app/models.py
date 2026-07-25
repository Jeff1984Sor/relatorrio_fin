"""Modelo de dados. Guardamos apenas o consolidado, nunca a base analítica."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class DecimalTexto(TypeDecorator):
    """Decimal persistido como TEXT.

    O SQLite não tem NUMERIC de verdade — SQLAlchemy converteria para float e
    perderíamos centavos. Guardando o texto da representação decimal o valor
    volta idêntico ao que entrou.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect) -> str | None:
        if value is None:
            return None
        return str(Decimal(str(value)).quantize(Decimal("0.01")))

    def process_result_value(self, value: Any, dialect) -> Decimal | None:
        if value is None:
            return None
        return Decimal(value)


class JSONTexto(TypeDecorator):
    """jsonb do Postgres → TEXT com JSON no SQLite."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, default=str)

    def process_result_value(self, value: Any, dialect) -> Any:
        if value is None:
            return None
        return json.loads(value)


class Processamento(Base):
    __tablename__ = "processamento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    criado_por: Mapped[str] = mapped_column(String(120), nullable=False)
    nome_arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    hash_arquivo: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    periodo_inicio: Mapped[date | None] = mapped_column(nullable=True)
    periodo_fim: Mapped[date | None] = mapped_column(nullable=True)

    total_geral: Mapped[Decimal] = mapped_column(DecimalTexto(20), nullable=False)
    qtd_lancamentos: Mapped[int] = mapped_column(Integer, nullable=False)

    opcoes: Mapped[dict] = mapped_column(JSONTexto, nullable=False, default=dict)
    avisos: Mapped[list] = mapped_column(JSONTexto, nullable=False, default=list)

    linhas: Mapped[list["ProcessamentoLinha"]] = relationship(
        back_populates="processamento",
        cascade="all, delete-orphan",
        order_by="ProcessamentoLinha.id",
    )


class ProcessamentoLinha(Base):
    __tablename__ = "processamento_linha"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    processamento_id: Mapped[int] = mapped_column(
        ForeignKey("processamento.id", ondelete="CASCADE"), nullable=False
    )

    categoria: Mapped[str] = mapped_column(String(255), nullable=False)
    subcategoria: Mapped[str | None] = mapped_column(String(255), nullable=True)
    categoria_key: Mapped[str] = mapped_column(String(255), nullable=False)
    subcategoria_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    total: Mapped[Decimal] = mapped_column(DecimalTexto(20), nullable=False)
    qtd: Mapped[int] = mapped_column(Integer, nullable=False)

    processamento: Mapped[Processamento] = relationship(back_populates="linhas")


Index(
    "ix_linha_proc_categoria",
    ProcessamentoLinha.processamento_id,
    ProcessamentoLinha.categoria_key,
    ProcessamentoLinha.subcategoria_key,
)
