import type { Metadata } from "next";
import { OrderConfirmation } from "@/components/order-confirmation";

export const metadata: Metadata = { title: "Sipariş onayı" };

export default function OrderConfirmationPage() {
  return (
    <div className="px-4 py-10">
      <OrderConfirmation />
    </div>
  );
}
