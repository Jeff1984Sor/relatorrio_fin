export type Mapeamento = {
  valor: number | null;
  categoria: number | null;
  subcategoria: number | null;
  data: number | null;
  fornecedor: number | null;
  conta: number | null;
  somente_preenchidos: boolean;
};

export type CampoMapeamento = Exclude<keyof Mapeamento, "somente_preenchidos">;

export type ArquivoInspecionado = {
  nome: string;
  abas: string[];
  aba: string;
  linha_cabecalho: number | null;
  colunas: string[];
  mapeamento: Mapeamento;
  amostra: string[][];
};

export type Inspecao = {
  arquivos: ArquivoInspecionado[];
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
  por_conta: Record<string, string>;
};

export type Categoria = Subcategoria & { subcategorias: Subcategoria[] };

export type Resumo = {
  arquivos: string[];
  periodo_inicio: string | null;
  periodo_fim: string | null;
  total_geral: string;
  qtd_lancamentos: number;
  contas: string[];
  total_por_conta: Record<string, string>;
  categorias: Categoria[];
  avisos: Aviso[];
};
