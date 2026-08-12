"""Leitor de SpreadsheetML 2003 — o XML que o sistema exporta com extensão `.xls`.

O arquivo começa com `<?xml ...?><?mso-application progid="Excel.Sheet"?>` e nem
o xlrd nem o openpyxl abrem. Como o formato é simples (Workbook > Worksheet >
Table > Row > Cell > Data), vale mais um parser próprio do que uma dependência.

Duas particularidades do formato que o parser precisa respeitar:

- `ss:Index` numa célula pula colunas vazias, então a posição não pode ser
  inferida pela contagem de células.
- `ss:MergeAcross` / `ss:MergeDown` marcam as células mescladas, que no XML
  aparecem uma única vez e precisam ser replicadas para as posições cobertas.
"""

from __future__ import annotations

import datetime as dt
import xml.etree.ElementTree as ET

NS = {
    "ss": "urn:schemas-microsoft-com:office:spreadsheet",
    "o": "urn:schemas-microsoft-com:office:office",
}

PREFIXO_XML = b"<?xml"
MARCA_EXCEL = b"mso-application"


def parece_spreadsheetml(conteudo: bytes) -> bool:
    inicio = conteudo[:400].lstrip()
    return inicio.startswith(PREFIXO_XML) and MARCA_EXCEL in conteudo[:400]


def _converter(celula: ET.Element) -> object:
    dado = celula.find("ss:Data", NS)
    if dado is None:
        return None

    texto = "".join(dado.itertext())
    tipo = dado.get(f"{{{NS['ss']}}}Type", "String")

    if texto == "":
        return None
    if tipo == "Number":
        try:
            numero = float(texto)
        except ValueError:
            return texto
        return int(numero) if numero.is_integer() else numero
    if tipo == "DateTime":
        for formato in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return dt.datetime.strptime(texto, formato)
            except ValueError:
                continue
        return texto
    if tipo == "Boolean":
        return texto not in ("0", "false")
    return texto


def _linhas_da_tabela(tabela: ET.Element) -> list[list[object]]:
    linhas: list[list[object]] = []
    # Coluna → (valor, quantas linhas ABAIXO desta ainda são cobertas pela mescla).
    pendentes: dict[int, tuple[object, int]] = {}
    indice_linha = 0

    for elemento in tabela.findall("ss:Row", NS):
        indice_declarado = elemento.get(f"{{{NS['ss']}}}Index")
        if indice_declarado:
            # Linhas puladas continuam existindo, só que vazias.
            while indice_linha < int(indice_declarado) - 1:
                linhas.append(_herdar(pendentes))
                indice_linha += 1

        # A linha começa com o que veio das mesclas de cima; as células próprias
        # sobrescrevem em seguida.
        linha = _herdar(pendentes)
        novas: dict[int, tuple[object, int]] = {}
        coluna = 0

        for celula in elemento.findall("ss:Cell", NS):
            indice_coluna = celula.get(f"{{{NS['ss']}}}Index")
            if indice_coluna:
                coluna = int(indice_coluna) - 1

            valor = _converter(celula)
            largura = int(celula.get(f"{{{NS['ss']}}}MergeAcross", 0))
            altura = int(celula.get(f"{{{NS['ss']}}}MergeDown", 0))

            for deslocamento in range(largura + 1):
                posicao = coluna + deslocamento
                while len(linha) <= posicao:
                    linha.append(None)
                linha[posicao] = valor
                if altura:
                    novas[posicao] = (valor, altura)

            coluna += largura + 1

        pendentes.update(novas)
        linhas.append(linha)
        indice_linha += 1

    return linhas


def _herdar(pendentes: dict[int, tuple[object, int]]) -> list[object]:
    """Monta a linha com os valores das mesclas verticais abertas acima.

    Cada uso consome uma das linhas restantes da mescla; quando acaba, some.
    """
    linha: list[object] = []
    for coluna in sorted(pendentes):
        valor, restantes = pendentes[coluna]
        while len(linha) <= coluna:
            linha.append(None)
        linha[coluna] = valor
        pendentes[coluna] = (valor, restantes - 1)

    for coluna in [c for c, (_valor, restantes) in pendentes.items() if restantes <= 0]:
        del pendentes[coluna]
    return linha


def listar_abas(conteudo: bytes) -> list[str]:
    raiz = ET.fromstring(conteudo)
    return [
        planilha.get(f"{{{NS['ss']}}}Name", f"Planilha{i + 1}")
        for i, planilha in enumerate(raiz.findall("ss:Worksheet", NS))
    ]


def ler(conteudo: bytes, aba: str | None = None) -> tuple[list[list[object]], str]:
    """Devolve (linhas, nome da aba). Sem cabeçalho: as linhas vêm como estão."""
    raiz = ET.fromstring(conteudo)
    planilhas = raiz.findall("ss:Worksheet", NS)
    if not planilhas:
        return [], ""

    escolhida = planilhas[0]
    if aba:
        for candidata in planilhas:
            if candidata.get(f"{{{NS['ss']}}}Name") == aba:
                escolhida = candidata
                break

    nome = escolhida.get(f"{{{NS['ss']}}}Name", "Planilha1")
    tabela = escolhida.find("ss:Table", NS)
    if tabela is None:
        return [], nome
    return _linhas_da_tabela(tabela), nome
