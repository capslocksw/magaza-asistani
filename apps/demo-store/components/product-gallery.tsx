"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Badge } from "./ui/badge";

export function ProductGallery({ images, badge }: { images: { src: string; alt: string }[]; badge?: string | null }) {
  const [active, setActive] = useState(0);
  const current = images[active] ?? images[0]!;
  return (
    <div className="flex flex-col-reverse gap-3 sm:flex-row">
      <div className="flex gap-2 sm:flex-col" role="tablist" aria-label="Ürün görselleri">
        {images.map((img, i) => (
          <button
            key={img.src}
            type="button"
            role="tab"
            aria-selected={i === active}
            aria-label={`Görsel ${i + 1}`}
            onClick={() => setActive(i)}
            className={cn("size-16 overflow-hidden rounded-lg border-2 bg-surface sm:size-20", i === active ? "border-brand-strong" : "border-line")}
          >
            <img src={img.src} alt="" className="size-full object-cover" />
          </button>
        ))}
      </div>
      <div className="relative aspect-square flex-1 overflow-hidden rounded-2xl border border-line bg-surface">
        <img src={current.src} alt={current.alt} className="size-full object-contain" />
        {badge ? (
          <Badge variant="deal" className="absolute left-3 top-3 text-xs">
            {badge}
          </Badge>
        ) : null}
      </div>
    </div>
  );
}
