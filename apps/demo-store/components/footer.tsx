import Link from "next/link";
import { CreditCard, RotateCcw, ShieldCheck, Truck } from "lucide-react";
import { brandConfig } from "@/lib/brand";
import type { Category } from "@/lib/types";

const TRUST_ICONS = [Truck, ShieldCheck, CreditCard, RotateCcw];

export function TrustBar() {
  return (
    <ul className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {brandConfig.trust.map((text, i) => {
        const Icon = TRUST_ICONS[i % TRUST_ICONS.length]!;
        return (
          <li key={text} className="flex items-center gap-3 rounded-xl border border-line bg-white p-3 text-sm font-medium">
            <span className="grid size-10 shrink-0 place-items-center rounded-full bg-brand-soft text-brand-ink">
              <Icon className="size-5" aria-hidden="true" />
            </span>
            {text}
          </li>
        );
      })}
    </ul>
  );
}

export function Footer({ categories }: { categories: Category[] }) {
  return (
    <footer className="mt-16 bg-chrome text-gray-200">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-lg font-extrabold text-white">{brandConfig.name}</p>
          <p className="mt-2 text-sm text-gray-300">{brandConfig.tagline}</p>
          <p className="mt-4 text-sm">Müşteri hizmetleri: {brandConfig.supportPhone}</p>
        </div>
        <div>
          <p className="font-semibold text-white">Kategoriler</p>
          <ul className="mt-3 space-y-1.5 text-sm">
            {categories.slice(0, 6).map((c) => (
              <li key={c.slug}>
                <Link href={`/kategori/${c.slug}/`} className="hover:text-white hover:underline">
                  {c.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-semibold text-white">Alışveriş</p>
          <ul className="mt-3 space-y-1.5 text-sm">
            <li>Kargo ve teslimat</li>
            <li>İade ve değişim</li>
            <li>{brandConfig.b2b ? "Kurumsal teklif" : "Taksit seçenekleri"}</li>
            <li>
              <a href="/feed.xml" className="hover:text-white hover:underline">
                Ürün feed&apos;i (XML)
              </a>
            </li>
          </ul>
        </div>
        <div>
          <p className="font-semibold text-white">Demo bilgisi</p>
          <p className="mt-3 text-sm text-gray-300">
            Bu mağaza Mağaza Asistanım için hazırlanmış kurgusal bir demodur. Markalar, ürünler ve fiyatlar gerçek değildir; ödeme alınmaz.
          </p>
        </div>
      </div>
      <p className="border-t border-white/10 py-4 text-center text-xs text-gray-200">© 2026 {brandConfig.name} — demo vitrin</p>
    </footer>
  );
}
