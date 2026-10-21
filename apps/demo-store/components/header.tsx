import Link from "next/link";
import { Headset, User } from "lucide-react";
import { brandConfig } from "@/lib/brand";
import type { Category } from "@/lib/types";
import { AskAssistantButton } from "./ask-assistant-button";
import { CartButton, MobileMenu, SearchBox } from "./header-client";

export function Header({ categories }: { categories: Category[] }) {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-white/95 backdrop-blur">
      <div className="hidden bg-chrome text-xs text-white sm:block">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-1.5">
          <p>{brandConfig.topBar}</p>
          <p className="flex items-center gap-1.5">
            <Headset className="size-3.5" aria-hidden="true" /> {brandConfig.supportPhone}
          </p>
        </div>
      </div>
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3 lg:gap-6">
        <MobileMenu categories={categories} />
        <Link href="/" className="flex shrink-0 items-center gap-2" aria-label={`${brandConfig.name} ana sayfa`}>
          <img src="/logo.svg" alt="" className="size-9 sm:size-10" />
          <span className="flex flex-col leading-none">
            <span className="text-lg font-extrabold tracking-tight sm:text-xl">{brandConfig.name}</span>
            <span className="hidden text-[11px] text-muted sm:block">{brandConfig.tagline}</span>
          </span>
        </Link>
        <div className="hidden flex-1 md:block">
          <SearchBox />
        </div>
        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <AskAssistantButton className="hidden lg:inline-flex" />
          <Link href="/" className="hidden items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium hover:bg-surface sm:flex">
            <User className="size-5" aria-hidden="true" /> {brandConfig.b2b ? "Kurumsal giriş" : "Giriş yap"}
          </Link>
          <CartButton />
        </div>
      </div>
      <div className="px-4 pb-3 md:hidden">
        <SearchBox />
      </div>
      <nav aria-label="Kategoriler" className="border-t border-line">
        <ul className="scrollbar-none mx-auto flex max-w-7xl gap-1 overflow-x-auto px-2 text-sm font-medium">
          {categories.map((c) => (
            <li key={c.slug} className="shrink-0">
              <Link href={`/kategori/${c.slug}/`} className="block rounded-md px-3 py-2.5 text-ink hover:bg-brand-soft hover:text-brand-ink">
                {c.name}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
