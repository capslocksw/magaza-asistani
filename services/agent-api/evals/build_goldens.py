"""Writes the golden sets (ADK EvalSet JSON, 30 cases per tenant): python services/agent-api/evals/build_goldens.py

Each case: one user turn, the expected tool trajectory (names, in order) and a reference answer whose key
terms the response should cover. Kinds: bundle (product + complements), clarify (vague), unmet (not sold here).
"""

from __future__ import annotations

import json
from pathlib import Path

from google.adk.evaluation.eval_case import EvalCase, IntermediateData, Invocation, SessionInput
from google.adk.evaluation.eval_set import EvalSet
from google.genai import types

HERE = Path(__file__).parent
TOOLS = {
    "bundle": ["search_products", "get_complements", "propose_bundle"],
    "clarify": [],
    "unmet": ["search_products"],
}
CLARIFY_REF = "Size doğru ürünü önerebilmem için biraz daha ayrıntı verir misiniz?"
UNMET_REF = "Bu talebe uygun bir ürünü katalogda bulamadım."

GOLDENS: dict[str, list[tuple[str, str, str]]] = {
    "yapi-market": [
        (
            "Kornişim koptu, matkabım yok",
            "bundle",
            "Montaj yapıştırıcısı, silikon tabancası ve yüzey temizleyici öneririm.",
        ),
        (
            "Banyo derzleri karardı, nasıl yenilerim?",
            "bundle",
            "Derz dolgu ve derz temizleyici ile derzleri yenileyin.",
        ),
        (
            "Salonu boyayacağım, neler lazım?",
            "bundle",
            "İç cephe boyası, astar, rulo ve maskeleme bandı gerekir.",
        ),
        (
            "Damlatan musluğu nasıl tamir ederim?",
            "bundle",
            "Musluk conta seti ve teflon bant ile musluğu tamir edin.",
        ),
        (
            "Aynayı duvara matkapsız yapıştırmak istiyorum",
            "bundle",
            "Ayna yapıştırıcısı ile aynayı matkapsız sabitleyin.",
        ),
        (
            "Küvet kenarındaki silikon küflenmiş",
            "bundle",
            "Antibakteriyel banyo silikonu, silikon sökücü ve tabanca kullanın.",
        ),
        (
            "Pencere kasası ile duvar arasında boşluk var, doldurmak istiyorum",
            "bundle",
            "Poliüretan köpük ile boşluğu doldurun.",
        ),
        (
            "Demir bahçe kapımı boyamak istiyorum",
            "bundle",
            "Metal için antipas astar ve sentetik yağlı boya kullanın.",
        ),
        ("Beton duvara raf asacağım", "bundle", "Raf braketi, dübel ve beton matkap ucu gerekir."),
        ("Tavanı boyamam lazım", "bundle", "Tavan boyası ve rulo ile tavanı boyayın."),
        ("Dış cepheyi yenileyeceğim", "bundle", "Dış cephe boyası ve dış cephe astarı öneririm."),
        (
            "Mobilya montajı için akülü vidalama önerir misin?",
            "bundle",
            "Akülü vidalama matkap ve uç seti öneririm.",
        ),
        (
            "Kırılan seramik kupayı yapıştırmak istiyorum",
            "bundle",
            "Seramik onarımı için epoksi ya da hızlı yapıştırıcı kullanın.",
        ),
        ("Lavabo gideri tıkandı", "bundle", "Gider açıcı jel kullanın."),
        ("Ahşap sandalyem sallanıyor, tutkal lazım", "bundle", "Ahşap tutkalı ile birleşimleri yapıştırın."),
        ("Duş başlığım kireçlendi", "bundle", "Kireç çözücü ya da yeni duş başlığı öneririm."),
        (
            "Betona delik açacağım, hangi matkap?",
            "bundle",
            "Darbeli matkap ve beton matkap ucu seti öneririm.",
        ),
        ("Duvara tablo asmak istiyorum", "bundle", "Tablo askı seti öneririm."),
        ("Rezervuar sürekli su kaçırıyor", "bundle", "Rezervuar iç takımını değiştirin."),
        (
            "Mutfak tezgahı ile duvar arasını silikonlamak istiyorum",
            "bundle",
            "Banyo mutfak silikonu ve silikon tabancası kullanın.",
        ),
        ("Eski boyayı sökmem gerekiyor", "bundle", "Boya sökücü jel ve spatula kullanın."),
        ("Ahşap pergolayı güneşten korumak istiyorum", "bundle", "Ahşap koruyucu vernik uygulayın."),
        (
            "Boya yaparken zemini ve kenarları nasıl korurum?",
            "bundle",
            "Koruyucu örtü naylonu ve maskeleme bandı kullanın.",
        ),
        ("Kapı menteşesi gıcırdıyor", "bundle", "Çok amaçlı yağlayıcı sprey kullanın."),
        ("Mobilya monte edeceğim, vida seti lazım", "bundle", "Vida dübel seti ve tornavida öneririm."),
        ("Bisikletimi sprey boya ile boyayacağım", "bundle", "Sprey boya kullanın."),
        ("merhaba", "clarify", CLARIFY_REF),
        ("yardım", "clarify", CLARIFY_REF),
        ("Buzdolabımın kompresörü bozuldu", "unmet", UNMET_REF),
        ("Araba lastiği arıyorum", "unmet", UNMET_REF),
    ],
    "ambalaj": [
        (
            "2 kg seramik kupa göndereceğim, hangi koli?",
            "bundle",
            "Çift oluklu koli, balonlu naylon ve koli bandı öneririm.",
        ),
        ("Paletimi nasıl sarmalıyım?", "bundle", "El streç filmi ve köşe koruyucu kullanın."),
        (
            "Ayda 1000 koli gönderiyorum, teklif alabilir miyim?",
            "bundle",
            "Koli ve koli bandı için teklif talebi oluşturabilirsiniz.",
        ),
        (
            "Tekstil ürünleri için en ekonomik ambalaj?",
            "bundle",
            "Kargo poşeti ya da tek oluklu koli ekonomiktir.",
        ),
        (
            "Cam şişe göndereceğim, nasıl paketlemeliyim?",
            "bundle",
            "Çift oluklu koli ve balonlu naylon ile paketleyin.",
        ),
        ("Kitap göndermek için koli lazım", "bundle", "Tek oluklu koli öneririm."),
        (
            "Ağır koliler için koli bandı önerir misin?",
            "bundle",
            "Hotmelt koli bandı ağır kolilerde güçlü kapama sağlar.",
        ),
        ("Termal yazıcım için kargo etiketi", "bundle", "Termal kargo etiketi öneririm."),
        ("Takı gönderiyorum, küçük paket lazım", "bundle", "Balonlu zarf öneririm."),
        ("Porselen tabak takımı göndereceğim", "bundle", "Çift oluklu koli ve balonlu naylon öneririm."),
        ("Bant tabancası lazım", "bundle", "Bant tabancası öneririm."),
        (
            "Koli içindeki boşluğu nasıl doldururum?",
            "bundle",
            "Kırpık kağıt ya da köpük cips dolgu kullanın.",
        ),
        ("Palet köşeleri eziliyor", "bundle", "Karton köşe koruyucu kullanın."),
        ("Sessiz koli bandı var mı?", "bundle", "Sessiz koli bandı öneririm."),
        ("Kırılacak eşya uyarı etiketi istiyorum", "bundle", "Kırılacak eşya uyarı etiketi öneririm."),
        ("Elektronik cihaz göndereceğim", "bundle", "Balonlu naylon ve çift oluklu koli öneririm."),
        ("Bardakları koli içinde ayrı ayrı koymak istiyorum", "bundle", "Bardak ayırıcı separatör kullanın."),
        ("40 x 30 x 30 koli lazım", "bundle", "40 x 30 x 30 cm koli öneririm."),
        ("15 kg ürün göndereceğim, hangi koli dayanır?", "bundle", "Çift oluklu koli öneririm."),
        ("Plastiksiz ambalaj istiyorum", "bundle", "Kraft kağıt bant ve petek kağıt öneririm."),
        ("Kargo poşeti lazım", "bundle", "Kargo poşeti öneririm."),
        ("Siyah streç film var mı?", "bundle", "Siyah el streç filmi öneririm."),
        ("Evrak göndermek için zarf", "bundle", "Kraft zarf öneririm."),
        ("Bantsız hızlı kurulan koli var mı?", "bundle", "Kilitli dipli koli öneririm."),
        ("Mobilya sarmak için köpük", "bundle", "Köpük levha öneririm."),
        ("Palet sarma makinesi için streç film", "bundle", "Makine streç filmi öneririm."),
        ("merhaba", "clarify", CLARIFY_REF),
        ("fiyat?", "clarify", CLARIFY_REF),
        ("Forklift kiralamak istiyorum", "unmet", UNMET_REF),
        ("Dizüstü bilgisayar satıyor musunuz?", "unmet", UNMET_REF),
    ],
}


