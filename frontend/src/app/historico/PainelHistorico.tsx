"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Fragment, useCallback, useEffect, useState } from "react";

import Avisos from "@/components/Avisos";
import TabelaResumo from "@/components/TabelaResumo";
import { comparar, ErroApi, listarHistorico, obterResumo, urlDownload } from "@/lib/api";
import {
  descreverPeriodo,
  ehNegativo,
  formatarDataHora,
  formatarPercentual,
  formatarValor,
} from "@/lib/formato";
import type { Comparacao, ProcessamentoResumido, Resumo, Variacao } from "@/lib/tipos";

export default function PainelHistorico() {
  const parametros = useSearchParams();
  const abrirInicial = parametros.get("abrir");

  const [itens, setItens] = useState<ProcessamentoResumido[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const [aberto, setAberto] = useState<Resumo | null>(null);
  const [selecionados, setSelecionados] = useState<number[]>([]);
  const [comparacao, setComparacao] = useState<Comparacao | null>(null);

  const tratarErro = useCallback((excecao: unknown) => {
    setErro(
      excecao instanceof ErroApi
        ? excecao.message
        : "Não foi possível carregar o histórico. Tente de novo.",
    );
  }, []);

  useEffect(() => {
    listarHistorico().then((pagina) => setItens(pagina.itens)).catch(tratarErro);
  }, [tratarErro]);

  const abrir = useCallback(
    (id: number) => {
      setComparacao(null);
      obterResumo(id).then(setAberto).catch(tratarErro);
    },
    [tratarErro],
  );

  useEffect(() => {
    if (abrirInicial) abrir(Number(abrirInicial));
  }, [abrirInicial, abrir]);

  function alternarSelecao(id: number) {
    setSelecionados((atual) => {
      if (atual.includes(id)) return atual.filter((x) => x !== id);
      return [...atual, id].slice(-2);
    });
  }

  function compararSelecionados() {
    if (selecionados.length !== 2) return;
    const [a, b] = selecionados;
    setAberto(null);
    comparar(a, b).then(setComparacao).catch(tratarErro);
  }

  if (erro) {
    return (
      <div className="rounded border border-negativo/30 bg-rose-50 px-4 py-3 text-sm text-negativo">
        {erro}
      </div>
    );
  }

  if (itens === null) {
    return <p className="text-sm text-slate-500">Carregando histórico…</p>;
  }

  if (itens.length === 0) {
    return (
      <div className="rounded border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
        <p className="text-sm font-medium text-slate-900">Nenhuma planilha processada ainda.</p>
        <p className="mt-1 text-sm text-slate-500">
          Suba a primeira planilha analítica para começar o histórico.
        </p>
        <Link
          href="/"
          className="mt-4 inline-block rounded bg-slate-900 px-5 py-2.5 text-sm font-medium text-white"
        >
          Consolidar uma planilha
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-2 text-xl font-semibold text-slate-900">Histórico</h1>
      <p className="mb-6 text-sm text-slate-600">
        Marque dois processamentos para comparar os períodos.
      </p>

      <div className="mb-6 overflow-hidden rounded border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              <th className="w-10 px-4 py-2.5" aria-label="Comparar" />
              <th className="px-4 py-2.5 text-left font-medium">Arquivo</th>
              <th className="px-4 py-2.5 text-left font-medium">Período</th>
              <th className="px-4 py-2.5 text-right font-medium">Total</th>
              <th className="px-4 py-2.5 text-right font-medium">Lançamentos</th>
              <th className="px-4 py-2.5 text-left font-medium">Processado em</th>
              <th className="px-4 py-2.5" aria-label="Ações" />
            </tr>
          </thead>
          <tbody>
            {itens.map((item) => (
              <tr key={item.id} className="border-t border-slate-100">
                <td className="px-4 py-2">
                  <input
                    type="checkbox"
                    checked={selecionados.includes(item.id)}
                    onChange={() => alternarSelecao(item.id)}
                    aria-label={`Comparar ${item.nome_arquivo}`}
                  />
                </td>
                <td className="px-4 py-2 text-slate-800">{item.nome_arquivo}</td>
                <td className="px-4 py-2 text-slate-600">
                  {descreverPeriodo(item.periodo_inicio, item.periodo_fim)}
                </td>
                <td
                  className={`numero px-4 py-2 text-right ${
                    ehNegativo(item.total_geral) ? "text-negativo" : "text-slate-800"
                  }`}
                >
                  {formatarValor(item.total_geral)}
                </td>
                <td className="numero px-4 py-2 text-right text-slate-600">
                  {item.qtd_lancamentos}
                </td>
                <td className="px-4 py-2 text-slate-600">{formatarDataHora(item.criado_em)}</td>
                <td className="whitespace-nowrap px-4 py-2 text-right">
                  <button
                    type="button"
                    onClick={() => abrir(item.id)}
                    className="text-slate-700 underline hover:text-slate-900"
                  >
                    Abrir
                  </button>
                  <a
                    href={urlDownload(item.id)}
                    className="ml-4 text-slate-700 underline hover:text-slate-900"
                  >
                    Baixar
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        type="button"
        onClick={compararSelecionados}
        disabled={selecionados.length !== 2}
        className="rounded bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        Comparar os dois marcados
      </button>

      {aberto && (
        <section className="mt-8">
          <h2 className="mb-3 text-base font-semibold text-slate-900">{aberto.nome_arquivo}</h2>
          <TabelaResumo resumo={aberto} positivo={aberto.opcoes.positivo} />
          <Avisos avisos={aberto.avisos} />
        </section>
      )}

      {comparacao && <PainelComparacao comparacao={comparacao} />}
    </div>
  );
}

function PainelComparacao({ comparacao }: { comparacao: Comparacao }) {
  return (
    <section className="mt-8">
      <h2 className="mb-1 text-base font-semibold text-slate-900">Comparação</h2>
      <p className="mb-4 text-sm text-slate-600">
        {comparacao.a.nome_arquivo} → {comparacao.b.nome_arquivo}
      </p>

      <div className="overflow-hidden rounded border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-800 text-white">
            <tr>
              <th className="px-4 py-2.5 text-left font-medium">Categoria / Subcategoria</th>
              <th className="px-4 py-2.5 text-right font-medium">Período A</th>
              <th className="px-4 py-2.5 text-right font-medium">Período B</th>
              <th className="px-4 py-2.5 text-right font-medium">Variação</th>
              <th className="px-4 py-2.5 text-right font-medium">%</th>
            </tr>
          </thead>
          <tbody>
            {comparacao.categorias.map((categoria) => (
              <Fragment key={categoria.chave}>
                <LinhaVariacao item={categoria} destaque />
                {categoria.subcategorias.map((sub) => (
                  <LinhaVariacao key={`${categoria.chave}-${sub.chave}`} item={sub} />
                ))}
              </Fragment>
            ))}
          </tbody>
          <tfoot className="bg-slate-800 text-white">
            <tr>
              <td className="px-4 py-2.5 font-semibold">TOTAL GERAL</td>
              <td className="numero px-4 py-2.5 text-right">{formatarValor(comparacao.total_a)}</td>
              <td className="numero px-4 py-2.5 text-right">{formatarValor(comparacao.total_b)}</td>
              <td className="numero px-4 py-2.5 text-right font-semibold">
                {formatarValor(comparacao.variacao)}
              </td>
              <td className="numero px-4 py-2.5 text-right">
                {comparacao.variacao_percentual === null
                  ? "—"
                  : formatarPercentual(comparacao.variacao_percentual)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}

function LinhaVariacao({ item, destaque = false }: { item: Variacao; destaque?: boolean }) {
  const variacao = Number(item.variacao);
  // Despesa é negativa: variação negativa significa gasto MAIOR.
  const gastouMais = variacao < 0;
  const seta = variacao === 0 ? "—" : gastouMais ? "▲" : "▼";
  const cor = variacao === 0 ? "text-slate-500" : gastouMais ? "text-negativo" : "text-emerald-700";

  return (
    <tr className={`border-t border-slate-100 ${destaque ? "bg-orange-100/70" : ""}`}>
      <td className={`px-4 py-2 ${destaque ? "font-semibold uppercase" : "pl-12 text-slate-700"}`}>
        {item.rotulo}
      </td>
      <td className="numero px-4 py-2 text-right text-slate-600">{formatarValor(item.total_a)}</td>
      <td className="numero px-4 py-2 text-right text-slate-600">{formatarValor(item.total_b)}</td>
      <td className={`numero px-4 py-2 text-right ${cor}`}>
        {seta} {formatarValor(item.variacao)}
      </td>
      <td className={`numero px-4 py-2 text-right ${cor}`}>
        {item.variacao_percentual === null ? "—" : formatarPercentual(item.variacao_percentual)}
      </td>
    </tr>
  );
}
