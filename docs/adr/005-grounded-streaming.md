# ADR 005 — Grounding önce, akış sonra

- Durum: kabul edildi (Gece 1)
- Bağlam: Kural: agent cevabında yalnızca araçların o oturumda döndürdüğü SKU'lar geçebilir. Modelin ham token akışını doğrudan istemciye iletmek, doğrulanmamış bir SKU'nun (ve buna bağlı fiyatın) kısa süreliğine de olsa ekrana düşmesine yol açar.
- Karar:
  - ADK `after_model_callback` her nihai model yanıtında tenant'ın `sku_pattern`'i ile SKU'ları bulur ve oturum durumundaki `grounded_skus` kümesiyle (araç sonuçlarından) karşılaştırır.
  - İlk ihlalde yanıt, iç araç `report_grounding_issue` çağrısına dönüştürülür; araç bilinmeyen SKU'ları ve izinli listeyi modele geri verir, model yanıtı yeniden yazar (**bir kez yeniden yönlendirme**). İkinci ihlalde bilinmeyen SKU içeren satırlar çıkarılır (hiçbir şey kalmazsa güvenli bir geri dönüş metni).
  - `propose_bundle` ve `create_quote_request` de yalnızca topraklanmış ve stoktaki SKU'ları kabul eder.
  - Agent turu `StreamingMode.NONE` ile tamamlanır; SSE `token` olayları yalnızca guardrail'den geçmiş nihai metinden üretilir. Ürün kartları ve paket, araçlardan dönen ürün nesnelerinden kurulur.
- Sonuç: İlk token gecikmesi model süresine eşit (Flash modelde kabul edilebilir); bunun karşılığında doğrulanmamış ürün asla görünmez. Guardrail tetiklenmeleri `agent_message.payload.guardrails` ile analitiğe yazılır (Konuşma kalitesi panosu).
- Kanıt: `services/agent-api/tests/test_grounding.py`.
