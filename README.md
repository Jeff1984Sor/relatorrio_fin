# Relatório Fin — Agrupador de Despesas por Categoria

Sobe a planilha analítica de despesas exportada do sistema de gestão e devolve o
consolidado por categoria e subcategoria, pronto para a diretoria.

**O app não guarda nada.** Sem banco, sem histórico, sem trava de duplicado. A
planilha enviada só existe na memória durante o request e é descartada em seguida.
O mesmo arquivo pode ser enviado quantas vezes quiser, e o resultado é sempre o mesmo.

## O que faz

- Lê `.xlsx`, `.xls`, `.xlsm` e `.csv` (até 15 MB), com o cabeçalho em qualquer
  uma das 30 primeiras linhas.
- Detecta as colunas sozinho e deixa o usuário corrigir o mapeamento antes de processar.
- Separa `CATEGORIA:SUBCATEGORIA` quando os dois níveis vêm concatenados numa
  célula só — é como o sistema de gestão exporta.
- Unifica nomes cadastrados de formas diferentes: `Guias / Custas Judiciais` e
  `Guias/Custas Judiciais` viram uma linha só.
- Mostra a prévia com categorias recolhíveis e total geral, e devolve o `.xlsx`
  consolidado com agrupamento nativo do Excel.

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
| `POST` | `/api/despesas/inspecionar` | abas, cabeçalho detectado, mapeamento sugerido, 10 primeiras linhas |
| `POST` | `/api/despesas/processar` | resumo em JSON |
| `POST` | `/api/despesas/xlsx` | arquivo consolidado |

Documentação interativa em `/api/docs`.

As três rotas recebem o arquivo. O download refaz a consolidação a partir do
mesmo arquivo que o navegador ainda tem em memória — é o preço de não guardar
estado no servidor, e é barato: a consolidação leva milissegundos.

Erro de leitura devolve `422` com mensagem em português dizendo o que fazer —
nunca um traceback.

## Decisões que valem saber

- **`Decimal` em todo o caminho, nunca `float`.** Arredondamento só na apresentação.
- **`CATEGORIA:SUBCATEGORIA` é cortado no primeiro `:`.** Quando a planilha tem
  coluna de subcategoria própria, ela tem prioridade sobre a separação.
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

76 testes cobrindo parsing de valores, unificação de nomes, separação de
`CATEGORIA:SUBCATEGORIA`, detecção de cabeçalho fora da linha 1, planilha sem
subcategoria, linha com valor vazio no meio da base, geração da planilha e as
rotas da API.

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
