import type { Metadata } from "next";
import { SearchResults } from "@/components/search-results";

export const metadata: Metadata = { title: "Arama" };

export default function SearchPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <SearchResults />
    </div>
  );
}
