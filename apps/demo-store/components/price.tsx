import { formatTRY } from "@magaza/contracts";
import { Star } from "lucide-react";
import { cn, discountPercent } from "@/lib/utils";

export function Price({
  price,
  listPrice,
  size = "md",
  className,
}: {
  price: number;
  listPrice?: number | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const pct = discountPercent(price, listPrice);
  return (
    <div className={cn("flex flex-wrap items-baseline gap-x-2", className)}>
      {pct ? (
        <span className="text-xs text-muted line-through" aria-label={`Eski fiyat ${formatTRY(listPrice!)}`}>
          {formatTRY(listPrice!)}
        </span>
      ) : null}
      <span
        className={cn(
          "font-bold tracking-tight",
          pct ? "text-deal" : "text-ink",
          size === "sm" && "text-base",
          size === "md" && "text-lg",
          size === "lg" && "text-3xl",
        )}
      >
        {formatTRY(price)}
      </span>
    </div>
  );
}

export function Rating({ rating, count }: { rating?: number | null; count?: number | null }) {
  if (!rating) return null;
  return (
    <div className="flex items-center gap-1 text-xs text-muted" aria-label={`5 üzerinden ${rating} puan, ${count ?? 0} değerlendirme`}>
      <span className="flex" aria-hidden="true">
        {[1, 2, 3, 4, 5].map((i) => (
          <Star key={i} className={cn("size-3.5", i <= Math.round(rating) ? "fill-amber-400 text-amber-400" : "text-gray-300")} />
        ))}
      </span>
      <span>
        {rating.toFixed(1).replace(".", ",")} ({count ?? 0})
      </span>
    </div>
  );
}
