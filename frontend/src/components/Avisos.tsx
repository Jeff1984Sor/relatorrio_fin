import type { Aviso } from "@/lib/tipos";

export default function Avisos({ avisos }: { avisos: Aviso[] }) {
  if (avisos.length === 0) return null;

  return (
    <div className="mt-6 border-l-2 border-amber-400 pl-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
        Vale conferir
      </p>
      <ul className="mt-2 space-y-2">
        {avisos.map((aviso) => (
          <li key={aviso.tipo} className="text-sm text-slate-600">
            {aviso.mensagem}
            {aviso.detalhes.length > 0 && (
              <span className="mt-0.5 block text-xs text-slate-500">
                {aviso.tipo === "valor_invalido" ? "Linhas: " : ""}
                {aviso.detalhes.slice(0, 12).join(", ")}
                {aviso.detalhes.length > 12 && ` e mais ${aviso.detalhes.length - 12}`}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
