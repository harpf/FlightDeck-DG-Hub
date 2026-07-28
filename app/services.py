"""Shared application services used by both the web UI and the REST API.

Keeping the scan-import and review-upsert logic here (rather than inline in a
route) means the browser flow and the API flow share exactly one implementation,
so their behaviour can't drift.
"""
from __future__ import annotations

from app.extensions import db
from app.models import Product, ProductReview, SourceRequest, User
from app.scanner import is_scraping_allowed, scan_products_from_url


class SourceNotApproved(Exception):
    """Raised when a scan is attempted on a source that isn't approved."""


class RobotsForbidden(Exception):
    """Raised when robots.txt disallows scanning the source URL."""


def import_products_from_source(source_request: SourceRequest, *, scan=None, robots_allowed=None) -> dict:
    """Scan an approved source and insert new products (dedup by name+manufacturer).

    ``scan`` / ``robots_allowed`` are looked up at call time (and overridable) so
    callers and tests can inject their own. Returns ``{found, created, duplicates}``.
    """
    scan = scan or scan_products_from_url
    robots_allowed = robots_allowed or is_scraping_allowed

    if source_request.status != "approved":
        raise SourceNotApproved(source_request.source_url)
    if not robots_allowed(source_request.source_url):
        raise RobotsForbidden(source_request.source_url)

    scanned = scan(source_request.source_url)
    found = len(scanned)
    created = 0
    duplicates = 0
    for item in scanned:
        if Product.query.filter_by(name=item.name, manufacturer=item.manufacturer).first():
            duplicates += 1
            continue
        db.session.add(Product(
            name=item.name,
            manufacturer=item.manufacturer,
            category="Disc",
            description=item.description,
            product_url=item.product_url,
            image_url=item.image_url,
            disc_type=item.disc_type,
            speed=item.speed,
            glide=item.glide,
            turn=item.turn,
            fade=item.fade,
            price=item.price,
            weight_range_g=item.weight_range_g,
            stability=item.stability,
        ))
        created += 1
    db.session.commit()
    return {"found": found, "created": created, "duplicates": duplicates}


def upsert_review(user: User, product: Product, rating: int, comment: str | None) -> tuple[ProductReview, bool]:
    """Create or update the given user's review for a product. Returns (review, created)."""
    review = ProductReview.query.filter_by(user_id=user.id, product_id=product.id).first()
    created = review is None
    if review is None:
        review = ProductReview(user_id=user.id, product_id=product.id)
        db.session.add(review)
    review.rating = rating
    review.comment = comment
    db.session.commit()
    return review, created
