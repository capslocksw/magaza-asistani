"""Builds the per-request ADK agent: persona instruction from tenant config, tenant-bound tools, callbacks."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models import BaseLlm
from google.adk.tools import FunctionTool
from google.genai import types

from magaza_core.contracts import PersonaTemplate, TenantConfig

from .callbacks import TurnCallbacks
from .tools import ToolBox

APP_NAME = "magaza_asistani"

_ACTIONS_ADD_TO_CART = (
    "Müşteri ürünleri kartlardaki 'Sepete ekle' ya da paket kartındaki 'Paketi sepete ekle' düğmesiyle sepete ekleyebilir; "
    "paket önerdiğinde bunu kısaca hatırlat."
)
_ACTIONS_QUOTE = (
    "Toplu alımlarda (ör. 100 adet ve üzeri ya da düzenli gönderim) teklif talebi öner. Müşteri firma adı, ad soyad ve "
    "e-posta verip onay verirse create_quote_request aracını çağır; vermezse sohbetteki teklif formunu doldurabileceğini söyle."
)
_ACTIONS_NO_QUOTE = "Bu mağazada teklif talebi alınmıyor; teklif sözü verme."


def render_instruction(template: PersonaTemplate, config: TenantConfig) -> str:
    actions = []
    if config.actions.add_to_cart:
        actions.append(_ACTIONS_ADD_TO_CART)
    actions.append(_ACTIONS_QUOTE if config.actions.quote_request else _ACTIONS_NO_QUOTE)
    values = {
        "store_name": config.display_name,
        "assistant_name": config.persona.assistant_name,
        "actions": "\n".join(f"- {a}" for a in actions),
        "tone_notes": config.persona.tone_notes or "",
        "extra_instructions": config.persona.extra_instructions or "",
    }
    text = template.instruction
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text.strip()


def build_agent(
    *,
    template: PersonaTemplate,
    config: TenantConfig,
    toolbox: ToolBox,
    callbacks: TurnCallbacks,
    model: str | BaseLlm,
    thinking_level: str | None = None,
) -> LlmAgent:
    instruction = render_instruction(template, config)

    def instruction_provider(_ctx: ReadonlyContext) -> str:
        return instruction

    generate_config = None
    if isinstance(model, str) and thinking_level:
        generate_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level)
        )
    return LlmAgent(
        name="magaza_asistani",
        description="Mağaza danışman satış asistanı",
        model=model,
        instruction=instruction_provider,
        tools=[FunctionTool(f) for f in toolbox.tools()],
        before_model_callback=callbacks.before_model,
        after_model_callback=callbacks.after_model,
        generate_content_config=generate_config,
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
