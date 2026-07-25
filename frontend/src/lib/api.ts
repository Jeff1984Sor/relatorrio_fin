import type { Comparacao, Historico, Inspecao, Resumo } from "./tipos";

const BASE = "/api/despesas";

/** Erro já com texto pronto para a tela — nunca expõe detalhe técnico. */
export class ErroApi extends Error {
  readonly status: number;
  readonly processamentoAnteriorId: number | null;

  constructor(mensagem: string, status: number, processamentoAnteriorId: number | null = null) {
    super(mensagem);
    this.status = status;
    this.processamentoAnteriorId = processamentoAnteriorId;
  }
}

const MSG_REDE =
  "Não foi possível falar com o servidor. Confira sua conexão e tente de novo.";

async function tratar<T>(resposta: Response): Promise<T> {
  if (resposta.ok) return (await resposta.json()) as T;

  let detalhe: unknown = null;
  try {
    detalhe = (await resposta.json())?.detail;
  } catch {
    detalhe = null;
  }

  if (detalhe && typeof detalhe === "object" && "detalhe" in detalhe) {
    const corpo = detalhe as { detalhe: string; processamento_id: number };
    throw new ErroApi(corpo.detalhe, resposta.status, corpo.processamento_id);
  }

  const texto =
    typeof detalhe === "string" && detalhe
      ? detalhe
      : "Não foi possível concluir a operação. Tente de novo.";
  throw new ErroApi(texto, resposta.status);
}

async function enviar<T>(caminho: string, corpo?: FormData): Promise<T> {
  let resposta: Response;
  try {
    resposta = corpo
      ? await fetch(caminho, { method: "POST", body: corpo })
      : await fetch(caminho);
  } catch {
    throw new ErroApi(MSG_REDE, 0);
  }
  return tratar<T>(resposta);
}

export function inspecionar(arquivo: File, aba?: string): Promise<Inspecao> {
  const dados = new FormData();
  dados.append("arquivo", arquivo);
  if (aba) dados.append("aba", aba);
  return enviar<Inspecao>(`${BASE}/inspecionar`, dados);
}

export type OpcoesProcessamento = {
  aba?: string;
  unificar: boolean;
  positivo: boolean;
  ordem: "alfabetica" | "valor";
  mapeamento: Record<string, number | null>;
  forcar?: boolean;
};

export function processar(arquivo: File, opcoes: OpcoesProcessamento): Promise<Resumo> {
  const dados = new FormData();
  dados.append("arquivo", arquivo);
  if (opcoes.aba) dados.append("aba", opcoes.aba);
  dados.append("unificar", String(opcoes.unificar));
  dados.append("positivo", String(opcoes.positivo));
  dados.append("ordem", opcoes.ordem);
  dados.append("mapeamento", JSON.stringify(opcoes.mapeamento));
  if (opcoes.forcar) dados.append("forcar", "true");
  return enviar<Resumo>(`${BASE}/processar`, dados);
}

export function obterResumo(id: number): Promise<Resumo> {
  return enviar<Resumo>(`${BASE}/${id}`);
}

export function listarHistorico(pagina = 1): Promise<Historico> {
  return enviar<Historico>(`${BASE}?pagina=${pagina}`);
}

export function comparar(a: number, b: number): Promise<Comparacao> {
  return enviar<Comparacao>(`${BASE}/comparar?a=${a}&b=${b}`);
}

export function urlDownload(id: number): string {
  return `${BASE}/${id}/xlsx`;
}
