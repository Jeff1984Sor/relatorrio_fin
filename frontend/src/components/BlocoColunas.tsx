"use client";

import type { ArquivoInspecionado, CampoMapeamento, Mapeamento } from "@/lib/tipos";

const CAMPOS: { campo: CampoMapeamento; rotulo: string; obrigatorio: boolean }[] = [
  { campo: "valor", rotulo: "Valor a consolidar", obrigatorio: true },
  { campo: "categoria", rotulo: "Categoria", obrigatorio: false },
  { campo: "subcategoria", rotulo: "Subcategoria (se houver coluna própria)", obrigatorio: false },
  { campo: "conta", rotulo: "Conta bancária", obrigatorio: false },
  { campo: "data", rotulo: "Data", obrigatorio: false },
  { campo: "fornecedor", rotulo: "Fornecedor", obrigatorio: false },
];

type Props = {
  arquivo: ArquivoInspecionado;
  qtdArquivos: number;
  mapeamento: Mapeamento;
  processando: boolean;
  onMapeamento: (mapeamento: Mapeamento) => void;
  onProcessar: () => void;
};

export default function BlocoColunas({
  arquivo,
  qtdArquivos,
  mapeamento,
  processando,
  onMapeamento,
  onProcessar,
}: Props) {
  return (
    <div className="space-y-6">
      {qtdArquivos > 1 && (
        <p className="rounded border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-600">
          O mapeamento abaixo foi detectado em <strong>{arquivo.nome}</strong> e vale para as{" "}
          {qtdArquivos} planilhas. Se elas tiverem formatos diferentes, processe em lotes
          separados.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {CAMPOS.map(({ campo, rotulo, obrigatorio }) => (
          <label key={campo} className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">
              {rotulo}
              {obrigatorio && <span className="ml-1 text-negativo">*</span>}
            </span>
            <select
              value={mapeamento[campo] ?? ""}
              onChange={(e) =>
                onMapeamento({
                  ...mapeamento,
                  [campo]: e.target.value === "" ? null : Number(e.target.value),
                })
              }
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm focus:border-slate-900 focus:outline-none"
            >
              <option value="">— não usar —</option>
              {arquivo.colunas.map((coluna, indice) => (
                <option key={`${coluna}-${indice}`} value={indice}>
                  {coluna}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>

      <label className="flex items-start gap-2 border-t border-slate-200 pt-5 text-sm">
        <input
          type="checkbox"
          checked={mapeamento.somente_preenchidos}
          onChange={(e) =>
            onMapeamento({ ...mapeamento, somente_preenchidos: e.target.checked })
          }
          className="mt-0.5"
        />
        <span>
          Considerar só as linhas com a coluna de valor preenchida
          <span className="block text-xs text-slate-500">
            Ligado automaticamente quando a coluna é <strong>Débito</strong>: as linhas em
            branco são créditos (entradas), não despesas.
          </span>
        </span>
      </label>

      <p className="text-xs text-slate-500">
        Nomes escritos de formas diferentes são sempre unificados, e{" "}
        <code className="rounded bg-slate-100 px-1">Categoria : Subcategoria</code> na mesma
        célula é separado automaticamente.
      </p>

      {arquivo.amostra.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-slate-600 hover:text-slate-900">
            Ver as primeiras linhas de {arquivo.nome}
          </summary>
          <div className="mt-3 overflow-x-auto rounded border border-slate-200">
            <table className="min-w-full text-xs">
              <thead className="bg-slate-100">
                <tr>
                  {arquivo.colunas.map((coluna, indice) => (
                    <th key={indice} className="whitespace-nowrap px-3 py-2 text-left font-medium">
                      {coluna}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {arquivo.amostra.map((linha, indiceLinha) => (
                  <tr key={indiceLinha} className="border-t border-slate-100">
                    {arquivo.colunas.map((_, indiceColuna) => (
                      <td key={indiceColuna} className="whitespace-nowrap px-3 py-1.5">
                        {linha[indiceColuna] ?? ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}

      <button
        type="button"
        onClick={onProcessar}
        disabled={processando || mapeamento.valor === null}
        className="rounded bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {processando ? "Consolidando…" : "Consolidar despesas"}
      </button>
      {mapeamento.valor === null && (
        <p className="text-sm text-negativo">
          Escolha qual coluna tem o valor a consolidar para continuar.
        </p>
      )}
    </div>
  );
}
