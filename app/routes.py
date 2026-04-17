from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.forms import EventForm, LoginForm, MemberForm, RoleForm
from app.models import Event, Member, MemberRole, User

main_bp = Blueprint("main", __name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
members_bp = Blueprint("members", __name__, url_prefix="/members")
roles_bp = Blueprint("roles", __name__, url_prefix="/roles")
events_bp = Blueprint("events", __name__, url_prefix="/events")
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


@main_bp.route("/")
@login_required
def dashboard():
    total_members = Member.query.count()
    active_members = Member.query.filter_by(status="active").count()
    upcoming_events = Event.query.filter(Event.event_date >= datetime.utcnow()).order_by(Event.event_date).limit(5).all()
    return render_template(
        "dashboard.html",
        total_members=total_members,
        active_members=active_members,
        upcoming_events=upcoming_events,
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("main.dashboard"))
        flash("Ungültige Zugangsdaten.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@members_bp.route("/")
@login_required
def list_members():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")

    query = Member.query
    if q:
        query = query.filter(
            (Member.first_name.ilike(f"%{q}%"))
            | (Member.last_name.ilike(f"%{q}%"))
            | (Member.email.ilike(f"%{q}%"))
        )
    if status in {"active", "inactive"}:
        query = query.filter(Member.status == status)

    members = query.order_by(Member.last_name, Member.first_name).all()
    return render_template("members/list.html", members=members, q=q, status=status)


@members_bp.route("/create", methods=["GET", "POST"])
@admin_required
def create_member():
    form = MemberForm()
    form.role_id.choices = [(0, "-- Keine Rolle --")] + [(role.id, role.name) for role in MemberRole.query.order_by(MemberRole.name)]

    if form.validate_on_submit():
        member = Member(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            street=form.street.data,
            zip_code=form.zip_code.data,
            city=form.city.data,
            join_date=form.join_date.data,
            status=form.status.data,
            notes=form.notes.data,
            role_id=form.role_id.data or None,
        )
        db.session.add(member)
        db.session.commit()
        flash("Mitglied wurde erstellt.", "success")
        return redirect(url_for("members.list_members"))

    return render_template("members/form.html", form=form, title="Mitglied erstellen")


@members_bp.route("/<int:member_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_member(member_id):
    member = Member.query.get_or_404(member_id)
    form = MemberForm(obj=member)
    form.role_id.choices = [(0, "-- Keine Rolle --")] + [(role.id, role.name) for role in MemberRole.query.order_by(MemberRole.name)]
    if member.role_id is None:
        form.role_id.data = 0

    if form.validate_on_submit():
        form.populate_obj(member)
        member.role_id = form.role_id.data or None
        db.session.commit()
        flash("Mitglied wurde aktualisiert.", "success")
        return redirect(url_for("members.list_members"))

    return render_template("members/form.html", form=form, title="Mitglied bearbeiten")


@members_bp.route("/<int:member_id>/deactivate", methods=["POST"])
@admin_required
def deactivate_member(member_id):
    member = Member.query.get_or_404(member_id)
    member.status = "inactive"
    db.session.commit()
    flash("Mitglied wurde deaktiviert.", "info")
    return redirect(url_for("members.list_members"))


@roles_bp.route("/")
@login_required
def list_roles():
    roles = MemberRole.query.order_by(MemberRole.name).all()
    return render_template("roles/list.html", roles=roles)


@roles_bp.route("/create", methods=["GET", "POST"])
@admin_required
def create_role():
    form = RoleForm()
    if form.validate_on_submit():
        role = MemberRole(name=form.name.data, description=form.description.data)
        db.session.add(role)
        db.session.commit()
        flash("Rolle wurde erstellt.", "success")
        return redirect(url_for("roles.list_roles"))

    return render_template("roles/form.html", form=form, title="Rolle erstellen")


@roles_bp.route("/<int:role_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_role(role_id):
    role = MemberRole.query.get_or_404(role_id)
    form = RoleForm(obj=role)
    if form.validate_on_submit():
        form.populate_obj(role)
        db.session.commit()
        flash("Rolle wurde aktualisiert.", "success")
        return redirect(url_for("roles.list_roles"))

    return render_template("roles/form.html", form=form, title="Rolle bearbeiten")


@events_bp.route("/")
@login_required
def list_events():
    events = Event.query.order_by(Event.event_date.desc()).all()
    return render_template("events/list.html", events=events)


@events_bp.route("/create", methods=["GET", "POST"])
@admin_required
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            title=form.title.data,
            description=form.description.data,
            location=form.location.data,
            event_date=form.event_date.data,
        )
        db.session.add(event)
        db.session.commit()
        flash("Event wurde erstellt.", "success")
        return redirect(url_for("events.list_events"))

    return render_template("events/form.html", form=form, title="Event erstellen")


@events_bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    form = EventForm(obj=event)
    if form.validate_on_submit():
        form.populate_obj(event)
        db.session.commit()
        flash("Event wurde aktualisiert.", "success")
        return redirect(url_for("events.list_events"))

    return render_template("events/form.html", form=form, title="Event bearbeiten")


@api_bp.route("/members")
@login_required
def api_members():
    members = Member.query.order_by(Member.id).all()
    return jsonify(
        [
            {
                "id": m.id,
                "first_name": m.first_name,
                "last_name": m.last_name,
                "email": m.email,
                "status": m.status,
                "role": m.role.name if m.role else None,
            }
            for m in members
        ]
    )


@api_bp.route("/events")
@login_required
def api_events():
    events = Event.query.order_by(Event.event_date).all()
    return jsonify(
        [
            {
                "id": e.id,
                "title": e.title,
                "description": e.description,
                "location": e.location,
                "event_date": e.event_date.isoformat(),
            }
            for e in events
        ]
    )
