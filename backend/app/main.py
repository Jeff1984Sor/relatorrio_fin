"""Aplicação FastAPI."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config
from .routers import despesas

logger = logging.getLogger("relatorio_fin")

app = FastAPI(
    title="Relatório Financeiro — Agrupador de Despesas",
    version="2.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def erro_inesperado(request: Request, exc: Exception) -> JSONResponse:
    """Nenhum traceback chega à tela — o detalhe fica no log do servidor."""
    logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro inesperado ao processar a solicitação. "
            "Tente de novo; se continuar, avise o suporte."
        },
    )


@app.get("/api/saude", tags=["infra"])
def saude() -> dict:
    return {"status": "ok"}


app.include_router(despesas.router)
