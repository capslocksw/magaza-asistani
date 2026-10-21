import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { CartProvider } from "@/components/cart-provider";
import { CartSheet } from "@/components/cart-sheet";
import { Footer } from "@/components/footer";
import { Header } from "@/components/header";
import { WidgetEmbed } from "@/components/widget-embed";
import { BRAND, brandConfig } from "@/lib/brand";
import { getCategories } from "@/lib/catalog";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: `${brandConfig.name} — ${brandConfig.tagline}`, template: `%s | ${brandConfig.name}` },
  description: brandConfig.hero.subtitle,
  icons: { icon: "/logo.svg" },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#ffffff" };

export default function RootLayout({ children }: { children: ReactNode }) {
  const categories = getCategories();
  return (
    <html lang="tr" data-brand={BRAND}>
      <body className="min-h-screen">
        <a href="#icerik" className="skip-link">
          İçeriğe geç
        </a>
        <CartProvider>
          <Header categories={categories} />
          <main id="icerik">{children}</main>
          <Footer categories={categories} />
          <CartSheet />
          <WidgetEmbed />
        </CartProvider>
      </body>
    </html>
  );
}
