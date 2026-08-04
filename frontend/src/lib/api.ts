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
  arquivos: File[],
  mapeamento?: Record<string, number | null> | null,
): FormData {
  const dados = new FormData();
  // Mesmo nome de campo repetido: é assim que o FastAPI recebe uma lista.
  arquivos.forEach((arquivo) => dados.append("arquivos", arquivo));
  if (mapeamento) dados.append("mapeamento", JSON.stringify(mapeamento));
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

export async function inspecionar(arquivos: File[]): Promise<Inspecao> {
  const resposta = await postar(`${BASE}/inspecionar`, corpo(arquivos));
  return (await resposta.json()) as Inspecao;
}

export async function processar(
  arquivos: File[],
  mapeamento: Record<string, number | null> | null,
): Promise<Resumo> {
  const resposta = await postar(`${BASE}/processar`, corpo(arquivos, mapeamento));
  return (await resposta.json()) as Resumo;
}

/** Reenvia os arquivos e salva o .xlsx que volta. Nada fica guardado no servidor. */
export async function baixarXlsx(
  arquivos: File[],
  mapeamento: Record<string, number | null> | null,
): Promise<void> {
  const resposta = await postar(`${BASE}/xlsx`, corpo(arquivos, mapeamento));
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
