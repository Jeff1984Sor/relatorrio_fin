"use client";

import { useRef, useState } from "react";

const EXTENSOES = [".xlsx", ".xls", ".xlsm", ".csv"];

type Props = {
  arquivos: File[];
  carregando: boolean;
  onEscolher: (arquivos: File[]) => void;
  onRemover: (indice: number) => void;
};

export default function Dropzone({ arquivos, carregando, onEscolher, onRemover }: Props) {
  const [arrastando, setArrastando] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  function abrirSeletor() {
    input.current?.click();
  }

  function aoSoltar(evento: React.DragEvent) {
    evento.preventDefault();
    setArrastando(false);
    const escolhidos = Array.from(evento.dataTransfer.files ?? []);
    if (escolhidos.length) onEscolher(escolhidos);
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
        aria-label="Escolher as planilhas de despesas"
        aria-busy={carregando}
        onClick={abrirSeletor}
        onKeyDown={aoTeclar}
        onDragOver={(e) => {
          e.preventDefault();
          setArrastando(true);
        }}
        onDragLeave={() => setArrastando(false)}
        onDrop={aoSoltar}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2 ${
          arrastando
            ? "border-slate-900 bg-slate-100"
            : "border-slate-300 bg-slate-50 hover:border-slate-400"
        }`}
      >
        {carregando ? (
          <p className="text-sm text-slate-600">Lendo as planilhas…</p>
        ) : (
          <>
            <p className="text-sm font-medium text-slate-900">
              {arquivos.length
                ? "Clique ou arraste para adicionar mais planilhas"
                : "Arraste as planilhas aqui ou clique para escolher"}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Pode subir várias de uma vez — {EXTENSOES.join(", ")}, até 15 MB cada
            </p>
          </>
        )}
      </div>

      {arquivos.length > 0 && (
        <ul className="mt-4 divide-y divide-slate-100 rounded border border-slate-200">
          {arquivos.map((arquivo, indice) => (
            <li
              key={`${arquivo.name}-${indice}`}
              className="flex items-center justify-between gap-4 px-4 py-2 text-sm"
            >
              <span className="truncate text-slate-800">{arquivo.name}</span>
              <span className="flex shrink-0 items-center gap-4">
                <span className="numero text-xs text-slate-500">
                  {(arquivo.size / 1024 / 1024).toFixed(1)} MB
                </span>
                <button
                  type="button"
                  onClick={() => onRemover(indice)}
                  className="text-xs text-slate-500 underline hover:text-negativo"
                  aria-label={`Remover ${arquivo.name}`}
                >
                  remover
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      <input
        ref={input}
        type="file"
        multiple
        accept={EXTENSOES.join(",")}
        className="hidden"
        onChange={(e) => {
          const escolhidos = Array.from(e.target.files ?? []);
          if (escolhidos.length) onEscolher(escolhidos);
          e.target.value = "";
        }}
      />
    </div>
  );
}
