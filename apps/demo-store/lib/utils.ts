import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

const TR_FOLD: Record<string, string> = { ç: "c", ğ: "g", ı: "i", İ: "i", ö: "o", ş: "s", ü: "u", â: "a", î: "i", û: "u" };

/** Lower-cases with Turkish rules and folds diacritics so "Korniş" matches "kornis". */
export function normalizeTr(text: string): string {
  return text
    .toLocaleLowerCase("tr-TR")
    .replace(/[çğıİöşüâîû]/g, (ch) => TR_FOLD[ch] ?? ch)
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function discountPercent(price: number, listPrice?: number | null): number | null {
  if (!listPrice || listPrice <= price) return null;
  return Math.round(((listPrice - price) / listPrice) * 100);
}

export function installmentText(maxInstallments?: number | null): string | null {
  return maxInstallments && maxInstallments > 1 ? `${maxInstallments} aya varan taksit` : null;
}
