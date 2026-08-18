from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    barcode TEXT PRIMARY KEY,
    name TEXT,
    brand TEXT,
    size TEXT,
    serving_size TEXT,
    image_url TEXT,
    image_license TEXT,
    ingredients TEXT,
    allergens TEXT,
    traces TEXT,
    dietary TEXT,
    categories TEXT,
    origin TEXT,
    storage TEXT,
    countries TEXT,
    nutrition_json TEXT,
    source TEXT NOT NULL DEFAULT 'OpenFoodFacts',
    source_url TEXT,
    fetched_at TEXT,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS ingest_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT,
    barcode TEXT,
    status TEXT,
    message TEXT
);
"""


def init_db(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def _join(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return ",".join(str(x) for x in value if x)
    return str(value)


def _json(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def upsert_product(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        """
        INSERT INTO products (
            barcode, name, brand, size, serving_size, image_url, image_license,
            ingredients, allergens, traces, dietary, categories, origin,
            storage, countries, nutrition_json, source, source_url,
            fetched_at, raw_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(barcode) DO UPDATE SET
            name=excluded.name,
            brand=excluded.brand,
            size=excluded.size,
            serving_size=excluded.serving_size,
            image_url=excluded.image_url,
            image_license=excluded.image_license,
            ingredients=excluded.ingredients,
            allergens=excluded.allergens,
            traces=excluded.traces,
            dietary=excluded.dietary,
            categories=excluded.categories,
            origin=excluded.origin,
            storage=excluded.storage,
            countries=excluded.countries,
            nutrition_json=excluded.nutrition_json,
            source=excluded.source,
            source_url=excluded.source_url,
            fetched_at=excluded.fetched_at,
            raw_json=excluded.raw_json
        """,
        (
            row["barcode"],
            row.get("name"),
            row.get("brand"),
            row.get("size"),
            row.get("serving_size"),
            row.get("image_url"),
            row.get("image_license"),
            row.get("ingredients"),
            _join(row.get("allergens")),
            _join(row.get("traces")),
            _join(row.get("dietary")),
            _join(row.get("categories")),
            row.get("origin"),
            row.get("storage"),
            _join(row.get("countries")),
            _json(row.get("nutrition")),
            row.get("source", "OpenFoodFacts"),
            row.get("source_url"),
            row.get("fetched_at"),
            _json(row.get("raw")),
        ),
    )
    conn.commit()


def log_ingest(
    conn: sqlite3.Connection,
    started_at: str,
    barcode: str,
    status: str,
    message: str = "",
) -> None:
    conn.execute(
        "INSERT INTO ingest_log (started_at, barcode, status, message) VALUES (?,?,?,?)",
        (started_at, barcode, status, message),
    )
    conn.commit()


def get_product(conn: sqlite3.Connection, barcode: str) -> dict | None:
    cur = conn.execute("SELECT * FROM products WHERE barcode=?", (barcode,))
    row = cur.fetchone()
    return dict(row) if row else None


def list_products(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    cur = conn.execute(
        "SELECT * FROM products ORDER BY fetched_at DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in cur.fetchall()]
