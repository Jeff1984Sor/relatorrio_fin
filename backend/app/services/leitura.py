"""Leitura bruta do arquivo enviado — devolve linhas, sem interpretar nada."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd

from .. import config


class ArquivoIlegivel(Exception):
    """Erro de leitura já com mensagem pronta para o usuário final."""

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


MSG_GENERICA = (
    "Não foi possível ler o arquivo. Exporte novamente em .xlsx e tente de novo."
)


def extensao(nome_arquivo: str) -> str:
    return Path(nome_arquivo).suffix.lower()


def validar_upload(nome_arquivo: str, tamanho: int) -> None:
    ext = extensao(nome_arquivo)
    if ext not in config.EXTENSOES_ACEITAS:
        aceitas = ", ".join(sorted(config.EXTENSOES_ACEITAS))
        raise ArquivoIlegivel(
            f"Formato {ext or 'desconhecido'} não é aceito. Envie um arquivo {aceitas}."
        )
    if tamanho > config.MAX_UPLOAD_BYTES:
        raise ArquivoIlegivel(
            f"O arquivo tem {tamanho / 1024 / 1024:.1f} MB e o limite é "
            f"{config.MAX_UPLOAD_MB} MB. Exporte um período menor e tente de novo."
        )
    if tamanho == 0:
        raise ArquivoIlegivel("O arquivo está vazio. Exporte novamente e tente de novo.")


def _motor_excel(ext: str) -> str:
    return "xlrd" if ext == ".xls" else "openpyxl"


def listar_abas(conteudo: bytes, nome_arquivo: str) -> list[str]:
    ext = extensao(nome_arquivo)
    if ext == ".csv":
        return ["CSV"]
    try:
        arquivo = pd.ExcelFile(io.BytesIO(conteudo), engine=_motor_excel(ext))
        return [str(nome) for nome in arquivo.sheet_names]
    except Exception as exc:  # noqa: BLE001 - qualquer falha vira mensagem amigável
        raise ArquivoIlegivel(MSG_GENERICA) from exc


def _decodificar(conteudo: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return conteudo.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ArquivoIlegivel(
        "Não foi possível identificar a codificação do CSV. "
        "Salve o arquivo como UTF-8 ou exporte em .xlsx."
    )


def _ler_csv(conteudo: bytes) -> list[list[object]]:
    texto = _decodificar(conteudo)
    amostra = texto[:8192]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=";,\t|")
        separador = dialeto.delimiter
    except csv.Error:
        separador = ";" if amostra.count(";") > amostra.count(",") else ","

    leitor = csv.reader(io.StringIO(texto), delimiter=separador)
    return [list(linha) for linha in leitor]


def ler_linhas(
    conteudo: bytes, nome_arquivo: str, aba: str | None = None
) -> tuple[list[list[object]], str]:
    """Devolve (linhas, nome_da_aba). Nenhuma linha é descartada nem convertida."""
    ext = extensao(nome_arquivo)

    if ext == ".csv":
        return _ler_csv(conteudo), "CSV"

    try:
        alvo = aba if aba else 0
        df = pd.read_excel(
            io.BytesIO(conteudo),
            sheet_name=alvo,
            header=None,
            dtype=object,
            engine=_motor_excel(ext),
        )
    except ArquivoIlegivel:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ArquivoIlegivel(MSG_GENERICA) from exc

    if isinstance(df, dict):  # pandas devolve dict quando sheet_name é None
        nome_aba, df = next(iter(df.items()))
    else:
        nome_aba = aba or (listar_abas(conteudo, nome_arquivo) or ["Planilha1"])[0]

    df = df.where(pd.notna(df), None)
    linhas = [list(linha) for linha in df.itertuples(index=False, name=None)]
    return linhas, str(nome_aba)
