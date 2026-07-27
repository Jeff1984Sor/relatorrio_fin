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

export type Resumo = {
  nome_arquivo: string;
  periodo_inicio: string | null;
  periodo_fim: string | null;
  total_geral: string;
  qtd_lancamentos: number;
  categorias: Categoria[];
  avisos: Aviso[];
};
