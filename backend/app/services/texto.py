"""Normalização de texto — base da detecção de cabeçalho e da unificação de nomes."""

from __future__ import annotations

import re
import unicodedata

_ESPACOS = re.compile(r"\s+")
_EM_VOLTA_DE_SEPARADOR = re.compile(r"\s*([/-])\s*")


def sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizar(valor: object) -> str:
    """Sem acento, minúsculo, espaços colapsados. Usado para comparar cabeçalhos."""
    if valor is None:
        return ""
    texto = str(valor)
    texto = texto.replace(" ", " ")
    texto = sem_acento(texto).lower()
    return _ESPACOS.sub(" ", texto).strip()


def chave_agrupamento(valor: object) -> str:
    """Chave de unificação: `normalizar` + espaços em volta de `/` e `-` removidos.

    "Guias / Custas Judiciais" e "Guias/Custas Judiciais" caem na mesma chave.
    """
    return _EM_VOLTA_DE_SEPARADOR.sub(r"\1", normalizar(valor))


def chave_ordenacao(rotulo: str) -> tuple[str, str]:
    """Ordenação alfabética pt-BR sem depender de locale instalado no servidor.

    Comparar o texto sem acento faz `Á` cair junto de `A`, portanto antes de `B`.
    O rótulo original entra como desempate para manter a ordem estável.
    """
    return (sem_acento(rotulo).lower(), rotulo)
