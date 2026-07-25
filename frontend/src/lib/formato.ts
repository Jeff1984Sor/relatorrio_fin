const MOEDA = new Intl.NumberFormat("pt-BR", {
  style: "decimal",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Negativo entre parênteses, padrão contábil. O sinal só muda na apresentação. */
export function formatarValor(bruto: string | number, comoPositivo = false): string {
  const numero = (typeof bruto === "string" ? Number(bruto) : bruto) * (comoPositivo ? -1 : 1);
  if (Number.isNaN(numero)) return "—";
  const texto = MOEDA.format(Math.abs(numero));
  return numero < 0 ? `(${texto})` : texto;
}

export function ehNegativo(bruto: string | number, comoPositivo = false): boolean {
  const numero = (typeof bruto === "string" ? Number(bruto) : bruto) * (comoPositivo ? -1 : 1);
  return numero < 0;
}

export function formatarPercentual(fracao: number): string {
  return `${(fracao * 100).toFixed(1).replace(".", ",")}%`;
}

export function formatarData(iso: string | null): string {
  if (!iso) return "—";
  const data = new Date(`${iso.slice(0, 10)}T12:00:00`);
  if (Number.isNaN(data.getTime())) return "—";
  return data.toLocaleDateString("pt-BR");
}

export function formatarDataHora(iso: string): string {
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return "—";
  return data.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function descreverPeriodo(inicio: string | null, fim: string | null): string {
  if (!inicio || !fim) return "Período não identificado";
  return `${formatarData(inicio)} a ${formatarData(fim)}`;
}
