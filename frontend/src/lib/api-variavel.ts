import { ErroApi } from "./api";
import type { RelatorioVariavel } from "./tipos-variavel";

const BASE = "/api/variavel";

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

export type Parametros = { aliquota: string; participacao: string };

function corpo(cubo: File, casos: File, parametros: Parametros): FormData {
  const dados = new FormData();
  dados.append("cubo", cubo);
  dados.append("casos", casos);
  if (parametros.aliquota.trim()) dados.append("aliquota", parametros.aliquota.trim());
  if (parametros.participacao.trim())
    dados.append("participacao", parametros.participacao.trim());
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

export async function processarVariavel(
  cubo: File,
  casos: File,
  parametros: Parametros,
): Promise<RelatorioVariavel> {
  const resposta = await postar(`${BASE}/processar`, corpo(cubo, casos, parametros));
  return (await resposta.json()) as RelatorioVariavel;
}

export async function baixarVariavel(
  cubo: File,
  casos: File,
  parametros: Parametros,
): Promise<void> {
  const resposta = await postar(`${BASE}/xlsx`, corpo(cubo, casos, parametros));
  const blob = await resposta.blob();

  const cabecalho = resposta.headers.get("content-disposition") ?? "";
  const nome = /filename="([^"]+)"/.exec(cabecalho)?.[1] ?? "relatorio-variavel.xlsx";

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
