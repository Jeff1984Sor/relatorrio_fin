import type { Metadata } from "next";
import Link from "next/link";
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
          <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
            <Link href="/" className="text-sm font-semibold text-slate-900">
              Resumo de despesas
            </Link>
            <nav className="flex gap-6 text-sm text-slate-600">
              <Link href="/" className="hover:text-slate-900">
                Nova planilha
              </Link>
              <Link href="/historico" className="hover:text-slate-900">
                Histórico
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
