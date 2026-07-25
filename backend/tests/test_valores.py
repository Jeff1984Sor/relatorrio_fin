import datetime as dt
from decimal import Decimal

import pytest

from app.services.valores import parse_data, parse_valor


@pytest.mark.parametrize(
    "bruto,esperado",
    [
        ("(R$ 4.117,00)", Decimal("-4117.00")),
        ("R$ 7.901,36", Decimal("7901.36")),
        ("-1.234,56", Decimal("-1234.56")),
        ("1234.56", Decimal("1234.56")),
        ("R$ 0,00", Decimal("0.00")),
        ("", None),
        (None, None),
    ],
)
def test_exemplos_do_escopo(bruto, esperado):
    assert parse_valor(bruto) == esperado


@pytest.mark.parametrize(
    "bruto,esperado",
    [
        (-300.25, Decimal("-300.25")),
        (0, Decimal("0")),
        (Decimal("-1.5"), Decimal("-1.5")),
        ("  R$ -10,00 ", Decimal("-10.00")),
        ("-R$ 10,00", Decimal("-10.00")),
        ("(1.000,00)", Decimal("-1000.00")),
        ("1.234.567,89", Decimal("1234567.89")),
        ("1.234.567", Decimal("1234567")),
        ("   ", None),
        ("n/a", None),
        ("-", None),
    ],
)
def test_variacoes_de_formato(bruto, esperado):
    assert parse_valor(bruto) == esperado


def test_float_nao_e_usado_no_resultado():
    assert isinstance(parse_valor("R$ 0,10"), Decimal)
    assert parse_valor("R$ 0,10") + parse_valor("R$ 0,20") == Decimal("0.30")


@pytest.mark.parametrize(
    "bruto,esperado",
    [
        ("05/01/2026", dt.date(2026, 1, 5)),
        ("2026-01-05", dt.date(2026, 1, 5)),
        (dt.datetime(2026, 1, 5, 10, 30), dt.date(2026, 1, 5)),
        (46027, dt.date(2026, 1, 5)),
        ("", None),
        (None, None),
        ("não é data", None),
    ],
)
def test_parse_data(bruto, esperado):
    assert parse_data(bruto) == esperado
