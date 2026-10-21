"""Deterministic stand-in for Gemini (LLM_MODE=fake): drives the real tool loop without network access.

It follows the same protocol a real model would: search -> complements -> bundle -> grounded answer,
using only data returned by the tools. Nothing in here is tenant or sector specific.
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types

from magaza_core.text import tokens

CLARIFY = (
    "Size en doğru ürünü önerebilmem için biraz daha ayrıntı verir misiniz? Ne yapmak istediğinizi, "
    "kullanılacak yüzeyi ya da ürünü ve varsa yaklaşık ölçü veya ağırlığı yazarsanız hemen yardımcı olurum."
)
NOT_FOUND = (
    "Bu talebe uygun bir ürünü katalogda bulamadım. İsterseniz ihtiyacınızı farklı kelimelerle anlatın; "
    "benzer bir çözüm arayayım."
)


def _call(name: str, args: dict[str, Any]) -> types.Part:
    return types.Part(function_call=types.FunctionCall(name=name, args=args))


def _first_sentence(text: str, limit: int = 180) -> str:
    sentence = re.split(r"(?<=[.!?])\s", text.strip())[0]
    return sentence if len(sentence) <= limit else sentence[: limit - 1] + "…"


class FakeLlm(BaseLlm):
    model: str = "fake-llm"

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        parts = self._decide(llm_request)
        prompt_chars = sum(len(str(c.model_dump(exclude_none=True))) for c in llm_request.contents)
        out_chars = sum(len(p.text or "") + len(str(p.function_call or "")) for p in parts)
        yield LlmResponse(
            content=types.Content(role="model", parts=parts),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=prompt_chars // 4
                + len(str(llm_request.config.system_instruction or "")) // 4,
                candidates_token_count=max(1, out_chars // 4),
                total_token_count=prompt_chars // 4 + out_chars // 4,
            ),
        )

    def _decide(self, req: LlmRequest) -> list[types.Part]:
        contents = req.contents
        user_idx = max(
            (i for i, c in enumerate(contents) if c.role == "user" and any(p.text for p in c.parts or [])),
            default=-1,
        )
        user_text = "".join(p.text or "" for p in contents[user_idx].parts or []) if user_idx >= 0 else ""
        responses: dict[str, list[dict[str, Any]]] = {}
        for c in contents[user_idx + 1 :]:
            for p in c.parts or []:
                if p.function_response and p.function_response.name:
                    responses.setdefault(p.function_response.name, []).append(
                        dict(p.function_response.response or {})
                    )
        tools = set(req.tools_dict)

        if not responses:
            if len(tokens(user_text)) < 2:
                return [types.Part(text=CLARIFY)]
            calls = [_call("search_products", {"query": user_text})]
            if "search_knowledge" in tools:
                calls.append(_call("search_knowledge", {"query": user_text}))
            return calls
        if "propose_bundle" in responses and "error" not in responses["propose_bundle"][-1]:
            return [types.Part(text=self._answer(responses))]
        if "get_complements" in responses and "propose_bundle" not in responses:
            data = responses["get_complements"][-1]
            if "error" in data:
                return [types.Part(text=NOT_FOUND)]
            main = data["main"]
            comps = data.get("complements", [])[:3]
            skus = [main["sku"], *[c["sku"] for c in comps]]
            reasons = [c.get("reason") for c in comps if c.get("reason")]
            return [
                _call(
                    "propose_bundle",
                    {
                        "skus": skus,
                        "quantities": [1] * len(skus),
                        "title": f"{main['title']} çözüm paketi",
                        "rationale": "; ".join(reasons) or "Ana ürün ve birlikte kullanılan tamamlayıcıları.",
                    },
                )
            ]
        if "search_products" in responses:
            products = [p for p in responses["search_products"][-1].get("products", []) if p.get("in_stock")]
            if not products:
                return [types.Part(text=NOT_FOUND)]
            # Prefer a well-documented product with complements among the top hits, like a careful expert would.
            top = products[:4]
            main = max(
                top,
                key=lambda p: (
                    p.get("has_datasheet", False) and p.get("complement_count", 0) > 0,
                    -top.index(p),
                ),
            )
            return [_call("get_complements", {"sku": main["sku"]})]
        return [types.Part(text=CLARIFY)]

    def _answer(self, responses: dict[str, list[dict[str, Any]]]) -> str:
        bundle = responses["propose_bundle"][-1]
        items = bundle.get("items", [])
        lines = ["Anladım, bunun için şu paketi öneriyorum:", ""]
        for i, item in enumerate(items):
            role = "ana ürün" if i == 0 else "tamamlayıcı"
            lines.append(f"- **{item['title']}** ({item['sku']}) — {item['price_text']}, {role}")
        passages = responses.get("search_knowledge", [{}])[-1].get("passages", [])
        main_sku = items[0]["sku"] if items else None
        passage = next((p for p in passages if p.get("sku") == main_sku), passages[0] if passages else None)
        if passage:
            lines += ["", f"Teknik föye göre: {_first_sentence(passage['text'])}"]
        lines += [
            "",
            f"Paket toplamı {bundle.get('total_text', '')}. Paketi tek tıkla sepetinize ekleyebilirsiniz.",
        ]
        return "\n".join(lines)
