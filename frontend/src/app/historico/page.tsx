import { Suspense } from "react";

import PainelHistorico from "./PainelHistorico";

export default function Pagina() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Carregando histórico…</p>}>
      <PainelHistorico />
    </Suspense>
  );
}
