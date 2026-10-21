"""conversation-labeler: (re)labels user messages with each tenant's topic taxonomy (Cloud Run Job in production).

    python -m magaza_jobs.labeler --input .local/analytics/live-events.jsonl --output labeled.jsonl [--tenants data/demo]

The agent already labels messages inline when they arrive; this job back-fills/relabels history after a tenant
changes its taxonomy. Locally it works on the analytics JSONL; in production the same function runs over the
BigQuery table and writes a labels table. The taxonomy is tenant data, so no sector logic lives here.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from magaza_core.contracts import TenantConfig, TopicDefinition
from magaza_core.text import label_topic


def load_taxonomies(tenants_dir: Path) -> dict[str, list[TopicDefinition]]:
    out: dict[str, list[TopicDefinition]] = {}
    for path in sorted(tenants_dir.glob("*/tenant.json")):
        config = TenantConfig.model_validate_json(path.read_text(encoding="utf-8"))
        out[config.tenant_id] = config.topic_taxonomy
    return out


def label_events(
    events: Iterable[dict[str, Any]], taxonomies: dict[str, list[TopicDefinition]], *, overwrite: bool = False
) -> Iterator[dict[str, Any]]:
    """Yields events; user messages get payload.topic from their own tenant's taxonomy."""
    for event in events:
        payload = dict(event.get("payload") or {})
        taxonomy = taxonomies.get(str(event.get("tenant_id")))
        if (
            event.get("event_type") == "user_message"
            and taxonomy is not None
            and (overwrite or not payload.get("topic"))
        ):
            payload["topic"] = label_topic(str(payload.get("text", "")), taxonomy)
            event = {**event, "payload": payload}
        yield event


def main() -> None:
    parser = argparse.ArgumentParser(description="Label user messages with the tenant topic taxonomy")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tenants", default="data/demo", type=Path)
    parser.add_argument("--overwrite", action="store_true", help="relabel messages that already have a topic")
    args = parser.parse_args()
    taxonomies = load_taxonomies(args.tenants)
    labeled = 0
    with args.input.open(encoding="utf-8") as src, args.output.open("w", encoding="utf-8") as dst:
        events = (json.loads(line) for line in src if line.strip())
        for event in label_events(events, taxonomies, overwrite=args.overwrite):
            labeled += event.get("event_type") == "user_message" and bool(event["payload"].get("topic"))
            dst.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(json.dumps({"labeled_user_messages": labeled, "tenants": sorted(taxonomies)}))


if __name__ == "__main__":
    main()
