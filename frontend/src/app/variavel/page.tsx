"use client";

import { useState } from "react";

import Avisos from "@/components/Avisos";
import Bloco from "@/components/Bloco";
import SeletorArquivo from "@/components/SeletorArquivo";
import TabelaVariavel from "@/components/TabelaVariavel";
import { ErroApi } from "@/lib/api";
import { baixarVariavel, processarVariavel } from "@/lib/api-variavel";
import { descreverPeriodo } from "@/lib/formato";
import type { RelatorioVariavel } from "@/lib/tipos-variavel";

function mensagem(excecao: unknown, padrao: string): string {
  return excecao instanceof ErroApi ? excecao.message : padrao;
}

export default function Pagina() {
  const [cubo, setCubo] = useState<File | null>(null);
  const [casos, setCasos] = useState<File | null>(null);
  const [aliquota, setAliquota] = useState("17,5");
  const [relatorio, setRelatorio] = useState<RelatorioVariavel | null>(null);

  const [processando, setProcessando] = useState(false);
  const [baixando, setBaixando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const pronto = cubo !== null && casos !== null;

  async function aoProcessar() {
    if (!cubo || !casos) return;
    setProcessando(true);
    setErro(null);
    try {
      setRelatorio(await processarVariavel(cubo, casos, aliquota));
    } catch (excecao) {
      setErro(mensagem(excecao, "Não foi possível gerar o relatório. Tente de novo."));
      setRelatorio(null);
    } finally {
      setProcessando(false);
    }
  }

  async function aoBaixar() {
    if (!cubo || !casos) return;
    setBaixando(true);
    setErro(null);
    try {
      await baixarVariavel(cubo, casos, aliquota);
    } catch (excecao) {
      setErro(mensagem(excecao, "Não foi possível gerar a planilha. Tente de novo."));
    } finally {
      setBaixando(false);
    }
  }

  return (
    <div>
      <h1 className="mb-2 text-xl font-semibold text-slate-900">
        Relatório de remuneração variável
      </h1>
      <p className="mb-8 text-sm text-slate-600">
        Cruza os recebimentos do período com os casos e calcula a variável de cada
        responsável.
      </p>

      {erro && (
        <div className="mb-6 rounded border border-negativo/30 bg-rose-50 px-4 py-3 text-sm text-negativo">
          {erro}
        </div>
      )}

      <Bloco numero={1} titulo="Arquivos" descricao="Os dois relatórios exportados do sistema.">
        <div className="grid gap-4 sm:grid-cols-2">
          <SeletorArquivo
            rotulo="Visão cubo de recebimentos"
            ajuda="O que tem NH, pagador, valores e o número do caso."
            arquivo={cubo}
            onEscolher={(a) => {
              setCubo(a);
              setRelatorio(null);
            }}
          />
          <SeletorArquivo
            rotulo="Relatório de casos"
            ajuda="Número do caso, título, área, responsável e participação."
            arquivo={casos}
            onEscolher={(a) => {
              setCasos(a);
              setRelatorio(null);
            }}
          />
        </div>

        <div className="mt-6 flex flex-wrap items-end gap-6">
          <label className="text-sm">
            <span className="mb-1 block font-medium text-slate-700">Imposto (%)</span>
            <input
              type="text"
              inputMode="decimal"
              value={aliquota}
              onChange={(e) => {
                setAliquota(e.target.value);
                setRelatorio(null);
              }}
              className="numero w-28 rounded border border-slate-300 px-3 py-2 text-right text-sm focus:border-slate-900 focus:outline-none"
            />
          </label>

          <button
            type="button"
            onClick={aoProcessar}
            disabled={!pronto || processando}
            className="rounded bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {processando ? "Calculando…" : "Gerar relatório"}
          </button>
        </div>

        {!pronto && (
          <p className="mt-3 text-xs text-slate-500">
            Escolha os dois arquivos para liberar o cálculo.
          </p>
        )}
      </Bloco>

      {relatorio && (
        <Bloco
          numero={2}
          titulo="Relatório"
          descricao={`${descreverPeriodo(relatorio.periodo_inicio, relatorio.periodo_fim)} — ${relatorio.linhas.length} linhas`}
        >
          <TabelaVariavel relatorio={relatorio} />
          <Avisos avisos={relatorio.avisos} />
          <div className="mt-6">
            <button
              type="button"
              onClick={aoBaixar}
              disabled={baixando}
              className="rounded bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {baixando ? "Gerando a planilha…" : "Baixar planilha"}
            </button>
          </div>
        </Bloco>
      )}
    </div>
  );
}
