import { formatTRY } from "@magaza/contracts";

export { formatTRY };

const intFmt = new Intl.NumberFormat("tr-TR");

export function int(value: number | null | undefined): string {
  return value == null ? "—" : intFmt.format(Math.round(value));
}

/** 0.1234 -> "%12,3" (Turkish places the percent sign first). */
export function pct(value: number | null | undefined, digits = 1): string {
  return value == null ? "—" : `%${(value * 100).toFixed(digits).replace(".", ",")}`;
}

/** Already a percentage (e.g. 12.5) -> "+%12,5". */
export function delta(value: number | null | undefined): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}%${Math.abs(value).toFixed(1).replace(".", ",")}`;
}

export function usd(value: number | null | undefined): string {
  return value == null ? "—" : `$${value.toFixed(2)}`;
}

export function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function shortDate(iso: string): string {
  const [, m, d] = iso.slice(0, 10).split("-");
  return `${d}.${m}`;
}

export function dateTime(iso: string): string {
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  return d.toLocaleString("tr-TR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}
