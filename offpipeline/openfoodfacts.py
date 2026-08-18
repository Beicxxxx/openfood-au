from __future__ import annotations

import re
import time
from datetime import datetime, timezone

import httpx

from . import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _upgrade_image(url: str | None) -> str | None:
    if not url:
        return None
    return re.sub(r"\.(\d{2,4})\.(jpg|png)$", r".full.\2", url, flags=re.I)


def _front_image(product: dict) -> str | None:
    selected = (product.get("selected_images") or {}).get("front") or {}
    display = selected.get("display") or {}
    for lang in ("en", "fr"):
        if display.get(lang):
            return _upgrade_image(display[lang]) or display[lang]
    if display:
        url = next(iter(display.values()))
        return _upgrade_image(url) or url
    return (
        _upgrade_image(product.get("image_front_url"))
        or product.get("image_front_url")
        or product.get("image_url")
    )


def _clean_tags(tags: list | None) -> list[str]:
    out = []
    for tag in tags or []:
        text = str(tag)
        if ":" in text:
            text = text.split(":", 1)[1]
        text = text.replace("-", " ").strip()
        if text:
            out.append(text)
    return out


class OpenFoodFactsClient:
    """Read-only Open Food Facts client. One real scan should equal one API call."""

    def __init__(self) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": config.OFF_USER_AGENT},
            timeout=config.REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        self._last_request = 0.0

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        wait = config.MIN_REQUEST_INTERVAL - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def by_barcode(self, barcode: str) -> dict | None:
        code = re.sub(r"\D", "", barcode)
        if not code:
            return None
        self._throttle()
        url = config.OFF_API_V3.format(barcode=code)
        response = self._client.get(url, params={"fields": config.OFF_FIELDS})
        response.raise_for_status()
        data = response.json()
        product = data.get("product")
        if data.get("status") not in (1, "success") or not product:
            return None
        return self._normalize(product)

    def search_australia(self, query: str, page_size: int = 10) -> list[dict]:
        self._throttle()
        response = self._client.get(
            config.OFF_SEARCH,
            params={
                "search_terms": query,
                "countries_tags_en": "australia",
                "page_size": min(page_size, 20),
                "fields": config.OFF_FIELDS,
            },
        )
        response.raise_for_status()
        products = response.json().get("products") or []
        rows = []
        for product in products:
            row = self._normalize(product)
            if row:
                rows.append(row)
        return rows

    def _normalize(self, product: dict) -> dict | None:
        code = product.get("code")
        if not code:
            return None
        nutriments = product.get("nutriments") or {}
        return {
            "barcode": str(code),
            "name": product.get("product_name") or product.get("generic_name"),
            "brand": product.get("brands"),
            "size": product.get("quantity"),
            "serving_size": product.get("serving_size"),
            "image_url": _front_image(product),
            "image_license": "CC-BY-SA (Open Food Facts)",
            "ingredients": product.get("ingredients_text"),
            "allergens": _clean_tags(product.get("allergens_tags")),
            "traces": _clean_tags(product.get("traces_tags")),
            "dietary": _clean_tags(product.get("labels_tags")),
            "categories": _clean_tags(product.get("categories_tags")),
            "origin": product.get("origins"),
            "storage": product.get("conservation_conditions"),
            "countries": _clean_tags(product.get("countries_tags")),
            "nutrition": nutriments or None,
            "source": "OpenFoodFacts",
            "source_url": f"https://world.openfoodfacts.org/product/{code}",
            "fetched_at": _now(),
            "raw": {
                k: product.get(k)
                for k in (
                    "code",
                    "product_name",
                    "brands",
                    "quantity",
                    "ingredients_text",
                    "allergens_tags",
                    "traces_tags",
                    "labels_tags",
                    "nutriments",
                )
            },
        }
