from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import config, storage
from .openfoodfacts import OpenFoodFactsClient


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cmd_init_db(args: argparse.Namespace) -> int:
    storage.init_db(args.db)
    print(f"database ready: {args.db}")
    return 0


def cmd_lookup(args: argparse.Namespace) -> int:
    conn = storage.init_db(args.db)
    client = OpenFoodFactsClient()
    started = _now()
    try:
        row = client.by_barcode(args.barcode)
    except Exception as exc:
        storage.log_ingest(conn, started, args.barcode, "error", str(exc))
        print(f"lookup failed: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()

    if not row:
        storage.log_ingest(conn, started, args.barcode, "miss", "not in Open Food Facts")
        print("not found")
        return 2

    storage.upsert_product(conn, row)
    storage.log_ingest(conn, started, row["barcode"], "ok")
    printable = {k: v for k, v in row.items() if k != "raw"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    barcodes = [
        line.strip()
        for line in Path(args.file).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    conn = storage.init_db(args.db)
    client = OpenFoodFactsClient()
    ok = miss = err = 0
    try:
        for barcode in barcodes:
            started = _now()
            try:
                row = client.by_barcode(barcode)
            except Exception as exc:
                err += 1
                storage.log_ingest(conn, started, barcode, "error", str(exc))
                print(f"{barcode}: error {exc}", file=sys.stderr)
                continue
            if not row:
                miss += 1
                storage.log_ingest(conn, started, barcode, "miss")
                print(f"{barcode}: miss")
                continue
            storage.upsert_product(conn, row)
            storage.log_ingest(conn, started, row["barcode"], "ok")
            ok += 1
            print(f"{row['barcode']}: {row.get('name') or '(unnamed)'}")
    finally:
        client.close()
    print(f"done ok={ok} miss={miss} error={err}")
    return 0 if err == 0 else 1


def cmd_search(args: argparse.Namespace) -> int:
    client = OpenFoodFactsClient()
    try:
        rows = client.search_australia(args.query, page_size=args.limit)
    finally:
        client.close()
    print(json.dumps([{k: v for k, v in r.items() if k != "raw"} for r in rows], ensure_ascii=False, indent=2))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    conn = storage.init_db(args.db)
    row = storage.get_product(conn, args.barcode)
    if not row:
        print("not in local database")
        return 2
    print(json.dumps(row, ensure_ascii=False, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FIT5120 Open Food Facts product pipeline (no supermarket crawl)."
    )
    parser.add_argument("--db", default=str(config.DEFAULT_DB))
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-db", help="create SQLite schema")
    p_init.set_defaults(func=cmd_init_db)

    p_lookup = sub.add_parser("lookup", help="fetch one barcode from Open Food Facts")
    p_lookup.add_argument("barcode")
    p_lookup.set_defaults(func=cmd_lookup)

    p_ingest = sub.add_parser("ingest", help="fetch many barcodes from a text file")
    p_ingest.add_argument("file")
    p_ingest.set_defaults(func=cmd_ingest)

    p_search = sub.add_parser("search", help="search Australian OFF products by name")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=5)
    p_search.set_defaults(func=cmd_search)

    p_show = sub.add_parser("show", help="print a product already stored locally")
    p_show.add_argument("barcode")
    p_show.set_defaults(func=cmd_show)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    raise SystemExit(args.func(args))
