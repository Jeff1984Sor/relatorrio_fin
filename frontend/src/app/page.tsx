"use client";

import Link from "next/link";
import { useState } from "react";

import Avisos from "@/components/Avisos";
import Bloco from "@/components/Bloco";
import BlocoColunas from "@/components/BlocoColunas";
import Dropzone from "@/components/Dropzone";
import TabelaResumo from "@/components/TabelaResumo";
import { ErroApi, inspecionar, processar, urlDownload } from "@/lib/api";
import { descreverPeriodo } from "@/lib/formato";
import type { Inspecao, Mapeamento, Resumo } from "@/lib/tipos";

export default function Pagina() {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [inspecao, setInspecao] = useState<Inspecao | null>(null);
  const [mapeamento, setMapeamento] = useState<Mapeamento | null>(null);
  const [resumo, setResumo] = useState<Resumo | null>(null);

  const [lendo, setLendo] = useState(false);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [duplicadoId, setDuplicadoId] = useState<number | null>(null);

  function limpar() {
    setInspecao(null);
    setMapeamento(null);
    setResumo(null);
    setErro(null);
    setDuplicadoId(null);
  }

  async function aoEscolherArquivo(escolhido: File) {
    setArquivo(escolhido);
    limpar();
    setLendo(true);
    try {
      const lido = await inspecionar(escolhido);
      setInspecao(lido);
      setMapeamento(lido.mapeamento);
      setDuplicadoId(lido.ja_processado_id);
    } catch (excecao) {
      setErro(excecao instanceof ErroApi ? excecao.message : "Não foi possível ler o arquivo.");
      setArquivo(null);
    } finally {
      setLendo(false);
    }
  }

  async function aoProcessar(forcar = false) {
    if (!arquivo || !mapeamento || !inspecao) return;
    setProcessando(true);
    setErro(null);
    try {
      const consolidado = await processar(arquivo, {
        aba: inspecao.aba,
        mapeamento: mapeamento as unknown as Record<string, number | null>,
        forcar,
      });
      setResumo(consolidado);
      setDuplicadoId(null);
    } catch (excecao) {
      if (excecao instanceof ErroApi && excecao.status === 409) {
        setDuplicadoId(excecao.processamentoAnteriorId);
        setErro(excecao.message);
      } else {
        setErro(
          excecao instanceof ErroApi
            ? excecao.message
            : "Não foi possível consolidar a planilha. Tente de novo.",
        );
      }
    } finally {
      setProcessando(false);
    }
  }

  return (
    <div>
      <h1 className="mb-2 text-xl font-semibold text-slate-900">
        Consolidar despesas por categoria
      </h1>
      <p className="mb-8 text-sm text-slate-600">
        Suba a planilha analítica exportada do sistema de gestão e baixe o resumo pronto para a
        diretoria.
      </p>

      {erro && (
        <div className="mb-6 rounded border border-negativo/30 bg-rose-50 px-4 py-3 text-sm text-negativo">
          <p>{erro}</p>
          {duplicadoId !== null && (
            <div className="mt-2 flex flex-wrap gap-4">
              <Link href={`/historico?abrir=${duplicadoId}`} className="font-medium underline">
                Abrir o resultado anterior
              </Link>
              <button
                type="button"
                onClick={() => aoProcessar(true)}
                className="font-medium underline"
              >
                Processar mesmo assim
              </button>
            </div>
          )}
        </div>
      )}

      <Bloco numero={1} titulo="Arquivo" descricao="Planilha analítica de despesas pagas.">
        <Dropzone arquivo={arquivo} carregando={lendo} onEscolher={aoEscolherArquivo} />
      </Bloco>

      {inspecao && mapeamento && (
        <Bloco
          numero={2}
          titulo="Colunas"
          descricao={
            inspecao.linha_cabecalho !== null
              ? `Cabeçalho encontrado na linha ${inspecao.linha_cabecalho + 1}. Confira o que foi detectado e ajuste se precisar.`
              : "Confira o que foi detectado e ajuste se precisar."
          }
        >
          <BlocoColunas
            inspecao={inspecao}
            mapeamento={mapeamento}
            processando={processando}
            onMapeamento={setMapeamento}
            onProcessar={() => aoProcessar(false)}
          />
        </Bloco>
      )}

      {resumo && (
        <Bloco
          numero={3}
          titulo="Resumo"
          descricao={`${descreverPeriodo(resumo.periodo_inicio, resumo.periodo_fim)} — ${resumo.qtd_lancamentos} lançamentos`}
        >
          <TabelaResumo resumo={resumo} positivo={false} />
          <Avisos avisos={resumo.avisos} />
          <div className="mt-6 flex flex-wrap gap-4">
            <a
              href={urlDownload(resumo.processamento_id)}
              className="rounded bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              Baixar planilha consolidada
            </a>
            <Link
              href="/historico"
              className="rounded border border-slate-300 px-5 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
            >
              Ver histórico
            </Link>
          </div>
        </Bloco>
      )}
    </div>
  );
}
