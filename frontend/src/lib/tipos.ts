export type Mapeamento = {
  valor: number | null;
  categoria: number | null;
  subcategoria: number | null;
  data: number | null;
  fornecedor: number | null;
};

export type CampoMapeamento = keyof Mapeamento;

export type Inspecao = {
  abas: string[];
  aba: string;
  linha_cabecalho: number | null;
  colunas: string[];
  mapeamento: Mapeamento;
  amostra: string[][];
  hash_arquivo: string;
  ja_processado_id: number | null;
};

export type Aviso = {
  tipo: string;
  mensagem: string;
  quantidade: number;
  detalhes: (string | number)[];
};

export type Subcategoria = {
  rotulo: string;
  chave: string;
  total: string;
  qtd: number;
  percentual: number;
};

export type Categoria = Subcategoria & { subcategorias: Subcategoria[] };

export type Opcoes = {
  unificar: boolean;
  positivo: boolean;
  ordem: "alfabetica" | "valor";
  mapeamento: Record<string, number | null>;
};

export type Resumo = {
  processamento_id: number;
  nome_arquivo: string;
  criado_em: string;
  criado_por: string;
  periodo_inicio: string | null;
  periodo_fim: string | null;
  total_geral: string;
  qtd_lancamentos: number;
  opcoes: Opcoes;
  categorias: Categoria[];
  avisos: Aviso[];
};

export type ProcessamentoResumido = {
  id: number;
  nome_arquivo: string;
  criado_em: string;
  criado_por: string;
  periodo_inicio: string | null;
  periodo_fim: string | null;
  total_geral: string;
  qtd_lancamentos: number;
};

export type Historico = {
  itens: ProcessamentoResumido[];
  total: number;
  pagina: number;
  por_pagina: number;
};

export type Variacao = {
  rotulo: string;
  chave: string;
  total_a: string;
  total_b: string;
  variacao: string;
  variacao_percentual: number | null;
};

export type VariacaoCategoria = Variacao & { subcategorias: Variacao[] };

export type Comparacao = {
  a: ProcessamentoResumido;
  b: ProcessamentoResumido;
  total_a: string;
  total_b: string;
  variacao: string;
  variacao_percentual: number | null;
  categorias: VariacaoCategoria[];
};
