import type { Metadata } from "next";
import { CheckoutForm } from "@/components/checkout-form";

export const metadata: Metadata = { title: "Ödeme" };

export default function CheckoutPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <h1 className="mb-6 text-2xl font-extrabold">Ödeme</h1>
      <CheckoutForm />
    </div>
  );
}
