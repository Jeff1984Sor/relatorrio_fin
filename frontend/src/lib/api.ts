import type { Inspecao, Resumo } from "./tipos";

const BASE = "/api/despesas";

/** Erro já com texto pronto para a tela — nunca expõe detalhe técnico. */
export class ErroApi extends Error {
  readonly status: number;

  constructor(mensagem: string, status: number) {
    super(mensagem);
    this.status = status;
  }
}

const MSG_REDE =
  "Não foi possível falar com o servidor. Confira sua conexão e tente de novo.";

async function mensagemDeErro(resposta: Response): Promise<string> {
  try {
    const detalhe = (await resposta.json())?.detail;
    if (typeof detalhe === "string" && detalhe) return detalhe;
  } catch {
    /* corpo não era JSON */
  }
  return "Não foi possível concluir a operação. Tente de novo.";
}

function corpo(
  arquivo: File,
  aba: string | undefined,
  mapeamento: Record<string, number | null>,
): FormData {
  const dados = new FormData();
  dados.append("arquivo", arquivo);
  if (aba) dados.append("aba", aba);
  dados.append("mapeamento", JSON.stringify(mapeamento));
  return dados;
}

async function postar(caminho: string, dados: FormData): Promise<Response> {
  let resposta: Response;
  try {
    resposta = await fetch(caminho, { method: "POST", body: dados });
  } catch {
    throw new ErroApi(MSG_REDE, 0);
  }
  if (!resposta.ok) throw new ErroApi(await mensagemDeErro(resposta), resposta.status);
  return resposta;
}

export async function inspecionar(arquivo: File, aba?: string): Promise<Inspecao> {
  const dados = new FormData();
  dados.append("arquivo", arquivo);
  if (aba) dados.append("aba", aba);
  const resposta = await postar(`${BASE}/inspecionar`, dados);
  return (await resposta.json()) as Inspecao;
}

export async function processar(
  arquivo: File,
  aba: string | undefined,
  mapeamento: Record<string, number | null>,
): Promise<Resumo> {
  const resposta = await postar(`${BASE}/processar`, corpo(arquivo, aba, mapeamento));
  return (await resposta.json()) as Resumo;
}

/** Reenvia o arquivo e salva o .xlsx que volta. Nada fica guardado no servidor. */
export async function baixarXlsx(
  arquivo: File,
  aba: string | undefined,
  mapeamento: Record<string, number | null>,
): Promise<void> {
  const resposta = await postar(`${BASE}/xlsx`, corpo(arquivo, aba, mapeamento));
  const blob = await resposta.blob();

  const cabecalho = resposta.headers.get("content-disposition") ?? "";
  const nome = /filename="([^"]+)"/.exec(cabecalho)?.[1] ?? "resumo-despesas.xlsx";

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
