import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Resumo de despesas por categoria",
  description: "Sobe a planilha analítica e baixa o consolidado por categoria.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto max-w-5xl px-6 py-4">
            <span className="text-sm font-semibold text-slate-900">Resumo de despesas</span>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