def build(tenant_id: str) -> EvalSet:
    cases = []
    for i, (question, kind, reference) in enumerate(GOLDENS[tenant_id], start=1):
        invocation = Invocation(
            invocation_id=f"{tenant_id}-{i:02d}",
            user_content=types.Content(role="user", parts=[types.Part(text=question)]),
            final_response=types.Content(role="model", parts=[types.Part(text=reference)]),
            intermediate_data=IntermediateData(
                tool_uses=[types.FunctionCall(name=name, args={}) for name in TOOLS[kind]]
            ),
        )
        cases.append(
            EvalCase(
                eval_id=f"{tenant_id}-{i:02d}-{kind}",
                conversation=[invocation],
                session_input=SessionInput(
                    app_name="magaza_asistani", user_id="eval", state={"tenant_id_hint": tenant_id}
                ),
            )
        )
    return EvalSet(eval_set_id=f"{tenant_id}-golden", name=f"{tenant_id} altın set", eval_cases=cases)


def main() -> None:
    for tenant_id in GOLDENS:
        evalset = build(tenant_id)
        path = HERE / f"{tenant_id}.evalset.json"
        path.write_text(
            json.dumps(
                evalset.model_dump(mode="json", by_alias=True, exclude_none=True),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"{path.name}: {len(evalset.eval_cases)} cases")


if __name__ == "__main__":
    main()
