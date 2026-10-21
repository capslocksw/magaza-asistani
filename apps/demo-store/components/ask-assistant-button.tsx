"use client";

import { MessageCircle } from "lucide-react";
import { brandConfig } from "@/lib/brand";
import { cn } from "@/lib/utils";
import { openAssistant } from "./widget-embed";
import { Button, type ButtonProps } from "./ui/button";

export function AskAssistantButton({
  prompt,
  label,
  className,
  variant = "soft",
  size,
}: {
  prompt?: string;
  label?: string;
  className?: string;
  variant?: ButtonProps["variant"];
  size?: ButtonProps["size"];
}) {
  return (
    <Button variant={variant} size={size} className={cn(className)} onClick={() => openAssistant(prompt)}>
      <MessageCircle aria-hidden="true" /> {label ?? brandConfig.askLabel}
    </Button>
  );
}
