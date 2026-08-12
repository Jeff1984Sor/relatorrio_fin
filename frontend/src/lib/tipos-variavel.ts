import type { Aviso } from "./tipos";

export type LinhaVariavel = {
  grupo: string;
  pagador: string;
  cliente: string;
  nh: string;
  nf: string;
  situacao: string;
  data_vencimento: string | null;
  data_pagamento: string | null;
  numero_do_caso: number | null;
  titulo: string;
  area: string;
  responsavel: string;
  valor_bruto: string;
  valor_pago: string;
  aliquota: string;
  valor_dos_impostos: string;
  valor_liquido: string;
  participacao: string | null;
  variavel: string;
  casos_do_responsavel: number;
  casos_no_recebimento: number;
};

export type RelatorioVariavel = {
  arquivos: string[];
  aliquota: string;
  participacao: string;
  periodo_inicio: string | null;
  periodo_fim: string | null;
  total_pago: string;
  total_liquido: string;
  total_variavel: string;
  por_responsavel: Record<string, string>;
  linhas: LinhaVariavel[];
  avisos: Aviso[];
};
