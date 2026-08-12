# Relatório Fin — Relatórios do escritório

Dois relatórios, na mesma página inicial. A pessoa escolhe qual quer, sobe as
planilhas e baixa o resultado pronto.

| Relatório | Rota | Entrada | Saída |
|---|---|---|---|
| Despesas por categoria | `/despesas` | analítico de despesas ou fluxo de caixa (1 ou vários) | resumo por categoria |
| Remuneração variável | `/variavel` | visão cubo de recebimentos + relatório de casos | variável por responsável |

---

## Despesas por categoria

Sobe a planilha analítica de despesas exportada do sistema de gestão e devolve o
consolidado por categoria e subcategoria, pronto para a diretoria.

**O app não guarda nada.** Sem banco, sem histórico, sem trava de duplicado. A
planilha enviada só existe na memória durante o request e é descartada em seguida.
O mesmo arquivo pode ser enviado quantas vezes quiser, e o resultado é sempre o mesmo.

## O que faz

- Lê `.xlsx`, `.xls`, `.xlsm` e `.csv` (até 15 MB cada), com o cabeçalho em
  qualquer uma das 30 primeiras linhas.
- **Aceita várias planilhas de uma vez** e entrega um consolidado único, com uma
  coluna de valor por conta bancária mais a coluna Total.
- Detecta as colunas sozinho e deixa o usuário corrigir o mapeamento antes de processar.
- **Só considera as linhas com Débito preenchido** quando a planilha tem colunas
  Débito/Crédito — as linhas em branco são créditos (entradas), não despesas.
- Separa `CATEGORIA : SUBCATEGORIA` quando os dois níveis vêm concatenados numa
  célula só — é como o sistema de gestão exporta.
- Agrupa os lançamentos de folha sem categoria em `Despesas com Pessoal`, usando
  o beneficiário como subcategoria.
- Unifica nomes cadastrados de formas diferentes: `Guias / Custas Judiciais` e
  `Guias/Custas Judiciais` viram uma linha só.
- Mostra a prévia com categorias recolhíveis e total geral, e devolve o `.xlsx`
  consolidado com agrupamento nativo do Excel.

## Formatos de planilha suportados

| Formato | Coluna de valor | Categoria | Conta |
|---|---|---|---|
| Analítico de despesas | `Valor Líquido` (ou `Valor bruto`) | colunas `Categoria` e `Subcategoria` | `Conta Financeira` |
| Fluxo de caixa | `Débito` (só linhas preenchidas) | `Categoria / Subcategoria` numa coluna só | `Banco/Conta Financeira` |

A detecção é automática nos dois casos; o mapeamento pode ser corrigido na tela.

## Stack

| Camada | Tecnologia | Porta |
|---|---|---|
| API | Python 3.11+ · FastAPI · openpyxl · pandas | `127.0.0.1:8077` (interna) |
| Web | Next.js 16 (App Router) · TypeScript · Tailwind | `0.0.0.0:3007` |

O navegador fala só com o Next, que repassa `/api/*` para o FastAPI. A API não
precisa ficar exposta na internet e não há CORS em produção.

## Estrutura

```
backend/
  app/
    main.py              aplicação FastAPI
    config.py            configuração via ambiente
    schemas.py           schemas Pydantic
    routers/despesas.py  as três rotas da API
    services/
      texto.py           normalização e chave de unificação
      valores.py         parsing de valores (Decimal) e datas
      leitura.py         leitura bruta do arquivo enviado
      inspecao.py        detecção do cabeçalho e das colunas
      agregacao.py       agrupamento, percentuais e avisos
      planilha.py        geração do .xlsx com openpyxl
  tests/                 pytest + fixtures com dados sujos
frontend/
  src/app/               página única (arquivo → colunas → resumo)
  src/components/        dropzone, blocos, tabela de resumo, avisos
  src/lib/               cliente da API, tipos e formatação pt-BR
deploy/                  units systemd e script de deploy
```

## API

| Método | Rota | O que devolve |
|---|---|---|
| `POST` | `/api/despesas/inspecionar` | um bloco por arquivo: abas, cabeçalho detectado, mapeamento sugerido, 10 primeiras linhas |
| `POST` | `/api/despesas/processar` | resumo consolidado em JSON |
| `POST` | `/api/despesas/xlsx` | arquivo consolidado |

Documentação interativa em `/api/docs`.

