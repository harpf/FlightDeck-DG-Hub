from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.forms import ApiTokenForm, LoginForm, ProductForm, ProductReviewForm, RegisterForm, SourceRequestForm, SourceRequestStatusForm
from app.models import ApiToken, Product, ProductReview, SourceRequest, User
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

        token = ApiToken.query.get(token_id)
        if token is None or not token.check_secret(secret):
            return jsonify({"error": "Invalid API token"}), 401

        token.last_used_at = datetime.utcnow()
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
    product = Product.query.get_or_404(product_id)
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
    return render_template("admin/dashboard.html", source_requests=source_requests, tokens=tokens, token_form=ApiTokenForm(), status_form=SourceRequestStatusForm())


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
    token = ApiToken.query.get_or_404(token_id)
    token.is_active = False
    db.session.commit()
    flash("Token deaktiviert.", "info")
    return redirect(url_for('admin.dashboard'))




@admin_bp.route('/sources/<int:request_id>/scan', methods=['POST'])
@admin_required
def scan_source(request_id: int):
    source_request = SourceRequest.query.get_or_404(request_id)
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
    source_request = SourceRequest.query.get_or_404(request_id)
    form = SourceRequestStatusForm()
    if form.validate_on_submit():
        source_request.status = form.status.data
        db.session.commit()
        flash("Anfrage aktualisiert.", "success")
    return redirect(url_for("admin.dashboard"))


@api_bp.route('/v1/full')
@api_token_required
def api_full_dump():
    products = Product.query.order_by(Product.id).all()
    return jsonify({"products": [{"id": p.id, "name": p.name, "manufacturer": p.manufacturer, "category": p.category, "description": p.description, "product_url": p.product_url, "disc_type": p.disc_type, "speed": p.speed, "glide": p.glide, "turn": p.turn, "fade": p.fade, "diameter_cm": p.diameter_cm, "weight_range_g": p.weight_range_g, "plastic_type": p.plastic_type, "stability": p.stability, "created_at": p.created_at.isoformat(), "reviews": [{"id": r.id, "rating": r.rating, "comment": r.comment, "created_at": r.created_at.isoformat(), "username": r.user.username} for r in p.reviews]} for p in products], "source_requests": [{"id": s.id, "source_url": s.source_url, "note": s.note, "status": s.status, "requested_by": s.requested_by.username, "created_at": s.created_at.isoformat()} for s in SourceRequest.query.order_by(SourceRequest.id).all()]})
