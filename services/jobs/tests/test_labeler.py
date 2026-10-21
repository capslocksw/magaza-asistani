from __future__ import annotations

from pathlib import Path

from magaza_jobs.labeler import label_events, load_taxonomies


def test_labels_with_each_tenants_own_taxonomy(demo_data_dir: Path) -> None:
    taxonomies = load_taxonomies(demo_data_dir)
    assert set(taxonomies) == {"yapi-market", "ambalaj"}
    events = [
        {
            "event_type": "user_message",
            "tenant_id": "ambalaj",
            "payload": {"text": "2 kg seramik kupa göndereceğim"},
        },
        {
            "event_type": "user_message",
            "tenant_id": "yapi-market",
            "payload": {"text": "Banyo derzleri karardı"},
        },
        {
            "event_type": "user_message",
            "tenant_id": "yapi-market",
            "payload": {"text": "x", "topic": "hirdavat"},
        },
        {"event_type": "order", "tenant_id": "ambalaj", "payload": {"total": 10}},
    ]
    out = list(label_events(events, taxonomies))
    assert [e["payload"].get("topic") for e in out] == ["kirilacak_urun", "banyo_tesisat", "hirdavat", None]
    relabeled = list(label_events(events[2:3], taxonomies, overwrite=True))
    assert relabeled[0]["payload"]["topic"] is None
