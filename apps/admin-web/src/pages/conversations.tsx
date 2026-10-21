import * as Dialog from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { ThumbsDown, ThumbsUp, X } from "lucide-react";
import { useState } from "react";
import { DataTable } from "@/components/data-table";
import { PageHeader, Panel } from "@/components/panel";
import { Badge, ErrorNote, Input, Spinner } from "@/components/ui";
import { apiGet, qs } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { useFilters } from "@/lib/state";
import type { ConversationEvent, ConversationItem } from "@/lib/types";

const EVENT_LABELS: Record<string, string> = {
  visit: "Ziyaret",
  widget_open: "Widget açıldı",
  tool_call: "Araç çağrısı",
  product_shown: "Ürün gösterildi",
  add_to_cart: "Sepete eklendi",
  quote_request: "Teklif talebi",
  order: "Sipariş",
  feedback: "Geri bildirim",
};

const columns: ColumnDef<ConversationItem, unknown>[] = [
  { header: "Başlangıç", accessorKey: "started", cell: (c) => <span className="whitespace-nowrap text-muted">{dateTime(c.getValue() as string)}</span> },
  { header: "Konu", accessorKey: "topic_label", cell: (c) => <Badge tone="primary">{c.getValue() as string}</Badge> },
  { header: "İlk mesaj", accessorKey: "first_message" },
  { header: "Mesaj", accessorKey: "turns" },
  {
    header: "Sonuç",
    id: "outcome",
    cell: ({ row }) => (
      <span className="flex flex-wrap gap-1">
        {row.original.adds ? <Badge tone="good">Sepete ekledi</Badge> : <Badge>Eklemedi</Badge>}
        {row.original.likes ? <ThumbsUp className="size-4 text-good" aria-label="Beğendi" /> : null}
        {row.original.dislikes ? <ThumbsDown className="size-4 text-bad" aria-label="Beğenmedi" /> : null}
        {row.original.guardrails ? <Badge tone="bad">Guardrail</Badge> : null}
      </span>
    ),
  },
];

function ConversationDetail({ sessionId, onClose }: { sessionId: string | null; onClose: () => void }) {
  const { tenantId } = useFilters();
  const detail = useQuery({
    queryKey: ["conversation", tenantId, sessionId],
    queryFn: () => apiGet<{ events: ConversationEvent[] }>(`/api/tenants/${tenantId}/conversations/${sessionId}`),
    enabled: Boolean(sessionId && tenantId),
  });
  return (
    <Dialog.Root open={Boolean(sessionId)} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30" />
        <Dialog.Content className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col bg-white shadow-2xl" data-testid="conversation-detail">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <Dialog.Title className="font-bold">Konuşma ayrıntısı</Dialog.Title>
            <Dialog.Close aria-label="Kapat" className="rounded p-1 hover:bg-surface">
              <X className="size-5" />
            </Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">Oturumdaki mesajlar ve olaylar</Dialog.Description>
          <div className="flex-1 space-y-3 overflow-y-auto p-5">
            {detail.isLoading ? <Spinner /> : null}
            {detail.data?.events.map((e, i) => {
              const p = e.payload as Record<string, unknown>;
              if (e.event_type === "user_message")
                return (
                  <p key={i} className="ml-auto max-w-[85%] rounded-xl rounded-br-sm bg-ink px-3 py-2 text-sm text-white">
                    {String(p.text ?? "")}
                  </p>
                );
              if (e.event_type === "agent_message")
                return (
                  <div key={i} className="max-w-[85%] rounded-xl rounded-bl-sm border border-line px-3 py-2 text-sm">
                    <p className="whitespace-pre-line">{String(p.text ?? "")}</p>
                    <p className="mt-1 text-[11px] text-muted">
                      {e.model} · {e.latency_ms} ms{Array.isArray(p.guardrails) && p.guardrails.length ? ` · guardrail: ${p.guardrails.join(", ")}` : ""}
                    </p>
                  </div>
                );
              return (
                <p key={i} className="text-center text-xs text-muted">
                  {dateTime(e.ts)} · {EVENT_LABELS[e.event_type] ?? e.event_type}
                  {Array.isArray(p.skus) ? ` · ${(p.skus as string[]).join(", ")}` : ""}
                  {p.rating ? ` · ${String(p.rating) === "up" ? "beğendi" : "beğenmedi"}` : ""}
                </p>
              );
            })}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function ConversationList({ limit = 25, query = "" }: { limit?: number; query?: string }) {
  const { tenantId, range } = useFilters();
  const [selected, setSelected] = useState<string | null>(null);
  const list = useQuery({
    queryKey: ["conversations", tenantId, range.start, range.end, query, limit],
    queryFn: () =>
      apiGet<{ items: ConversationItem[] }>(`/api/tenants/${tenantId}/conversations${qs({ start: range.start, end: range.end, q: query, limit })}`),
    enabled: Boolean(tenantId),
  });
  if (list.isLoading) return <Spinner />;
  if (list.error) return <ErrorNote error={list.error} />;
  return (
    <>
      <DataTable data={list.data?.items ?? []} columns={columns} onRowClick={(row) => setSelected(row.session_id)} dense />
      <ConversationDetail sessionId={selected} onClose={() => setSelected(null)} />
    </>
  );
}

export function ConversationsPage() {
  const [query, setQuery] = useState("");
  return (
    <div className="space-y-5">
      <PageHeader title="Konuşmalar" description="Konuşma gezgini: ilk mesajda arayın, ayrıntı için satıra tıklayın." />
      <Panel title="Konuşma gezgini" dataset="konusmalar">
        <div className="border-b border-line p-3">
          <label htmlFor="conv-search" className="sr-only">
            Konuşmalarda ara
          </label>
          <Input id="conv-search" placeholder="İlk mesajda ara (ör. korniş, koli)" value={query} onChange={(e) => setQuery(e.target.value)} className="max-w-sm" />
        </div>
        <ConversationList limit={50} query={query} />
      </Panel>
    </div>
  );
}
