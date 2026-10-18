from urllib.parse import urlparse

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import Listing, User
from .forms import ChangePasswordForm, LoginForm, ProfileForm, RegisterForm

auth_bp = Blueprint("auth", __name__)


def _safe_next(target):
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.netloc or parsed.scheme or not target.startswith("/"):
        return None
    return target


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if request.method == "GET" and not form.college.data:
        form.college.data = current_app.config["DEFAULT_COLLEGE"]
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            email=form.email.data.strip().lower(),
            course=form.course.data,
            year=form.year.data,
            college=form.college.data.strip(),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f"Welcome to UniSphere, {user.first_name}! Your account is ready.", "success")
        return redirect(url_for("main.index"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash("Incorrect email or password.", "danger")
            return render_template("auth/login.html", form=form), 401
        if not user.is_active:
            flash("This account has been deactivated.", "danger")
            return render_template("auth/login.html", form=form), 403
        login_user(user, remember=form.remember.data)
        session.permanent = form.remember.data
        flash(f"Welcome back, {user.first_name}!", "success")
        return redirect(_safe_next(request.args.get("next")) or url_for("main.index"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/profile")
@login_required
def profile():
    listings = (
        Listing.query.filter_by(seller_id=current_user.id).order_by(Listing.created_at.desc()).all()
    )
    available = sum(1 for l in listings if not l.is_sold)
    sold = len(listings) - available
    favourites_count = current_user.favourites.count()
    return render_template(
        "auth/profile.html",
        listings=listings,
        available_count=available,
        sold_count=sold,
        favourites_count=favourites_count,
    )


@auth_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data.strip()
        current_user.last_name = form.last_name.data.strip()
        current_user.course = form.course.data
        current_user.year = form.year.data
        current_user.college = form.college.data.strip()
        current_user.phone = (form.phone.data or "").strip() or None
        current_user.bio = (form.bio.data or "").strip() or None
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/edit_profile.html", form=form)


@auth_bp.route("/profile/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            form.current_password.errors.append("Current password is incorrect.")
        elif form.current_password.data == form.new_password.data:
            form.new_password.errors.append("New password must be different from the current one.")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password updated successfully.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("auth/change_password.html", form=form)


@auth_bp.route("/users/<int:user_id>")
def public_profile(user_id):
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        abort(404)
    listings = (
        Listing.query.filter_by(seller_id=user.id, status="available").order_by(Listing.created_at.desc()).all()
    )
    sold_count = Listing.query.filter_by(seller_id=user.id, status="sold").count()
    return render_template("auth/public_profile.html", user=user, listings=listings, sold_count=sold_count)
