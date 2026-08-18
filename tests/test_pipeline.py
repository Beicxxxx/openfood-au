import json
from pathlib import Path

from offpipeline.openfoodfacts import OpenFoodFactsClient, _front_image, _upgrade_image
from offpipeline.storage import init_db, upsert_product, get_product


def test_front_image_prefers_selected_display():
    product = {
        "selected_images": {
            "front": {"display": {"en": "https://images.openfoodfacts.org/x/front_en.12.400.jpg"}}
        }
    }
    assert _front_image(product).endswith("front_en.12.full.jpg")


def test_upgrade_image_noop_without_url():
    assert _upgrade_image(None) is None


def test_sqlite_roundtrip(tmp_path: Path):
    conn = init_db(tmp_path / "t.db")
    upsert_product(
        conn,
        {
            "barcode": "9310021039080",
            "name": "Lemon Ice Tea",
            "brand": "Lipton",
            "allergens": ["milk"],
            "nutrition": {"sugars_100g": 4.2},
            "source": "OpenFoodFacts",
            "fetched_at": "2026-08-18T00:00:00+00:00",
        },
    )
    row = get_product(conn, "9310021039080")
    assert row["name"] == "Lemon Ice Tea"
    assert row["allergens"] == "milk"
    assert json.loads(row["nutrition_json"])["sugars_100g"] == 4.2


def test_client_requires_user_agent():
    client = OpenFoodFactsClient()
    assert "FIT5120" in client._client.headers["User-Agent"]
    client.close()
