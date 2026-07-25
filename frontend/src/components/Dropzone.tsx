"use client";

import { useRef, useState } from "react";

const EXTENSOES = [".xlsx", ".xls", ".xlsm", ".csv"];

type Props = {
  arquivo: File | null;
  carregando: boolean;
  onEscolher: (arquivo: File) => void;
};

export default function Dropzone({ arquivo, carregando, onEscolher }: Props) {
  const [arrastando, setArrastando] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  function abrirSeletor() {
    input.current?.click();
  }

  function aoSoltar(evento: React.DragEvent) {
    evento.preventDefault();
    setArrastando(false);
    const escolhido = evento.dataTransfer.files?.[0];
    if (escolhido) onEscolher(escolhido);
  }

  function aoTeclar(evento: React.KeyboardEvent) {
    if (evento.key === "Enter" || evento.key === " ") {
      evento.preventDefault();
      abrirSeletor();
    }
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Escolher a planilha analítica de despesas"
        aria-busy={carregando}
        onClick={abrirSeletor}
        onKeyDown={aoTeclar}
        onDragOver={(e) => {
          e.preventDefault();
          setArrastando(true);
        }}
        onDragLeave={() => setArrastando(false)}
        onDrop={aoSoltar}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-12 text-center transition focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 ${
          arrastando
            ? "border-slate-900 bg-slate-100"
            : "border-slate-300 bg-slate-50 hover:border-slate-400"
        }`}
      >
        {carregando ? (
          <p className="text-sm text-slate-600">Lendo a planilha…</p>
        ) : arquivo ? (
          <>
            <p className="text-sm font-medium text-slate-900">{arquivo.name}</p>
            <p className="mt-1 text-xs text-slate-500">
              {(arquivo.size / 1024 / 1024).toFixed(1)} MB — clique para trocar de arquivo
            </p>
          </>
        ) : (
          <>
            <p className="text-sm font-medium text-slate-900">
              Arraste a planilha aqui ou clique para escolher
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {EXTENSOES.join(", ")} — até 15 MB
            </p>
          </>
        )}
      </div>
      <input
        ref={input}
        type="file"
        accept={EXTENSOES.join(",")}
        className="hidden"
        onChange={(e) => {
          const escolhido = e.target.files?.[0];
          if (escolhido) onEscolher(escolhido);
          e.target.value = "";
        }}
      />
    </div>
  );
}
