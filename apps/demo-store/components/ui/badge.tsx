import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold leading-5", {
  variants: {
    variant: {
      deal: "bg-deal text-white",
      brand: "bg-brand-soft text-brand-ink",
      ok: "bg-green-50 text-ok",
      muted: "bg-surface text-muted",
      outline: "border border-line text-muted",
    },
  },
  defaultVariants: { variant: "brand" },
});

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
