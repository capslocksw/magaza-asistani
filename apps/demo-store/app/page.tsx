import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import { AskAssistantButton } from "@/components/ask-assistant-button";
import { TrustBar } from "@/components/footer";
import { ProductGrid } from "@/components/product-card";
import { Button } from "@/components/ui/button";
import { brandConfig } from "@/lib/brand";
import { getBestSellers, getCategories, getDeals } from "@/lib/catalog";
import { cn } from "@/lib/utils";

export default function HomePage() {
  const categories = getCategories();
  const bestSellers = getBestSellers(10);
  const deals = getDeals(5);
  const { hero, campaigns } = brandConfig;

  return (
    <div className="mx-auto max-w-7xl space-y-10 px-4 py-6">
      <section className="grid gap-4 lg:grid-cols-3">
        <div className="relative overflow-hidden rounded-2xl bg-chrome p-6 text-white sm:p-10 lg:col-span-2">
          <div className="absolute -right-16 -top-16 size-72 rounded-full bg-brand opacity-30 blur-2xl" aria-hidden="true" />
          <div className="absolute -bottom-24 right-24 size-64 rounded-full bg-brand opacity-20 blur-3xl" aria-hidden="true" />
          <p className="relative inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold">
            <Sparkles className="size-3.5" aria-hidden="true" /> {hero.eyebrow}
          </p>
          <h1 className="relative mt-4 max-w-xl text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl">{hero.title}</h1>
          <p className="relative mt-3 max-w-xl text-sm text-gray-200 sm:text-base">{hero.subtitle}</p>
          <div className="relative mt-6 flex flex-wrap gap-3">
            <AskAssistantButton prompt={brandConfig.assistantPrompt} label={hero.cta} variant="default" size="lg" />
            <Button asChild variant="outline" size="lg" className="border-white/30 bg-transparent text-white hover:bg-white/10">
              <Link href={hero.secondaryHref}>
                {hero.secondary} <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
          </div>
          <p className="relative mt-6 text-xs text-gray-300">
            Örnek: “{brandConfig.assistantPrompt}”
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
          {campaigns.map((c) => (
            <Link
              key={c.title}
              href={c.href}
              className={cn(
                "group flex flex-col justify-between rounded-2xl p-5 transition-transform hover:-translate-y-0.5",
                c.tone === "brand" && "bg-brand-strong text-white",
                c.tone === "dark" && "bg-ink text-white",
                c.tone === "soft" && "bg-brand-soft text-brand-ink",
              )}
            >
              <p className="text-lg font-bold leading-snug">{c.title}</p>
              <p className="mt-1 flex items-center justify-between text-sm">
                {c.text} <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" aria-hidden="true" />
              </p>
            </Link>
          ))}
        </div>
      </section>

      <TrustBar />

      <section aria-labelledby="kategoriler">
        <h2 id="kategoriler" className="text-xl font-bold">
          Kategoriler
        </h2>
        <ul className="mt-4 grid grid-cols-3 gap-3 sm:grid-cols-5 lg:grid-cols-9">
          {categories.map((c) => (
            <li key={c.slug}>
              <Link
                href={`/kategori/${c.slug}/`}
                className="flex h-full flex-col items-center gap-2 rounded-xl border border-line bg-white p-3 text-center text-xs font-semibold hover:border-brand-strong hover:shadow"
              >
                <img src={`/images/cat-${c.slug}.svg`} alt="" className="size-14" />
                {c.name}
                <span className="font-normal text-muted">{c.product_count} ürün</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="cok-satanlar">
        <div className="flex items-end justify-between">
          <h2 id="cok-satanlar" className="text-xl font-bold">
            Çok satanlar
          </h2>
          <Link href={`/kategori/${categories[0]!.slug}/`} className="text-sm font-semibold text-brand-strong hover:underline">
            Tümünü gör
          </Link>
        </div>
        <ProductGrid products={bestSellers} className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5" />
      </section>

      <section className="grid items-center gap-6 rounded-2xl bg-brand-soft p-6 sm:p-8 lg:grid-cols-2">
        <div>
          <h2 className="text-2xl font-extrabold text-brand-ink">Ne alacağınızı bilmiyor musunuz?</h2>
          <p className="mt-2 text-sm text-brand-ink/90">
            {brandConfig.assistantName} sorununuzu dinler, gerekirse bir-iki soru sorar ve teknik föylere dayanarak ana ürün ile
            tamamlayıcılarından oluşan paketi önerir. Paketi tek tıkla sepete ekleyebilirsiniz.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 lg:justify-end">
          <AskAssistantButton prompt={brandConfig.assistantPrompt} label={`“${brandConfig.assistantPrompt}”`} variant="default" />
          <AskAssistantButton label={brandConfig.askLabel} variant="outline" />
        </div>
      </section>

      {deals.length ? (
        <section aria-labelledby="firsatlar">
          <h2 id="firsatlar" className="text-xl font-bold">
            Haftanın fırsatları
          </h2>
          <ProductGrid products={deals} className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5" />
        </section>
      ) : null}
    </div>
  );
}
