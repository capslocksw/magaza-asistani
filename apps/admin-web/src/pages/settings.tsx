import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, RefreshCw, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Panel } from "@/components/panel";
import { Badge, Button, ErrorNote, Input, Label, Select, Spinner, Textarea } from "@/components/ui";
import { apiGet, apiSend } from "@/lib/api";
import { useFilters } from "@/lib/state";
import type { PersonaTemplate, TenantConfig } from "@/lib/types";

export function SettingsPage() {
  const { tenantId } = useFilters();
  const client = useQueryClient();
  const tenant = useQuery({ queryKey: ["tenant", tenantId], queryFn: () => apiGet<TenantConfig>(`/api/tenants/${tenantId}`), enabled: Boolean(tenantId) });
  const templates = useQuery({ queryKey: ["templates"], queryFn: () => apiGet<PersonaTemplate[]>("/api/persona-templates") });
  const snippet = useQuery({
    queryKey: ["snippet", tenantId],
    queryFn: () => apiGet<{ snippet: string }>(`/api/tenants/${tenantId}/widget-snippet`),
    enabled: Boolean(tenantId),
  });
  const [draft, setDraft] = useState<TenantConfig | null>(null);
  const [origins, setOrigins] = useState("");
  const [questions, setQuestions] = useState("");
  const [copied, setCopied] = useState(false);
  const [job, setJob] = useState<string | null>(null);

  useEffect(() => {
    if (tenant.data) {
      setDraft(tenant.data);
      setOrigins(tenant.data.allowed_origins.join("\n"));
      setQuestions(tenant.data.persona.suggested_questions.join("\n"));
    }
  }, [tenant.data]);

  const save = useMutation({
    mutationFn: (config: TenantConfig) => apiSend<TenantConfig>(`/api/tenants/${tenantId}`, "PUT", config),
    onSuccess: (saved) => {
      client.setQueryData(["tenant", tenantId], saved);
      void client.invalidateQueries({ queryKey: ["tenants"] });
    },
  });
  const sync = useMutation({
    mutationFn: () => apiSend<{ job_id: string }>(`/api/tenants/${tenantId}/catalog-sync`, "POST"),
    onSuccess: (r) => setJob(r.job_id),
  });
  const jobStatus = useQuery({
    queryKey: ["job", tenantId, job],
    queryFn: () => apiGet<{ status: string; products?: number }>(`/api/tenants/${tenantId}/sync-jobs/${job}`),
    enabled: Boolean(job),
    refetchInterval: (q) => (q.state.data?.status === "succeeded" || q.state.data?.status === "failed" ? false : 1500),
  });

  if (tenant.isLoading || !draft) return <Spinner />;
  if (tenant.error) return <ErrorNote error={tenant.error} />;
  const persona = draft.persona;
  const setPersona = (patch: Partial<TenantConfig["persona"]>) => setDraft({ ...draft, persona: { ...persona, ...patch } });

  const onSave = () =>
    save.mutate({
      ...draft,
      allowed_origins: origins.split(/\s+/).map((o) => o.trim().replace(/\/$/, "")).filter(Boolean),
      persona: {
        ...persona,
        suggested_questions: questions
          .split("\n")
          .map((q) => q.trim())
          .filter(Boolean)
          .slice(0, 6) as TenantConfig["persona"]["suggested_questions"],
      },
    });

  return (
    <div className="space-y-5">
      <PageHeader title="Tenant ayarları" description={`${draft.display_name} — persona, izinli alan adları, widget kodu, kontrol grubu ve katalog senkronu.`} />
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Persona">
          <div className="space-y-4 p-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="template">Persona şablonu</Label>
                <Select id="template" value={persona.template_id} onChange={(e) => setPersona({ template_id: e.target.value })}>
                  {(templates.data ?? []).map((t) => (
                    <option key={t.template_id} value={t.template_id}>
                      {t.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label htmlFor="assistant-name">Asistan adı</Label>
                <Input id="assistant-name" value={persona.assistant_name} onChange={(e) => setPersona({ assistant_name: e.target.value })} />
              </div>
            </div>
            <div>
              <Label htmlFor="greeting">Karşılama mesajı</Label>
              <Textarea id="greeting" rows={2} value={persona.greeting} onChange={(e) => setPersona({ greeting: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="tone">Ton notları</Label>
              <Textarea id="tone" rows={2} value={persona.tone_notes ?? ""} onChange={(e) => setPersona({ tone_notes: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="extra">Ek talimatlar</Label>
              <Textarea id="extra" rows={2} value={persona.extra_instructions ?? ""} onChange={(e) => setPersona({ extra_instructions: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="questions" hint="her satıra bir soru, en fazla 6">
                Önerilen sorular
              </Label>
              <Textarea id="questions" rows={4} value={questions} onChange={(e) => setQuestions(e.target.value)} />
            </div>
          </div>
        </Panel>
        <div className="space-y-5">
          <Panel title="Widget kodu">
            <div className="space-y-2 p-4">
              <pre className="overflow-x-auto rounded-lg bg-ink p-3 text-xs text-white" data-testid="widget-snippet">
                {snippet.data?.snippet ?? "…"}
              </pre>
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  await navigator.clipboard?.writeText(snippet.data?.snippet ?? "");
                  setCopied(true);
                }}
              >
                <Copy aria-hidden="true" /> {copied ? "Kopyalandı" : "Kodu kopyala"}
              </Button>
            </div>
          </Panel>
          <Panel title="Erişim ve deney">
            <div className="space-y-4 p-4">
              <div>
                <Label htmlFor="origins" hint="her satıra bir origin, ör. https://www.magazam.com">
                  İzinli alan adları
                </Label>
                <Textarea id="origins" rows={4} value={origins} onChange={(e) => setOrigins(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="holdout">Kontrol grubu (holdout): %{draft.holdout_pct}</Label>
                <input
                  id="holdout"
                  type="range"
                  min={0}
                  max={50}
                  step={1}
                  value={draft.holdout_pct}
                  onChange={(e) => setDraft({ ...draft, holdout_pct: Number(e.target.value) })}
                  className="w-full accent-[var(--color-primary)]"
                />
                <p className="text-xs text-muted">Bu orandaki ziyaretçiler widget'ı görmez; asistanın etkisi bu gruba göre ölçülür.</p>
              </div>
              <div className="flex flex-wrap gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={draft.actions.add_to_cart} onChange={(e) => setDraft({ ...draft, actions: { ...draft.actions, add_to_cart: e.target.checked } })} />
                  Sepete ekle aksiyonu
                </label>
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={draft.actions.quote_request} onChange={(e) => setDraft({ ...draft, actions: { ...draft.actions, quote_request: e.target.checked } })} />
                  Teklif talebi aksiyonu
                </label>
              </div>
            </div>
          </Panel>
          <Panel title="Katalog senkronu">
            <div className="flex flex-wrap items-center gap-3 p-4 text-sm">
              <Button variant="outline" onClick={() => sync.mutate()} disabled={sync.isPending}>
                <RefreshCw aria-hidden="true" /> Feed'i şimdi senkronla
              </Button>
              <span className="text-muted">Son senkron: {draft.catalog.last_synced_at ? new Date(draft.catalog.last_synced_at).toLocaleString("tr-TR") : "—"}</span>
              {jobStatus.data ? <Badge tone={jobStatus.data.status === "succeeded" ? "good" : jobStatus.data.status === "failed" ? "bad" : "neutral"}>{jobStatus.data.status}</Badge> : null}
            </div>
          </Panel>
        </div>
      </div>
      <div className="flex items-center justify-end gap-3">
        {save.isSuccess ? <span className="text-sm text-good">Kaydedildi.</span> : null}
        {save.error ? <ErrorNote error={save.error} /> : null}
        <Button onClick={onSave} disabled={save.isPending} data-testid="save-settings">
          <Save aria-hidden="true" /> Kaydet
        </Button>
      </div>
    </div>
  );
}
