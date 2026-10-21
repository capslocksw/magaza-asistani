# ADR 004 — Tenant izolasyonu

- Durum: kabul edildi (Gece 1)
- Bağlam: Tek agent servisi tüm tenant'lara hizmet ediyor; bir tenant'ın ürünleri, oturumları veya teklifleri başka tenant'ın sohbetine asla sızmamalı. `tenant_id` model çıktısından ya da istemci girdisinden alınamaz.
- Karar:
  1. **Bağlam yalnızca sunucuda kurulur.** Widget yalnızca public key gönderir (`/v1/t/{pk}/...`). `TenantRegistry.resolve_public_key` → `TenantConfig` → `TenantContext`. İstek gövdesindeki her model `extra="forbid"`; `ChatRequest`'te `tenant_id` alanı yoktur (gönderilirse 422).
  2. **Origin izin listesi.** Middleware, tarayıcının gönderdiği `Origin` başlığını tenant'ın `allowed_origins` listesiyle karşılaştırır; uymazsa 403 (`origin_not_allowed`), preflight dahil. CORS yanıt başlıkları yalnızca izinli origin'e verilir.
  3. **Repo katmanı.** Firestore'a yalnızca `magaza_core.repo` üzerinden erişilir. Tenant verisi repoları (`ProductRepo`, `KnowledgeRepo`, `SessionRepo`, `QuoteRepo`, `UsageRepo`, ...) `TenantContext` ile kurulur ve yolları `tenants/{tid}/...` altında üretir; hiçbir metot tenant kimliği parametresi almaz.
  4. **Araçlar kapanış (closure).** Agent ve araçları her istekte, doğrulanmış bağlamla kurulmuş repolar üzerine yeniden oluşturulur; model hangi argümanı üretirse üretsin başka tenant'ın yoluna erişemez.
  5. **Oturumlar tenant altında.** `FirestoreSessionService` tek tenant'a bağlıdır; başka tenant'ın oturum kimliği "yok" sayılır ve yeni oturum açılır. Oturum ayrıca ziyaretçi hash'ine (user_id) bağlıdır.
  6. **Bilinçli istisnalar:** public key çözümleme (bağlamı *kuran* işlem) kök `tenants` koleksiyonunu sorgular; persona şablonları tenant'lar arası ortak, tenant verisi içermeyen kök `persona_templates` koleksiyonundadır. Admin API'de tenant, kullanıcının yetkili olduğu tenant listesiyle doğrulanır.
- Kanıt: `services/agent-api/tests/test_tenant_isolation.py` (araçlar, oturumlar, HTTP; çapraz-tenant SKU dönmez), `test_api.py` (CORS, istemci olaylarında tenant'ın anahtardan gelmesi).
