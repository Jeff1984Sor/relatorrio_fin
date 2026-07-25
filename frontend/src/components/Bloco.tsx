type Props = {
  numero: number;
  titulo: string;
  descricao?: string;
  children: React.ReactNode;
};

/** Um dos três passos da página: arquivo → colunas → resumo. */
export default function Bloco({ numero, titulo, descricao, children }: Props) {
  return (
    <section className="mb-8 rounded-lg border border-slate-200 bg-white p-6">
      <div className="mb-5 flex items-start gap-3">
        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white">
          {numero}
        </span>
        <div>
          <h2 className="text-base font-semibold text-slate-900">{titulo}</h2>
          {descricao && <p className="mt-1 text-sm text-slate-500">{descricao}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}
