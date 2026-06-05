from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.forms import ApiTokenForm, LoginForm, ProductForm, ProductReviewForm, RegisterForm, SourceRequestForm, SourceRequestStatusForm
from app.models import ApiToken, Product, ProductReview, SourceRequest, User
from app.openapi import build_openapi_spec
from app.scanner import is_scraping_allowed, scan_products_from_url

main_bp = Blueprint("main", __name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
products_bp = Blueprint("products", __name__, url_prefix="/products")
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
api_bp = Blueprint("api", __name__, url_prefix="/api")


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped


def _parse_api_token(raw_token: str) -> tuple[int, str] | tuple[None, None]:
    try:
        token_id_str, secret = raw_token.split(".", 1)
        return int(token_id_str), secret
    except (ValueError, AttributeError):
        return None, None


def api_token_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        raw_token = request.headers.get("X-API-Token", "")
        token_id, secret = _parse_api_token(raw_token)
        if token_id is None or not secret:
            return jsonify({"error": "Invalid API token format"}), 401

        token = db.session.get(ApiToken, token_id)
        if token is None or not token.check_secret(secret):
            return jsonify({"error": "Invalid API token"}), 401

        token.last_used_at = datetime.now(timezone.utc)
        db.session.commit()
        g.api_token = token
        return view_func(*args, **kwargs)

    return wrapped


@main_bp.route("/")
def home():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    query = Product.query
    if q:
        query = query.filter((Product.name.ilike(f"%{q}%")) | (Product.manufacturer.ilike(f"%{q}%")))
    if category:
        query = query.filter_by(category=category)

    products = query.order_by(Product.created_at.desc()).all()
    categories = [c[0] for c in db.session.query(Product.category).distinct().order_by(Product.category).all()]
    return render_template("products/public_list.html", products=products, q=q, category=category, categories=categories)


@main_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first():
            flash("Benutzername oder E-Mail existiert bereits.", "danger")
            return render_template("auth/register.html", form=form)
        user = User(username=form.username.data, email=form.email.data, privacy_consent=form.privacy_consent.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Account erstellt. Bitte anmelden.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("main.home"))
        flash("Ungültige Zugangsdaten.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.home"))


@products_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_product():
    form = ProductForm()
    if form.validate_on_submit():
        db.session.add(Product(name=form.name.data, manufacturer=form.manufacturer.data, category=form.category.data, description=form.description.data, product_url=form.product_url.data, disc_type=form.disc_type.data, speed=form.speed.data, glide=form.glide.data, turn=form.turn.data, fade=form.fade.data, diameter_cm=form.diameter_cm.data, weight_range_g=form.weight_range_g.data, plastic_type=form.plastic_type.data, stability=form.stability.data))
        db.session.commit()
        flash("Produkt wurde angelegt.", "success")
        return redirect(url_for("main.home"))
    return render_template("products/form.html", form=form, title="Produkt anlegen")


@products_bp.route("/<int:product_id>", methods=["GET", "POST"])
def product_detail(product_id):
    product = db.get_or_404(Product, product_id)
    form = ProductReviewForm()
    if current_user.is_authenticated and form.validate_on_submit():
        review = ProductReview.query.filter_by(user_id=current_user.id, product_id=product.id).first()
        if review is None:
            review = ProductReview(user_id=current_user.id, product_id=product.id)
            db.session.add(review)
        review.rating = form.rating.data
        review.comment = form.comment.data
        db.session.commit()
        flash("Bewertung gespeichert.", "success")
        return redirect(url_for("products.product_detail", product_id=product.id))
    reviews = ProductReview.query.filter_by(product_id=product.id).order_by(ProductReview.created_at.desc()).all()
    return render_template("products/detail.html", product=product, reviews=reviews, form=form)


@products_bp.route("/sources/request", methods=["GET", "POST"])
@login_required
def request_source():
    form = SourceRequestForm()
    if form.validate_on_submit():
        db.session.add(SourceRequest(source_url=form.source_url.data, note=form.note.data, requested_by_id=current_user.id))
        db.session.commit()
        flash("Source-Anfrage gesendet.", "success")
        return redirect(url_for("main.home"))
    return render_template("products/source_request_form.html", form=form)


@admin_bp.route("/")
@admin_required
def dashboard():
    source_requests = SourceRequest.query.order_by(SourceRequest.created_at.desc()).all()
    tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/dashboard.html", source_requests=source_requests, tokens=tokens, users=users, token_form=ApiTokenForm(), status_form=SourceRequestStatusForm())


@admin_bp.route('/tokens/create', methods=['POST'])
@admin_required
def create_api_token():
    form = ApiTokenForm()
    if form.validate_on_submit():
        token = ApiToken(name=form.name.data, created_by_id=current_user.id, token_hash="placeholder")
        db.session.add(token)
        db.session.flush()
        secret = ApiToken.generate_secret()
        token.set_secret(secret)
        db.session.commit()
        flash(f"Token erstellt (nur jetzt sichtbar): {ApiToken.build_plaintext_token(token.id, secret)}", "warning")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/tokens/<int:token_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_api_token(token_id: int):
    token = db.get_or_404(ApiToken, token_id)
    token.is_active = False
    db.session.commit()
    flash("Token deaktiviert.", "info")
    return redirect(url_for('admin.dashboard'))




