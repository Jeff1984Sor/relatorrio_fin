# Relatório Fin — Agrupador de Despesas por Categoria

Sobe a planilha analítica de despesas exportada do sistema de gestão e devolve o
consolidado por categoria e subcategoria, pronto para a diretoria.

## O que faz

- Lê `.xlsx`, `.xls`, `.xlsm` e `.csv` (até 15 MB), com o cabeçalho em qualquer
  uma das 30 primeiras linhas.
- Detecta as colunas sozinho e deixa o usuário corrigir o mapeamento antes de processar.
- Unifica nomes cadastrados de formas diferentes — `Guias / Custas Judiciais` e
  `Guias/Custas Judiciais` viram uma linha só.
- Mostra a prévia com categorias recolhíveis e devolve o `.xlsx` consolidado com
  agrupamento nativo do Excel.
- Guarda o histórico dos processamentos e compara dois períodos.

## Stack

| Camada | Tecnologia | Porta |
|---|---|---|
| API | Python 3.11+ · FastAPI · openpyxl · pandas | `127.0.0.1:8077` (interna) |
| Banco | SQLite (arquivo em `backend/data/`) | — |
| Web | Next.js 16 (App Router) · TypeScript · Tailwind | `0.0.0.0:3007` |

O navegador fala só com o Next, que repassa `/api/*` para o FastAPI. A API não
precisa ficar exposta na internet e não há CORS em produção.

## Estrutura

```
backend/
  app/
    main.py              aplicação FastAPI
    config.py            configuração via ambiente
    database.py          engine e sessão SQLite
    models.py            Processamento e ProcessamentoLinha
    schemas.py           schemas Pydantic
    routers/despesas.py  as seis rotas da API
    services/
      texto.py           normalização e chave de unificação
      valores.py         parsing de valores (Decimal) e datas
      leitura.py         leitura bruta do arquivo enviado
      inspecao.py        detecção do cabeçalho e das colunas
      agregacao.py       agrupamento, percentuais e avisos
      planilha.py        geração do .xlsx com openpyxl
      persistencia.py    ponte entre o resumo e o banco
  tests/                 pytest + fixture com dados sujos
frontend/
  src/app/               páginas (upload e histórico)
  src/components/        dropzone, blocos, tabela de resumo, avisos
  src/lib/               cliente da API, tipos e formatação pt-BR
deploy/                  units systemd e script de deploy
```

## API

| Método | Rota | O que devolve |
|---|---|---|
| `POST` | `/api/despesas/inspecionar` | abas, cabeçalho detectado, mapeamento sugerido, 10 primeiras linhas |
| `POST` | `/api/despesas/processar` | resumo em JSON + `processamento_id` |
| `GET` | `/api/despesas/{id}` | resumo salvo |
| `GET` | `/api/despesas/{id}/xlsx` | arquivo consolidado |
| `GET` | `/api/despesas` | histórico paginado |
| `GET` | `/api/despesas/comparar?a={id}&b={id}` | variação por categoria e subcategoria |

Documentação interativa em `/api/docs`.

Erro de leitura devolve `422` com mensagem em português dizendo o que fazer —
nunca um traceback. Arquivo já processado devolve `409` com o id anterior, e o
usuário escolhe entre abrir o resultado antigo ou processar de novo.

## Decisões que valem saber

- **`Decimal` em todo o caminho, nunca `float`.** No SQLite os valores são
  guardados como texto (`DecimalTexto` em `models.py`) porque o SQLite não tem
  `NUMERIC` de verdade e converteria para float, perdendo centavos.
- **Só o consolidado vai para o banco**, não a base analítica. O `.xlsx` gerado
  fica em `backend/data/arquivos/{id}.xlsx` para o download não precisar
  reprocessar (e porque a aba `Detalhado` precisa da base, que não é persistida).
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

64 testes cobrindo parsing de valores, unificação de nomes, detecção de cabeçalho
fora da linha 1, planilha sem subcategoria, linha com valor vazio no meio da base,
geração da planilha e as rotas da API.

O teste mais importante é `test_invariante_principal_soma_do_resumo_bate_com_a_base`:
a soma do resumo tem que bater, centavo a centavo, com a base analítica. A fixture
`.xlsx` é gerada automaticamente por `tests/fixture_builder.py` e traz de propósito
os casos sujos (três variantes de "Guias/Custas Judiciais", linha sem valor,
lançamento sem categoria, subcategoria com `;`).

## Deploy no servidor

Ver [`deploy/README.md`](deploy/README.md).

## Fora de escopo nesta versão

Autenticação, edição de categorias pela tela, importação automática do sistema de
gestão, gráficos, exportação em PDF e multi-empresa.
