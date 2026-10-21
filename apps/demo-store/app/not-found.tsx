import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-20 text-center">
      <h1 className="text-3xl font-extrabold">Sayfa bulunamadı</h1>
      <p className="mt-2 text-muted">Aradığınız sayfa taşınmış ya da hiç var olmamış olabilir.</p>
      <Button asChild className="mt-6">
        <Link href="/">Ana sayfaya dön</Link>
      </Button>
    </div>
  );
}