@admin_bp.route('/sources/<int:request_id>/scan', methods=['POST'])
@admin_required
def scan_source(request_id: int):
    source_request = db.get_or_404(SourceRequest, request_id)
    if source_request.status != "approved":
        flash("Nur freigegebene Sources können gescannt werden.", "warning")
        return redirect(url_for('admin.dashboard'))
    if not is_scraping_allowed(source_request.source_url):
        flash("robots.txt verbietet das Scannen dieser Quelle.", "danger")
        return redirect(url_for('admin.dashboard'))
    scanned = scan_products_from_url(source_request.source_url)
    created = 0
    for item in scanned:
        exists = Product.query.filter_by(name=item.name, manufacturer=item.manufacturer).first()
        if exists:
            continue
        db.session.add(Product(name=item.name, manufacturer=item.manufacturer, category='Disc', description=item.description, product_url=item.product_url))
        created += 1
    db.session.commit()
    flash(f"Scan abgeschlossen. Neue Einträge: {created}", "success")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/sources/<int:request_id>", methods=["POST"])
@admin_required
def update_source_status(request_id):
    source_request = db.get_or_404(SourceRequest, request_id)
    form = SourceRequestStatusForm()
    if form.validate_on_submit():
        source_request.status = form.status.data
        db.session.commit()
        flash("Anfrage aktualisiert.", "success")
    return redirect(url_for("admin.dashboard"))


# --- API serializers -------------------------------------------------------
# Kept as small, single-responsibility helpers so the JSON shape is defined in
# exactly one place and reused by every endpoint (DRY). This avoids the drift
# you get when each route hand-builds its own dict.

def _serialize_review(review: ProductReview) -> dict:
    return {
        "id": review.id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at.isoformat(),
        "username": review.user.username,
    }


def _serialize_product(product: Product, include_reviews: bool = True) -> dict:
    data = {
        "id": product.id,
        "name": product.name,
        "manufacturer": product.manufacturer,
        "category": product.category,
        "description": product.description,
        "product_url": product.product_url,
        "disc_type": product.disc_type,
        "flight_numbers": {
            "speed": product.speed,
            "glide": product.glide,
            "turn": product.turn,
            "fade": product.fade,
        },
        "diameter_cm": product.diameter_cm,
        "weight_range_g": product.weight_range_g,
        "plastic_type": product.plastic_type,
        "stability": product.stability,
        "created_at": product.created_at.isoformat(),
    }
    if include_reviews:
        data["reviews"] = [_serialize_review(r) for r in product.reviews]
    return data


def _serialize_source_request(source_request: SourceRequest) -> dict:
    return {
        "id": source_request.id,
        "source_url": source_request.source_url,
        "note": source_request.note,
        "status": source_request.status,
        "requested_by": source_request.requested_by.username,
        "created_at": source_request.created_at.isoformat(),
    }


# --- API endpoints ---------------------------------------------------------

@api_bp.route("/openapi.json")
def openapi_spec():
    """OpenAPI 3.0 specification powering the embedded Swagger UI."""
    return jsonify(build_openapi_spec())


@api_bp.route("/docs")
def api_docs():
    """Interactive Swagger UI for the REST API."""
    return render_template("api_docs.html")


@api_bp.route("/v1/health")
def api_health():
    """Public, unauthenticated liveness probe (used by monitoring/healthchecks)."""
    return jsonify({"status": "ok", "service": "flightdeck-dg-hub"})


@api_bp.route("/v1/products")
@api_token_required
def api_products():
    """List discs/products. Supports the same ?q= and ?category= filters as the web UI."""
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    query = Product.query
    if q:
        query = query.filter((Product.name.ilike(f"%{q}%")) | (Product.manufacturer.ilike(f"%{q}%")))
    if category:
        query = query.filter_by(category=category)
    products = query.order_by(Product.created_at.desc()).all()
    return jsonify({"count": len(products), "products": [_serialize_product(p, include_reviews=False) for p in products]})


@api_bp.route("/v1/products/<int:product_id>")
@api_token_required
def api_product_detail(product_id: int):
    """Single product including its reviews. Returns 404 as JSON if not found."""
    product = db.session.get(Product, product_id)
    if product is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(_serialize_product(product, include_reviews=True))


@api_bp.route("/v1/full")
@api_token_required
def api_full_dump():
    """Full read-only export of products (with reviews) and source requests."""
    products = Product.query.order_by(Product.id).all()
    source_requests = SourceRequest.query.order_by(SourceRequest.id).all()
    return jsonify({
        "products": [_serialize_product(p, include_reviews=True) for p in products],
        "source_requests": [_serialize_source_request(s) for s in source_requests],
    })
