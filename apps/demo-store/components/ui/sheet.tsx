"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export const Sheet = Dialog.Root;
export const SheetTrigger = Dialog.Trigger;
export const SheetClose = Dialog.Close;

export function SheetContent({
  title,
  description,
  children,
  className,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in" />
      <Dialog.Content
        className={cn(
          "fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-white shadow-2xl outline-none",
          className,
        )}
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <Dialog.Title className="text-lg font-bold">{title}</Dialog.Title>
          <Dialog.Close className="rounded-md p-2 text-muted hover:bg-surface" aria-label="Kapat">
            <X className="size-5" />
          </Dialog.Close>
        </div>
        {description ? <Dialog.Description className="sr-only">{description}</Dialog.Description> : null}
        {children}
      </Dialog.Content>
    </Dialog.Portal>
  );
}
