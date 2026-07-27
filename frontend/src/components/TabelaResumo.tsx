"use client";

import { useState } from "react";

import { ehNegativo, formatarPercentual, formatarValor } from "@/lib/formato";
import type { Categoria, Resumo } from "@/lib/tipos";

/** Prévia em formato razão contábil: faixa de categoria clicável recolhe as subcategorias. */
export default function TabelaResumo({ resumo }: { resumo: Resumo }) {
  const [recolhidas, setRecolhidas] = useState<Set<string>>(new Set());

  function alternar(chave: string) {
    setRecolhidas((atual) => {
      const proximo = new Set(atual);
      if (proximo.has(chave)) proximo.delete(chave);
      else proximo.add(chave);
      return proximo;
    });
  }

  return (
    <div className="overflow-hidden rounded border border-slate-200">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-800 text-white">
          <tr>
            <th className="px-4 py-2.5 text-left font-medium">Categoria / Subcategoria</th>
            <th className="px-4 py-2.5 text-right font-medium">Valor</th>
            <th className="px-4 py-2.5 text-right font-medium">%</th>
            <th className="px-4 py-2.5 text-right font-medium">Lançamentos</th>
          </tr>
        </thead>
        <tbody>
          {resumo.categorias.map((categoria) => (
            <CorpoCategoria
              key={categoria.chave}
              categoria={categoria}
              recolhida={recolhidas.has(categoria.chave)}
              onAlternar={() => alternar(categoria.chave)}
            />
          ))}
        </tbody>
        <tfoot className="bg-slate-800 text-white">
          <tr>
            <td className="px-4 py-2.5 font-semibold">TOTAL GERAL</td>
            <td className="numero px-4 py-2.5 text-right font-semibold">
              {formatarValor(resumo.total_geral)}
            </td>
            <td className="numero px-4 py-2.5 text-right font-semibold">100,0%</td>
            <td className="numero px-4 py-2.5 text-right font-semibold">
              {resumo.qtd_lancamentos}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function CorpoCategoria({
  categoria,
  recolhida,
  onAlternar,
}: {
  categoria: Categoria;
  recolhida: boolean;
  onAlternar: () => void;
}) {
  return (
    <>
      <tr className="border-t border-slate-200 bg-orange-100/70">
        <td className="px-4 py-2">
          <button
            type="button"
            onClick={onAlternar}
            aria-expanded={!recolhida}
            className="flex items-center gap-2 text-left font-semibold uppercase text-slate-900 hover:underline"
          >
            <span className="numero w-3 text-slate-500">{recolhida ? "+" : "−"}</span>
            {categoria.rotulo}
          </button>
        </td>
        <Valor bruto={categoria.total} destaque />
        <td className="numero px-4 py-2 text-right font-semibold">
          {formatarPercentual(categoria.percentual)}
        </td>
        <td className="numero px-4 py-2 text-right font-semibold">{categoria.qtd}</td>
      </tr>

      {!recolhida &&
        categoria.subcategorias.map((sub) => (
          <tr key={sub.chave} className="border-t border-slate-100">
            <td className="py-1.5 pl-12 pr-4 text-slate-700">{sub.rotulo}</td>
            <Valor bruto={sub.total} />
            <td className="numero px-4 py-1.5 text-right text-slate-600">
              {formatarPercentual(sub.percentual)}
            </td>
            <td className="numero px-4 py-1.5 text-right text-slate-600">{sub.qtd}</td>
          </tr>
        ))}
    </>
  );
}

function Valor({ bruto, destaque = false }: { bruto: string; destaque?: boolean }) {
  return (
    <td
      className={`numero px-4 ${destaque ? "py-2 font-semibold" : "py-1.5"} text-right ${
        ehNegativo(bruto) ? "text-negativo" : "text-slate-800"
      }`}
    >
      {formatarValor(bruto)}
    </td>
  );
}
