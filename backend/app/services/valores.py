"""Parsing de valores monetários e datas vindos da planilha analítica."""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal, InvalidOperation

_SO_NUMERO = re.compile(r"[^0-9,.\-]")
_EPOCH_EXCEL = dt.date(1899, 12, 30)  # o Excel considera 1900 bissexto; 30/12/1899 corrige


def parse_valor(bruto: object) -> Decimal | None:
    """Converte a célula em Decimal. Devolve None quando não há valor utilizável.

    Aceita número puro ou texto formatado:
        "(R$ 4.117,00)" → -4117.00   (parênteses = negativo, padrão contábil)
        "R$ 7.901,36"   →  7901.36
        "-1.234,56"     → -1234.56
        "1234.56"       →  1234.56
        ""/None         →  None
    """
    if bruto is None:
        return None

    if isinstance(bruto, bool):
        return None

    if isinstance(bruto, Decimal):
        return bruto
    if isinstance(bruto, int):
        return Decimal(bruto)
    if isinstance(bruto, float):
        if bruto != bruto:  # NaN
            return None
        return Decimal(str(bruto))

    texto = str(bruto).replace(" ", " ").strip()
    if not texto:
        return None

    negativo = False
    if texto.startswith("(") and texto.endswith(")"):
        negativo = True
        texto = texto[1:-1].strip()

    # Sinal solto antes ou depois do símbolo de moeda: "-R$ 10", "R$ -10".
    limpo = _SO_NUMERO.sub("", texto)
    if not limpo:
        return None

    if limpo.startswith("-"):
        negativo = not negativo
    limpo = limpo.replace("-", "")

    if "," in limpo:
        # Havendo vírgula, o ponto só pode ser separador de milhar.
        limpo = limpo.replace(".", "").replace(",", ".")

    if limpo.count(".") > 1:
        # "1.234.567" sem vírgula: pontos são milhar.
        limpo = limpo.replace(".", "")

    if not limpo or limpo == ".":
        return None

    try:
        valor = Decimal(limpo)
    except InvalidOperation:
        return None

    return -valor if negativo else valor


def parse_data(bruto: object) -> dt.date | None:
    """Aceita datetime, serial do Excel ou texto dd/mm/aaaa (e variantes)."""
    if bruto is None:
        return None

    if isinstance(bruto, dt.datetime):
        return bruto.date()
    if isinstance(bruto, dt.date):
        return bruto

    if isinstance(bruto, bool):
        return None

    if isinstance(bruto, (int, float, Decimal)):
        serial = float(bruto)
        if serial != serial or not (1 <= serial <= 2958465):
            return None
        return _EPOCH_EXCEL + dt.timedelta(days=int(serial))

    texto = str(bruto).strip()
    if not texto:
        return None

    # Um serial que veio como texto.
    if re.fullmatch(r"\d{5}", texto):
        return _EPOCH_EXCEL + dt.timedelta(days=int(texto))

    texto = texto.split(" ")[0]
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return dt.datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def texto_celula(bruto: object) -> str:
    """Texto limpo da célula, preservando acentuação e caixa (vira rótulo exibido)."""
    if bruto is None:
        return ""
    if isinstance(bruto, float) and bruto != bruto:
        return ""
    return re.sub(r"\s+", " ", str(bruto).replace(" ", " ")).strip()
