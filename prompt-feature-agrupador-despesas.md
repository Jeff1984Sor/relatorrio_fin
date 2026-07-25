# Feature: Agrupador de Despesas por Categoria

> Prompt de implementação. Leia inteiro antes de escrever qualquer linha de código.
> Ao final, entregue um resumo do que foi feito e o que ficou pendente — não invente escopo além do descrito.

---

## 1. Contexto

O escritório exporta do sistema de gestão financeira uma planilha analítica de despesas: uma linha por lançamento pago. Hoje alguém monta manualmente, no Excel, um resumo agrupado por categoria e subcategoria — tarefa repetitiva, propensa a erro e refeita todo mês.

A feature substitui esse trabalho manual: o usuário sobe a planilha analítica e recebe de volta a planilha consolidada, pronta para leitura da diretoria.

**Formato da planilha de entrada** (cabeçalho pode não estar na primeira linha):

| Coluna | Observação |
|---|---|
| Data de Pagamento | `dd/mm/aaaa` ou serial do Excel |
| Data de Vencimento | idem |
| Conta Financeira | texto |
| Fornecedor | texto |
| Valor bruto | despesa, negativo |
| Multa + Juros - Desconto | costuma vir zerado |
| Impostos | costuma vir zerado |
| **Valor Líquido** | **é este que consolida** |
| **Categoria** | chave do agrupamento |
| **Subcategoria** | chave do agrupamento |

Categorias que aparecem hoje: `DESPESA COM PESSOAL`, `DESPESAS ADMINISTRATIVAS`, `DESPESAS FINANCEIRAS`, `DESPESAS NÃO REEMBOLSÁVEIS`, `DESPESAS REEMBOLSÁVEIS`, `DIRETORIA`, `IMPOSTOS`. **Não fixe essa lista no código** — ela muda; o agrupamento é dinâmico.

**Formato da planilha de saída**: uma linha de faixa por categoria com o total, abaixo dela as subcategorias com seus totais, e um total geral no fim.

---

## 2. Stack e ambiente

- Backend: **Python 3.11 + FastAPI**, `openpyxl` para escrita e `pandas` + `openpyxl` para leitura.
- Banco: **PostgreSQL** (já rodando no prod2).
- Frontend: **Next.js (App Router) + TypeScript**, Tailwind.
- Execução: **tudo roda no prod2 (GCP, usuário `mayacorp22`)**. Não rode nem instale nada na máquina local — o código é editado localmente e executado no servidor. Migrations, testes e servidor de dev: sempre no prod2.
- Não adicione Celery, Redis, fila ou worker nesta versão. Processamento é síncrono no request.

---

## 3. Escopo da v1

1. Upload de arquivo `.xlsx`, `.xls`, `.xlsm` ou `.csv` (limite 15 MB).
2. Detecção automática do cabeçalho e das colunas, com possibilidade de o usuário corrigir o mapeamento antes de processar.
3. Prévia do resumo na tela, com categorias recolhíveis.
4. Download do `.xlsx` consolidado.
5. Histórico dos processamentos, com comparação entre dois períodos.

---

## 4. Regras de negócio (a parte que importa)

### 4.1 Detecção do cabeçalho
Varra as 30 primeiras linhas e escolha a de maior pontuação: `categoria` = 4 pontos, `subcategoria` = 3, começa com `valor` = 2, `fornecedor` ou `data de` = 1. Compare sempre com o texto normalizado (sem acento, minúsculo, espaços colapsados).

### 4.2 Mapeamento de colunas
Preferência de casamento, na ordem: `valor líquido` → `valor bruto` → primeira coluna que comece com `valor`. Retorne o mapeamento detectado para a tela e aceite override do usuário no processamento.

### 4.3 Parsing de valores
A célula pode vir como número **ou** como texto formatado. Trate todos estes casos:

```
"(R$ 4.117,00)"  → -4117.00     # parênteses = negativo (padrão contábil)
"R$ 7.901,36"    →  7901.36
"-1.234,56"      → -1234.56
"1234.56"        →  1234.56
"R$ 0,00"        →  0.00
""  / None       →  None        # não entra no total, entra nos avisos
```

Regra: se houver vírgula, o ponto é separador de milhar. Use `Decimal` no backend — nunca `float` — e arredonde para 2 casas só na apresentação.

### 4.4 Unificação de nomes (ligada por padrão, com toggle)
A base tem o mesmo nome cadastrado de formas diferentes e isso **quebra o consolidado hoje**. A chave de agrupamento é o nome normalizado: sem acento, minúsculo, espaços colapsados e **espaços em volta de `/` e `-` removidos**.

```
"Guias / Custas Judiciais"  ┐
"Guias/Custas Judiciais"    ├→ mesma chave: "guias/custas judiciais"
"GUIAS / CUSTAS JUDICIAIS"  ┘
```

O rótulo exibido é a **variante mais frequente** no arquivo, não a primeira encontrada.

### 4.5 Agrupamento
- Categoria vazia → grupo `SEM CATEGORIA`. Subcategoria vazia → `(sem subcategoria)`.
- Para cada categoria: total, quantidade de lançamentos, % sobre o total geral.
- Para cada subcategoria: total, quantidade, % sobre o total **da sua categoria**.
- Ordenação alfabética (`pt-BR`, locale correto — `Á` antes de `B`) ou por maior valor absoluto, escolhida pelo usuário.
- Toggle "mostrar valores como positivos": inverte o sinal na apresentação e na planilha, sem alterar o dado guardado.

### 4.6 Avisos de conferência
Retorne e exiba, sem bloquear o processamento:
- lançamentos sem categoria (quantos);
- linhas com valor vazio ou não numérico (quantas, e quais linhas);
- subcategorias contendo `;` — erro de cadastro real na base, ex.: `BPO Financeiro; DESPESAS ADMINISTRATIVAS`;
- subcategoria com nome idêntico ao de uma categoria.

