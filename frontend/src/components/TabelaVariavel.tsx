"use client";

import { formatarData, formatarPercentual, formatarValor } from "@/lib/formato";
import type { RelatorioVariavel } from "@/lib/tipos-variavel";

export default function TabelaVariavel({ relatorio }: { relatorio: RelatorioVariavel }) {
  const responsaveis = Object.entries(relatorio.por_responsavel);

  return (
    <div className="space-y-8">
      {responsaveis.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-semibold text-slate-900">Variável por responsável</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {responsaveis.map(([nome, total]) => (
              <div key={nome} className="rounded border border-slate-200 bg-white px-4 py-3">
                <p className="truncate text-xs text-slate-500" title={nome}>
                  {nome}
                </p>
                <p className="numero mt-1 text-lg font-semibold text-slate-900">
                  {formatarValor(total)}
                </p>
              </div>
            ))}
            <div className="rounded border border-slate-800 bg-slate-800 px-4 py-3 text-white">
              <p className="text-xs text-slate-300">Total geral</p>
              <p className="numero mt-1 text-lg font-semibold">
                {formatarValor(relatorio.total_variavel)}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded border border-slate-200">
        <table className="min-w-full text-xs">
          <thead className="bg-slate-800 text-white">
            <tr>
              <th className="whitespace-nowrap px-3 py-2 text-left font-medium">NH</th>
              <th className="whitespace-nowrap px-3 py-2 text-left font-medium">Pagador</th>
              <th className="whitespace-nowrap px-3 py-2 text-left font-medium">Caso</th>
              <th className="whitespace-nowrap px-3 py-2 text-left font-medium">Área</th>
              <th className="whitespace-nowrap px-3 py-2 text-left font-medium">Responsável</th>
              <th className="whitespace-nowrap px-3 py-2 text-right font-medium">Pagamento</th>
              <th className="whitespace-nowrap px-3 py-2 text-right font-medium">Valor Pago</th>
              <th className="whitespace-nowrap px-3 py-2 text-right font-medium">Líquido</th>
              <th className="whitespace-nowrap px-3 py-2 text-right font-medium">Part.</th>
              <th className="whitespace-nowrap px-3 py-2 text-right font-medium">Variável</th>
            </tr>
          </thead>
          <tbody>
            {relatorio.linhas.map((linha, indice) => (
              <tr
                key={`${linha.nh}-${linha.responsavel}-${indice}`}
                className={`border-t border-slate-100 ${indice % 2 ? "bg-slate-50/60" : ""}`}
              >
                <td className="numero whitespace-nowrap px-3 py-1.5">{linha.nh}</td>
                <td className="max-w-56 truncate px-3 py-1.5" title={linha.pagador}>
                  {linha.pagador}
                </td>
                <td className="max-w-64 truncate px-3 py-1.5" title={linha.titulo}>
                  {linha.numero_do_caso ? `${linha.numero_do_caso} — ${linha.titulo}` : "—"}
                  {linha.casos_do_responsavel > 1 && (
                    <span className="ml-1 text-slate-400">
                      (+{linha.casos_do_responsavel - 1})
                    </span>
                  )}
                </td>
                <td className="whitespace-nowrap px-3 py-1.5 text-slate-600">
                  {linha.area || "—"}
                </td>
                <td className="max-w-48 truncate px-3 py-1.5" title={linha.responsavel}>
                  {linha.responsavel || <span className="text-slate-400">sem responsável</span>}
                </td>
                <td className="numero whitespace-nowrap px-3 py-1.5 text-right text-slate-600">
                  {formatarData(linha.data_pagamento)}
                </td>
                <td className="numero px-3 py-1.5 text-right">{formatarValor(linha.valor_pago)}</td>
                <td className="numero px-3 py-1.5 text-right text-slate-600">
                  {formatarValor(linha.valor_liquido)}
                </td>
                <td className="numero px-3 py-1.5 text-right text-slate-600">
                  {linha.participacao ? formatarPercentual(Number(linha.participacao)) : "—"}
                </td>
                <td className="numero bg-amber-50 px-3 py-1.5 text-right font-semibold">
                  {formatarValor(linha.variavel)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-slate-800 text-white">
            <tr>
              <td className="px-3 py-2 font-semibold" colSpan={6}>
                TOTAL
              </td>
              <td className="numero px-3 py-2 text-right font-semibold">
                {formatarValor(relatorio.total_pago)}
              </td>
              <td className="numero px-3 py-2 text-right font-semibold">
                {formatarValor(relatorio.total_liquido)}
              </td>
              <td />
              <td className="numero px-3 py-2 text-right font-semibold">
                {formatarValor(relatorio.total_variavel)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
