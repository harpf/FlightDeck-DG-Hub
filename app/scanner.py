from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser


SCANNER_USER_AGENT = "FlightDeckScanner/1.0"


@dataclass
class ScannedProduct:
    name: str
    description: str | None
    manufacturer: str | None
    product_url: str


def build_robots_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    return urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))


def is_scraping_allowed(source_url: str, user_agent: str = SCANNER_USER_AGENT) -> bool:
    parser = RobotFileParser()
    parser.set_url(build_robots_url(source_url))
    parser.read()
    return parser.can_fetch(user_agent, source_url)


def scan_products_from_url(source_url: str) -> list[ScannedProduct]:
    req = Request(source_url, headers={"User-Agent": SCANNER_USER_AGENT})
    with urlopen(req, timeout=10) as response:  # noqa: S310
        html = response.read().decode("utf-8", errors="ignore")

    matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, flags=re.DOTALL | re.IGNORECASE)
    scanned: list[ScannedProduct] = []
    for raw in matches:
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            if isinstance(entry, dict) and entry.get("@type") == "Product" and entry.get("name"):
                scanned.append(
                    ScannedProduct(
                        name=str(entry.get("name")),
                        description=entry.get("description"),
                        manufacturer=(entry.get("brand") or {}).get("name") if isinstance(entry.get("brand"), dict) else None,
                        product_url=entry.get("url") or source_url,
                    )
                )
    return scanned
