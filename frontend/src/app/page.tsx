import Link from "next/link";

const RELATORIOS = [
  {
    href: "/despesas",
    titulo: "Despesas por categoria",
    descricao:
      "Consolida uma ou várias planilhas de despesas por categoria e subcategoria, com coluna por conta bancária.",
    entrada: "Analítico de despesas ou fluxo de caixa",
    saida: "Resumo por categoria em .xlsx",
  },
  {
    href: "/variavel",
    titulo: "Remuneração variável",
    descricao:
      "Cruza os recebimentos do período com os casos e calcula a variável de cada responsável, já com o imposto descontado.",
    entrada: "Visão cubo de recebimentos + relatório de casos",
    saida: "Relatório de variável em .xlsx",
  },
];

export default function Pagina() {
  return (
    <div>
      <h1 className="mb-2 text-xl font-semibold text-slate-900">Qual relatório você precisa?</h1>
      <p className="mb-8 text-sm text-slate-600">
        Escolha o relatório, suba as planilhas e baixe o resultado pronto.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        {RELATORIOS.map((relatorio) => (
          <Link
            key={relatorio.href}
            href={relatorio.href}
            className="group flex flex-col rounded-lg border border-slate-200 bg-white p-6 transition hover:border-slate-900 hover:shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
          >
            <h2 className="text-base font-semibold text-slate-900">{relatorio.titulo}</h2>
            <p className="mt-2 flex-1 text-sm text-slate-600">{relatorio.descricao}</p>

            <dl className="mt-4 space-y-1 border-t border-slate-100 pt-4 text-xs text-slate-500">
              <div className="flex gap-2">
                <dt className="shrink-0 font-medium">Você sobe:</dt>
                <dd>{relatorio.entrada}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="shrink-0 font-medium">Você baixa:</dt>
                <dd>{relatorio.saida}</dd>
              </div>
            </dl>

            <span className="mt-4 text-sm font-medium text-slate-900 group-hover:underline">
              Abrir →
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
