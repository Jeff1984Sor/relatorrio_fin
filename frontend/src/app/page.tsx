"use client";

import { useState } from "react";

import Avisos from "@/components/Avisos";
import Bloco from "@/components/Bloco";
import BlocoColunas from "@/components/BlocoColunas";
import Dropzone from "@/components/Dropzone";
import TabelaResumo from "@/components/TabelaResumo";
import { baixarXlsx, ErroApi, inspecionar, processar } from "@/lib/api";
import { descreverPeriodo } from "@/lib/formato";
import type { Inspecao, Mapeamento, Resumo } from "@/lib/tipos";

function mensagem(excecao: unknown, padrao: string): string {
  return excecao instanceof ErroApi ? excecao.message : padrao;
}

export default function Pagina() {
  const [arquivos, setArquivos] = useState<File[]>([]);
  const [inspecao, setInspecao] = useState<Inspecao | null>(null);
  const [mapeamento, setMapeamento] = useState<Mapeamento | null>(null);
  const [resumo, setResumo] = useState<Resumo | null>(null);

  const [lendo, setLendo] = useState(false);
  const [processando, setProcessando] = useState(false);
  const [baixando, setBaixando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function reinspecionar(lista: File[]) {
    setArquivos(lista);
    setInspecao(null);
    setMapeamento(null);
    setResumo(null);
    setErro(null);

    if (lista.length === 0) return;

    setLendo(true);
    try {
      const lido = await inspecionar(lista);
      setInspecao(lido);
      setMapeamento(lido.arquivos[0].mapeamento);
    } catch (excecao) {
      setErro(mensagem(excecao, "Não foi possível ler os arquivos."));
    } finally {
      setLendo(false);
    }
  }

  function aoEscolher(novos: File[]) {
    // Mesmo nome e mesmo tamanho: o usuário selecionou o arquivo duas vezes.
    const existentes = new Set(arquivos.map((a) => `${a.name}:${a.size}`));
    const ineditos = novos.filter((a) => !existentes.has(`${a.name}:${a.size}`));
    reinspecionar([...arquivos, ...ineditos]);
  }

  function aoRemover(indice: number) {
    reinspecionar(arquivos.filter((_, i) => i !== indice));
  }

  const mapaParaEnvio = () =>
    mapeamento ? (mapeamento as unknown as Record<string, number | null>) : null;

  async function aoProcessar() {
    if (!arquivos.length || !mapeamento) return;
    setProcessando(true);
    setErro(null);
    try {
      setResumo(await processar(arquivos, mapaParaEnvio()));
    } catch (excecao) {
      setErro(mensagem(excecao, "Não foi possível consolidar as planilhas. Tente de novo."));
    } finally {
      setProcessando(false);
    }
  }

  async function aoBaixar() {
    if (!arquivos.length || !mapeamento) return;
    setBaixando(true);
    setErro(null);
    try {
      await baixarXlsx(arquivos, mapaParaEnvio());
    } catch (excecao) {
      setErro(mensagem(excecao, "Não foi possível gerar a planilha. Tente de novo."));
    } finally {
      setBaixando(false);
    }
  }

  return (
    <div>
      <h1 className="mb-2 text-xl font-semibold text-slate-900">
        Consolidar despesas por categoria
      </h1>
      <p className="mb-8 text-sm text-slate-600">
        Suba uma ou várias planilhas de despesas e baixe um resumo único, pronto para a
        diretoria.
      </p>

      {erro && (
        <div className="mb-6 rounded border border-negativo/30 bg-rose-50 px-4 py-3 text-sm text-negativo">
          {erro}
        </div>
      )}

      <Bloco
        numero={1}
        titulo="Arquivos"
        descricao="Planilhas de despesas pagas. Pode subir várias de uma vez."
      >
        <Dropzone
          arquivos={arquivos}
          carregando={lendo}
          onEscolher={aoEscolher}
          onRemover={aoRemover}
        />
      </Bloco>

      {inspecao && mapeamento && (
        <Bloco
          numero={2}
          titulo="Colunas"
          descricao={
            inspecao.arquivos[0].linha_cabecalho !== null
              ? `Cabeçalho encontrado na linha ${inspecao.arquivos[0].linha_cabecalho + 1}. Confira o que foi detectado e ajuste se precisar.`
              : "Confira o que foi detectado e ajuste se precisar."
          }
        >
          <BlocoColunas
            arquivo={inspecao.arquivos[0]}
            qtdArquivos={inspecao.arquivos.length}
            mapeamento={mapeamento}
            processando={processando}
            onMapeamento={setMapeamento}
            onProcessar={aoProcessar}
          />
        </Bloco>
      )}

      {resumo && (
        <Bloco
          numero={3}
          titulo="Resumo"
          descricao={`${descreverPeriodo(resumo.periodo_inicio, resumo.periodo_fim)} — ${resumo.qtd_lancamentos} lançamentos${
            resumo.arquivos.length > 1 ? ` de ${resumo.arquivos.length} planilhas` : ""
          }`}
        >
          <TabelaResumo resumo={resumo} />
          <Avisos avisos={resumo.avisos} />
          <div className="mt-6">
            <button
              type="button"
              onClick={aoBaixar}
              disabled={baixando}
              className="rounded bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {baixando ? "Gerando a planilha…" : "Baixar planilha consolidada"}
            </button>
          </div>
        </Bloco>
      )}
    </div>
  );
}
