"use client";

import { useState } from "react";

import { ehNegativo, formatarPercentual, formatarValor } from "@/lib/formato";
import type { Categoria, Resumo, Subcategoria } from "@/lib/tipos";

/** Prévia em formato razão contábil: faixa de categoria clicável recolhe as subcategorias. */
export default function TabelaResumo({ resumo }: { resumo: Resumo }) {
  const [recolhidas, setRecolhidas] = useState<Set<string>>(new Set());

  // Uma coluna por conta só faz sentido quando há mais de uma.
  const contas = resumo.contas.length > 1 ? resumo.contas : [];

  function alternar(chave: string) {
    setRecolhidas((atual) => {
      const proximo = new Set(atual);
      if (proximo.has(chave)) proximo.delete(chave);
      else proximo.add(chave);
      return proximo;
    });
  }

  return (
    <div className="overflow-x-auto rounded border border-slate-200">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-800 text-white">
          <tr>
            <th className="px-4 py-2.5 text-left font-medium">Categoria / Subcategoria</th>
            {contas.map((conta) => (
              <th key={conta} className="whitespace-nowrap px-4 py-2.5 text-right font-medium">
                {conta}
              </th>
            ))}
            <th className="px-4 py-2.5 text-right font-medium">Total</th>
            <th className="px-4 py-2.5 text-right font-medium">%</th>
            <th className="px-4 py-2.5 text-right font-medium">Lanç.</th>
          </tr>
        </thead>
        <tbody>
          {resumo.categorias.map((categoria) => (
            <CorpoCategoria
              key={categoria.chave}
              categoria={categoria}
              contas={contas}
              recolhida={recolhidas.has(categoria.chave)}
              onAlternar={() => alternar(categoria.chave)}
            />
          ))}
        </tbody>
        <tfoot className="bg-slate-800 text-white">
          <tr>
            <td className="px-4 py-2.5 font-semibold">TOTAL GERAL</td>
            {contas.map((conta) => (
              <td key={conta} className="numero px-4 py-2.5 text-right font-semibold">
                {formatarValor(resumo.total_por_conta[conta] ?? "0")}
              </td>
            ))}
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
  contas,
  recolhida,
  onAlternar,
}: {
  categoria: Categoria;
  contas: string[];
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
        <Valores no={categoria} contas={contas} destaque />
      </tr>

      {!recolhida &&
        categoria.subcategorias.map((sub) => (
          <tr key={sub.chave} className="border-t border-slate-100">
            <td className="py-1.5 pl-12 pr-4 text-slate-700">{sub.rotulo}</td>
            <Valores no={sub} contas={contas} />
          </tr>
        ))}
    </>
  );
}

function Valores({
  no,
  contas,
  destaque = false,
}: {
  no: Subcategoria;
  contas: string[];
  destaque?: boolean;
}) {
  const peso = destaque ? "py-2 font-semibold" : "py-1.5";
  return (
    <>
      {contas.map((conta) => (
        <Celula key={conta} bruto={no.por_conta[conta] ?? "0"} peso={peso} />
      ))}
      <Celula bruto={no.total} peso={peso} />
      <td className={`numero px-4 text-right ${peso} text-slate-600`}>
        {formatarPercentual(no.percentual)}
      </td>
      <td className={`numero px-4 text-right ${peso} text-slate-600`}>{no.qtd}</td>
    </>
  );
}

function Celula({ bruto, peso }: { bruto: string; peso: string }) {
  const zero = Number(bruto) === 0;
  return (
    <td
      className={`numero px-4 text-right ${peso} ${
        zero ? "text-slate-300" : ehNegativo(bruto) ? "text-negativo" : "text-slate-800"
      }`}
    >
      {zero ? "—" : formatarValor(bruto)}
    </td>
  );
}
