import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Relatórios financeiros",
  description: "Consolidação de despesas e cálculo da remuneração variável.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="text-sm font-semibold text-slate-900">
              Relatórios
            </Link>
            <nav className="flex gap-6 text-sm text-slate-600">
              <Link href="/despesas" className="hover:text-slate-900">
                Despesas
              </Link>
              <Link href="/variavel" className="hover:text-slate-900">
                Variável
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
