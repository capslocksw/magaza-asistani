import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { ProductListing } from "@/components/product-listing";
import { getCategories, getCategory, getCategoryProducts } from "@/lib/catalog";

export const dynamicParams = false;

export function generateStaticParams() {
  return getCategories().map((c) => ({ slug: c.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  return { title: getCategory(slug)?.name ?? "Kategori" };
}

export default async function CategoryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const category = getCategory(slug);
  if (!category) notFound();
  const products = getCategoryProducts(slug);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <nav aria-label="Konum" className="flex items-center gap-1 text-xs text-muted">
        <Link href="/" className="hover:underline">
          Ana sayfa
        </Link>
        <ChevronRight className="size-3" aria-hidden="true" />
        <span aria-current="page">{category.name}</span>
      </nav>
      <div className="mt-3 flex items-center gap-4 rounded-2xl bg-brand-soft p-5">
        <img src={`/images/cat-${category.slug}.svg`} alt="" className="size-16" />
        <div>
          <h1 className="text-2xl font-extrabold text-brand-ink">{category.name}</h1>
          <p className="text-sm text-brand-ink/90">{category.description}</p>
        </div>
      </div>
      <div className="mt-6">
        <ProductListing products={products} />
      </div>
    </div>
  );
}