---

## 5. Modelo de dados

```
Processamento
  id, criado_em, criado_por, nome_arquivo, hash_arquivo (sha256),
  periodo_inicio, periodo_fim, total_geral (numeric 14,2),
  qtd_lancamentos, opcoes (jsonb: unificar, positivo, ordem, mapeamento),
  avisos (jsonb)

ProcessamentoLinha
  id, processamento_id (FK, on delete cascade),
  categoria, subcategoria,           # rótulo exibido
  categoria_key, subcategoria_key,   # chave normalizada
  total (numeric 14,2), qtd

índice: (processamento_id, categoria_key, subcategoria_key)
```

Guarde apenas o consolidado, não a base analítica. Se o `hash_arquivo` já existir, avise que o arquivo já foi processado e ofereça abrir o resultado anterior em vez de duplicar.

---

## 6. API

| Método | Rota | Retorno |
|---|---|---|
| `POST` | `/api/despesas/inspecionar` | abas, cabeçalho detectado, mapeamento sugerido, 10 primeiras linhas |
| `POST` | `/api/despesas/processar` | resumo em JSON + `processamento_id` |
| `GET` | `/api/despesas/{id}` | resumo salvo |
| `GET` | `/api/despesas/{id}/xlsx` | arquivo pronto (`StreamingResponse`) |
| `GET` | `/api/despesas` | histórico paginado |
| `GET` | `/api/despesas/comparar?a={id}&b={id}` | variação por categoria e subcategoria, em R$ e % |

Schemas Pydantic para tudo. Erro de leitura retorna `422` com mensagem em português dizendo **o que fazer** ("Não foi possível ler o arquivo. Exporte novamente em .xlsx e tente de novo."), nunca o traceback.

---

## 7. Planilha de saída

Três abas, geradas com `openpyxl`:

**`Resumo`**
- A1:D1 mesclado, título `RESUMO DE DESPESAS POR CATEGORIA`, negrito 14.
- A2:D2 mesclado, subtítulo cinza: período, nome do arquivo de origem, data de geração.
- Linha 4 = cabeçalho `Categoria / Subcategoria | Valor | % | Lançamentos`, fundo `404040`, fonte branca, negrito. Painel congelado abaixo dela.
- Linha de categoria: nome em caixa alta, negrito, fundo `F8CBAD`, bordas finas `BFBFBF`.
- Linha de subcategoria: recuo de 2, borda inferior `hair` `D9D9D9`.
- Agrupamento nativo do Excel: subcategorias em `outline_level = 1`, com **`summaryBelow = False`** (o total fica *acima* do grupo) — sem isso o `+/−` da lateral aparece no lugar errado.
- Formato numérico: `"R$" #,##0.00_);[Red]("R$" #,##0.00)` — negativo entre parênteses e vermelho. Percentual: `0.0%`.
- Larguras: 46 / 18 / 10 / 12.
- Última linha: `TOTAL GERAL`, fundo `404040`, fonte branca.

**`Detalhado`** — base completa preservada, ordenada na mesma sequência do resumo, cabeçalho congelado e autofiltro na linha 1.

**`Conferência`** — só existe se houver avisos.

Nome do arquivo: `resumo-{nome-original}.xlsx`.

---

## 8. Frontend

Fluxo em três blocos numa página só: **arquivo → colunas → resumo**. Cada bloco só aparece quando o anterior é resolvido.

- Dropzone com drag-and-drop e clique, acessível por teclado (`Enter`/`Espaço`).
- Bloco de colunas: selects pré-preenchidos com o que o backend detectou, mais os toggles de unificação, sinal e ordem.
- Prévia em formato razão contábil: faixa de categoria clicável que recolhe as subcategorias, números em fonte monoespaçada com `tabular-nums`, negativos entre parênteses e em vermelho escuro.
- Bloco de avisos discreto, com barra lateral, só quando houver algo a conferir.
- Tela de histórico: lista dos processamentos e seletor de dois para comparar, com a variação sinalizada por cor e seta.
- Estados vazio, carregando e de erro escritos em português direto, dizendo qual é o próximo passo. Sem jargão de sistema na interface.

---

## 9. Testes

Pytest cobrindo, no mínimo:
- parsing de valores, incluindo todos os exemplos de 4.3;
- unificação de nomes com as três variantes de "Guias/Custas Judiciais";
- detecção de cabeçalho fora da linha 1;
- planilha sem coluna de subcategoria;
- linha com valor vazio no meio da base;
- soma do resumo igual à soma da base analítica (invariante principal — se essa falhar, nada mais importa).

Inclua uma fixture `.xlsx` pequena, com dados fictícios, cobrindo os casos sujos acima.

---

## 10. Critérios de aceite

- [ ] Subir a planilha analítica e baixar o consolidado leva menos de 4 cliques.
- [ ] Total geral do resumo bate, centavo a centavo, com a soma da coluna Valor Líquido da origem.
- [ ] "Guias/Custas Judiciais" e "Guias / Custas Judiciais" aparecem como uma linha só.
- [ ] No Excel, o `+/−` da lateral recolhe as subcategorias mantendo a categoria visível.
- [ ] Arquivo corrompido ou fora do formato retorna mensagem em português, sem stacktrace na tela.
- [ ] Rodando no prod2, com migrations aplicadas e `README` de deploy atualizado.

---

## 11. Fora de escopo nesta versão

Autenticação nova (use a existente), edição de categorias pela tela, importação automática do sistema de gestão, gráficos, exportação em PDF, multi-empresa.