As três rotas recebem os arquivos no campo `arquivos` (repetido, até 24 por vez).
O download refaz a consolidação a partir dos mesmos arquivos que o navegador
ainda tem em memória — é o preço de não guardar estado no servidor, e é barato:
a consolidação leva milissegundos.

Erro de leitura devolve `422` com mensagem em português dizendo o que fazer —
nunca um traceback.

---

## Remuneração variável

Cruza o cubo de recebimentos com o relatório de casos e calcula, por lançamento:

```
Valor dos Impostos = Valor Pago × alíquota        (padrão 17,5%, ajustável na tela)
Valor Líquido      = Valor Pago − Valor dos Impostos
Variável           = Valor Líquido × Participação do responsável
```

**Uma linha por recebimento e responsável — o NH nunca se repete para a mesma
pessoa.** Quando um recebimento cobre vários casos, o valor é dividido entre os
responsáveis na proporção de casos de cada um: quem tem 29 dos 33 casos leva
29/33. O rateio é feito em centavos exatos, então a soma das linhas é sempre
igual ao valor recebido — nenhum centavo é criado nem perdido.

Recebimentos sem caso vinculado entram na tabela sem responsável e com variável
zerada, para o total continuar batendo com o cubo. Eles aparecem nos avisos.

### O formato do cubo

O sistema exporta a visão cubo como **SpreadsheetML 2003** — XML com extensão
`.xls`, que nem o Excel-padrão das bibliotecas abre. Daí o leitor próprio em
`services/spreadsheetml.py`. O arquivo ainda tem três armadilhas:

- **sem linha de cabeçalho** — as colunas vêm na ordem fixa do sistema;
- **valores em texto**, no formato `valor: 3000.00`;
- **células mescladas verticalmente** quando um recebimento cobre vários casos:
  o recebimento aparece uma vez só e os casos descem em linhas próprias. O
  parser resolve as mesclas e preenche as linhas de baixo.

A coluna **Área** do relatório de casos é opcional: sem ela, o relatório sai com
a coluna em branco em vez de falhar.

---

## Decisões que valem saber

- **`Decimal` em todo o caminho, nunca `float`.** Arredondamento só na apresentação.
- **`CATEGORIA:SUBCATEGORIA` é cortado no primeiro `:`.** Quando a planilha tem
  coluna de subcategoria própria, ela tem prioridade sobre a separação.
- **Transferências entre contas entram como despesa**, na categoria
  `Transferência para`. Foi decisão do escritório: elas saíram do caixa e devem
  aparecer. Se um dia mudar, o lugar é `extrair_linhas`.
- **A coluna por conta só aparece quando há mais de uma conta.** Com uma só,
  ela seria idêntica à coluna Total.
- **`summaryBelow = False`** na aba `Resumo`: sem isso o `+/−` da lateral do
  Excel aparece na linha errada.
- **Ordenação pt-BR sem `locale`**: comparar o texto sem acento põe `Á` junto de
  `A`, portanto antes de `B`, sem depender de locale instalado no servidor.

## Rodar em desenvolvimento

```bash
# API
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8077

# Web (outro terminal)
cd frontend
npm install
npm run dev            # http://localhost:3007
```

## Testes

```bash
cd backend && .venv/bin/python -m pytest -q
```

90 testes cobrindo os dois formatos de planilha: parsing de valores, unificação
de nomes, separação de `CATEGORIA : SUBCATEGORIA`, filtro por coluna Débito,
folha sem categoria, totais por conta bancária, consolidado de vários arquivos,
detecção de cabeçalho fora da linha 1, linha com valor vazio no meio da base,
geração da planilha e as rotas da API.

O mais importante é `test_invariante_principal_soma_do_resumo_bate_com_a_base`:
a soma do resumo tem que bater, centavo a centavo, com a base analítica. As
fixtures `.xlsx` são geradas por `tests/fixture_builder.py` e trazem de propósito
os casos sujos (três variantes de "Guias/Custas Judiciais", linha sem valor,
lançamento sem categoria, subcategoria com `;`, categoria concatenada com `:`).

## Deploy no servidor

Ver [`deploy/README.md`](deploy/README.md).

## Fora de escopo

Autenticação, histórico e comparação de períodos, edição de categorias pela tela,
importação automática do sistema de gestão, gráficos, exportação em PDF e
multi-empresa.
