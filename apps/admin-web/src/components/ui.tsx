import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { clsx, type ClassValue } from "clsx";
import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 disabled:pointer-events-none [&_svg]:size-4",
  {
    variants: {
      variant: {
        default: "bg-primary text-white hover:bg-indigo-800",
        outline: "border border-line bg-white hover:bg-surface",
        ghost: "hover:bg-surface",
        danger: "bg-bad text-white hover:bg-red-800",
      },
      size: { default: "h-9 px-3.5", sm: "h-8 px-2.5 text-xs", lg: "h-11 px-5" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export function Button({
  className,
  variant,
  size,
  asChild,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-xl border border-line bg-white shadow-sm", className)} {...props} />;
}

const field = "h-9 w-full rounded-lg border border-line bg-white px-3 text-sm focus:border-primary focus:outline-none";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(field, className)} {...props} />;
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(field, "pr-8", className)} {...props} />;
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(field, "h-auto py-2 leading-6", className)} {...props} />;
}

export function Label({ htmlFor, children, hint }: { htmlFor: string; children: ReactNode; hint?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium">
      {children}
      {hint ? <span className="ml-1 font-normal text-muted">({hint})</span> : null}
    </label>
  );
}

export function Badge({ className, tone = "neutral", ...props }: HTMLAttributes<HTMLSpanElement> & { tone?: "neutral" | "good" | "bad" | "primary" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-semibold",
        tone === "neutral" && "bg-slate-100 text-slate-700",
        tone === "good" && "bg-green-50 text-good",
        tone === "bad" && "bg-red-50 text-bad",
        tone === "primary" && "bg-primary-soft text-primary",
        className,
      )}
      {...props}
    />
  );
}

export function Spinner({ label = "Yükleniyor…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-muted" role="status">
      <span className="size-4 animate-spin rounded-full border-2 border-primary border-t-transparent" aria-hidden="true" />
      {label}
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  return (
    <p className="rounded-lg bg-red-50 p-3 text-sm text-bad" role="alert">
      Veri alınamadı: {error instanceof Error ? error.message : String(error)}
    </p>
  );
}
