"""CLI: ``python -m magaza_jobs.demo_data --out data/demo [--no-pdf]``."""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from .generator import write_all


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic demo data for the demo tenants.")
    parser.add_argument("--out", default="data/demo", type=Path)
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF rendering of the data sheets")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    started = time.perf_counter()
    summary = write_all(args.out, pdf=not args.no_pdf, data_dir=args.out.as_posix())
    for tenant_id, counts in summary.items():
        print(
            f"{tenant_id}: {counts['products']} products, {counts['categories']} categories, "
            f"{counts['docs']} data sheets, {counts['pdfs']} PDFs"
        )
    print(f"demo data written to {args.out} in {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    main()
