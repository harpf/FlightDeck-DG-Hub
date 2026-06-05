"""Unit tests for the shared service layer (scan import + review upsert)."""
import pytest

from app.models import Product, SourceRequest
from app.scanner import ScannedProduct
from app.services import (
    RobotsForbidden,
    SourceNotApproved,
    import_products_from_source,
    upsert_review,
)


def _source(db, admin, status="approved"):
    src = SourceRequest(source_url="https://shop.example/kat/discs/", status=status, requested_by_id=admin.id)
    db.session.add(src)
    db.session.commit()
    return src


def test_import_dedups_and_returns_counts(db, admin, product):
    # `product` fixture already has name=Destroyer/Innova -> counts as a duplicate.
    src = _source(db, admin)
    scanned = [
        ScannedProduct("Destroyer", "d", "Innova", "https://shop.example/pr/destroyer/"),
        ScannedProduct("Wraith", "w", "Innova", "https://shop.example/pr/wraith/", disc_type="Distance Driver", speed=11),
        ScannedProduct("Firebird", "f", "Innova", "https://shop.example/pr/firebird/"),
    ]
    result = import_products_from_source(src, scan=lambda url: scanned, robots_allowed=lambda url: True)
    assert result == {"found": 3, "created": 2, "duplicates": 1}
    assert Product.query.count() == 3  # 1 pre-existing + 2 new
    wraith = Product.query.filter_by(name="Wraith").one()
    assert wraith.speed == 11 and wraith.disc_type == "Distance Driver"


def test_import_raises_when_not_approved(db, admin):
    src = _source(db, admin, status="open")
    with pytest.raises(SourceNotApproved):
        import_products_from_source(src, scan=lambda url: [], robots_allowed=lambda url: True)


def test_import_raises_when_robots_forbidden(db, admin):
    src = _source(db, admin)
    with pytest.raises(RobotsForbidden):
        import_products_from_source(src, scan=lambda url: [], robots_allowed=lambda url: False)


def test_upsert_review_creates_then_updates(db, admin, product):
    review, created = upsert_review(admin, product, 5, "Top")
    assert created is True and review.rating == 5
    review2, created2 = upsert_review(admin, product, 3, "Revised")
    assert created2 is False
    assert review2.id == review.id and review2.rating == 3 and review2.comment == "Revised"
