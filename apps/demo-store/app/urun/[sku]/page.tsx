import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CheckCircle2, ChevronRight, CreditCard, FileText, PackageX, Truck } from "lucide-react";
import { AddToCartButton } from "@/components/add-to-cart-button";
import { AskAssistantButton } from "@/components/ask-assistant-button";
import { Price, Rating } from "@/components/price";
import { ProductGallery } from "@/components/product-gallery";
import { ProductGrid } from "@/components/product-card";
import { Badge } from "@/components/ui/badge";
import { brandConfig } from "@/lib/brand";
import { getCategory, getComplements, getProduct, getProducts, getRelated, toSummary } from "@/lib/catalog";
import { discountPercent, installmentText } from "@/lib/utils";

export const dynamicParams = false;

export function generateStaticParams() {
  return getProducts().map((p) => ({ sku: p.sku }));
}

export async function generateMetadata({ params }: { params: Promise<{ sku: string }> }): Promise<Metadata> {
  const { sku } = await params;
  const p = getProduct(sku);
  return { title: p?.title ?? "Ürün", description: p?.description };
}

function specValue(value: string | number | boolean, unit?: string | null): string {
  const text = typeof value === "boolean" ? (value ? "Evet" : "Hayır") : typeof value === "number" ? String(value).replace(".", ",") : value;
  return unit ? `${text} ${unit}` : text;
}

export default async function ProductPage({ params }: { params: Promise<{ sku: string }> }) {
  const { sku } = await params;
  const product = getProduct(sku);
  if (!product) notFound();
  const category = getCategory(product.category);
  const complements = getComplements(product);
  const related = getRelated(product, 5);
  const pct = discountPercent(product.price, product.list_price);
  const inStock = product.stock > 0;
  const installments = installmentText(product.max_installments);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <nav aria-label="Konum" className="flex flex-wrap items-center gap-1 text-xs text-muted">
        <Link href="/" className="hover:underline">
          Ana sayfa
        </Link>
        <ChevronRight className="size-3" aria-hidden="true" />
        <Link href={`/kategori/${product.category}/`} className="hover:underline">
          {category?.name ?? product.category_name}
        </Link>
        <ChevronRight className="size-3" aria-hidden="true" />
        <span aria-current="page" className="line-clamp-1">
          {product.title}
        </span>
      </nav>

      <div className="mt-4 grid gap-8 lg:grid-cols-2">
        <ProductGallery
          images={[
            { src: product.image_url, alt: product.title },
            { src: `/images/cat-${product.category}.svg`, alt: `${product.category_name} kategorisi` },
          ]}
          badge={pct ? `%${pct} indirim` : null}
        />

        <div className="space-y-5">
          <div>
            <Link href={`/kategori/${product.category}/`} className="text-xs font-bold uppercase tracking-wide text-brand-strong">
              {product.brand}
            </Link>
            <h1 className="mt-1 text-2xl font-extrabold leading-tight sm:text-3xl" data-testid="product-title">
              {product.title}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted">
              <Rating rating={product.rating} count={product.review_count} />
              <span>Ürün kodu: {product.sku}</span>
            </div>
          </div>

          <div className="rounded-xl border border-line p-4">
            <Price price={product.price} listPrice={product.list_price} size="lg" />
            <p className="text-xs text-muted">{product.unit} fiyatı, KDV dahil</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {installments ? (
                <Badge variant="brand">
                  <CreditCard className="size-3" aria-hidden="true" /> {installments}
                </Badge>
              ) : null}
              {product.free_shipping ? (
                <Badge variant="ok">
                  <Truck className="size-3" aria-hidden="true" /> Kargo bedava
                </Badge>
              ) : (
                <Badge variant="muted">{brandConfig.freeShippingThreshold.toLocaleString("tr-TR")} TL üzeri kargo bedava</Badge>
              )}
              {inStock ? (
                <Badge variant="ok">
                  <CheckCircle2 className="size-3" aria-hidden="true" /> Stokta ({product.stock > 50 ? "50+" : product.stock} {product.unit})
                </Badge>
              ) : (
                <Badge variant="muted">
                  <PackageX className="size-3" aria-hidden="true" /> Stokta yok
                </Badge>
              )}
            </div>
          </div>

          {inStock ? (
            <AddToCartButton product={toSummary(product)} />
          ) : (
            <p className="rounded-lg bg-surface p-4 text-sm font-medium text-muted">Bu ürün geçici olarak stokta yok. Benzer ürünler için asistana sorabilirsiniz.</p>
          )}

          <div className="flex flex-wrap items-center gap-3 rounded-xl bg-brand-soft p-4">
            <p className="flex-1 text-sm text-brand-ink">
              Bu ürünle ne lazım olur, nasıl uygulanır? <strong>{brandConfig.assistantName}</strong> teknik föye bakarak yanıtlasın.
            </p>
            <AskAssistantButton prompt={`${product.title} için başka ne lazım?`} variant="default" size="sm" />
          </div>

          <p className="text-sm leading-6 text-ink">{product.description}</p>

          {product.doc_url ? (
            <a
              href={product.doc_url}
              className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2.5 text-sm font-semibold hover:bg-surface"
              target="_blank"
              rel="noreferrer"
              data-testid="datasheet-link"
            >
              <FileText className="size-4 text-brand-strong" aria-hidden="true" /> Teknik föyü indir (PDF)
            </a>
          ) : null}
        </div>
      </div>

      <section className="mt-10" aria-labelledby="teknik-ozellikler">
        <h2 id="teknik-ozellikler" className="text-xl font-bold">
          Teknik özellikler
        </h2>
        <table className="mt-3 w-full max-w-3xl overflow-hidden rounded-xl border border-line text-sm">
          <tbody>
            {product.specs.map((s, i) => (
              <tr key={s.key} className={i % 2 ? "bg-white" : "bg-surface"}>
                <th scope="row" className="w-1/2 px-4 py-2.5 text-left font-medium text-muted">
                  {s.label}
                </th>
                <td className="px-4 py-2.5 font-semibold">{specValue(s.value, s.unit)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {complements.length ? (
        <section className="mt-10" aria-labelledby="birlikte">
          <h2 id="birlikte" className="text-xl font-bold">
            Birlikte iyi gider
          </h2>
          <ProductGrid products={complements} className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5" />
        </section>
      ) : null}

      {related.length ? (
        <section className="mt-10" aria-labelledby="benzer">
          <h2 id="benzer" className="text-xl font-bold">
            Benzer ürünler
          </h2>
          <ProductGrid products={related} className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5" />
        </section>
      ) : null}
    </div>
  );
}
