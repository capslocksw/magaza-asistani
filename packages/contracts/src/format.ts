/**
 * Formats a TRY amount the way Turkish storefronts do: `₺1.234,90`.
 * Implemented by hand (not Intl) so output is identical in every runtime/ICU build.
 */
export function formatTRY(value: number): string {
  const [intPart = "0", decPart = "00"] = Math.abs(value).toFixed(2).split(".");
  const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${value < 0 ? "-" : ""}₺${grouped},${decPart}`;
}
