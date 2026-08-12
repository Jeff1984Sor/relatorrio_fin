"use client";

import { useRef } from "react";

const EXTENSOES = [".xlsx", ".xls", ".xlsm", ".csv"];

type Props = {
  rotulo: string;
  ajuda: string;
  arquivo: File | null;
  onEscolher: (arquivo: File) => void;
};

/** Escolha de um arquivo específico e nomeado, diferente da dropzone de lote. */
export default function SeletorArquivo({ rotulo, ajuda, arquivo, onEscolher }: Props) {
  const input = useRef<HTMLInputElement>(null);

  function abrir() {
    input.current?.click();
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={rotulo}
      onClick={abrir}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          abrir();
        }
      }}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        const escolhido = e.dataTransfer.files?.[0];
        if (escolhido) onEscolher(escolhido);
      }}
      className="cursor-pointer rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 px-5 py-6 transition hover:border-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
    >
      <p className="text-sm font-medium text-slate-900">{rotulo}</p>
      <p className="mt-0.5 text-xs text-slate-500">{ajuda}</p>
      <p className="mt-3 truncate text-sm">
        {arquivo ? (
          <span className="font-medium text-slate-800">{arquivo.name}</span>
        ) : (
          <span className="text-slate-400">Nenhum arquivo escolhido</span>
        )}
      </p>

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
