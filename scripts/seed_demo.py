"""Seed the database with demo data (admin user, sample discs, reviews).

Idempotent: does nothing if products already exist. Intended for local demos
and screenshots, not production.

Usage (from repo root, with the venv active):
    DATABASE_URL=sqlite:///dev.db BOOTSTRAP_ADMIN_PASSWORD=admin12345 \
        python scripts/seed_demo.py
"""
import os
import sys

# Allow running directly as `python scripts/seed_demo.py` from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import ApiToken, Product, ProductReview, User

DISCS = [
    # name, manufacturer, type, speed, glide, turn, fade, plastic, stability, weight, desc
    ("Destroyer", "Innova", "Distance Driver", 12, 5, -1, 3, "Star", "overstable", "165-175 g",
     "Zuverlässiger Overstable-Distance-Driver für Power-Würfe und Wind."),
    ("Wraith", "Innova", "Distance Driver", 11, 5, -1, 3, "Champion", "stable", "165-175 g",
     "Schneller, leicht stabiler Driver mit grosser Reichweite."),
    ("Buzzz", "Discraft", "Midrange", 5, 4, -1, 1, "ESP", "stable", "170-180 g",
     "Der Midrange-Klassiker – konstant und vielseitig."),
    ("Luna", "Discraft", "Putter", 3, 3, 0, 3, "Jawbreaker", "overstable", "170-174 g",
     "Overstable Putter für kontrollierte Approaches und Wind."),
    ("Zone", "Discraft", "Putt & Approach", 4, 3, 0, 3, "Z", "overstable", "170-174 g",
     "Extrem overstable – perfekt für präzise Approaches."),
    ("Teebird", "Innova", "Fairway Driver", 7, 5, 0, 2, "Champion", "stable", "168-175 g",
     "Akkurater Fairway-Driver mit gutmütigem Flug."),
    ("Hex", "Axiom", "Midrange", 5, 5, -1, 1, "Neutron", "neutral", "170-180 g",
     "Neutraler Midrange mit langem, geradem Flug."),
    ("Aviar", "Innova", "Putter", 2, 3, 0, 1, "DX", "stable", "170-175 g",
     "Der meistgespielte Putter der Welt."),
]

REVIEWS = [
    ("Destroyer", 5, "Mein Go-to-Driver bei Wind."),
    ("Buzzz", 5, "Einfach perfekt, fliegt immer gleich."),
    ("Zone", 4, "Unglaublich zuverlässig für Approaches."),
    ("Aviar", 4, "Klassiker, liegt gut in der Hand."),
]

app = create_app()
with app.app_context():
    db.create_all()

    if Product.query.first() is not None:
        print("Products already exist — skipping seed.")
        raise SystemExit(0)

    admin = User.query.filter_by(username="admin").first()
    if admin is None:
        admin = User(username="admin", email="admin@flightdeck.local", is_admin=True, privacy_consent=True)
        admin.set_password(os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "admin12345"))
        db.session.add(admin)

    demo = User.query.filter_by(username="discgolfer").first()
    if demo is None:
        demo = User(username="discgolfer", email="demo@flightdeck.local", privacy_consent=True)
        demo.set_password("demo123456")
        db.session.add(demo)
    db.session.flush()

    by_name = {}
    for name, mfr, dtype, sp, gl, tu, fa, plastic, stab, weight, desc in DISCS:
        p = Product(name=name, manufacturer=mfr, category="Disc", disc_type=dtype,
                    speed=sp, glide=gl, turn=tu, fade=fa, plastic_type=plastic,
                    stability=stab, weight_range_g=weight, diameter_cm=21.1, description=desc)
        db.session.add(p)
        by_name[name] = p
    db.session.flush()

    for pname, rating, comment in REVIEWS:
        db.session.add(ProductReview(rating=rating, comment=comment, user_id=demo.id, product_id=by_name[pname].id))

    db.session.commit()
    print(f"Seeded {len(DISCS)} discs, {len(REVIEWS)} reviews, admin + demo user.")
