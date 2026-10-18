from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..constants import CATEGORIES, CONDITIONS, SORT_OPTIONS
from ..extensions import db
from ..models import Conversation, Favourite, Listing, ListingImage
from ..utils import InvalidImage, delete_image_file, save_listing_image
from .forms import ListingForm

listings_bp = Blueprint("listings", __name__)


def _get_owned_listing_or_403(listing_id):
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        abort(404)
    if listing.seller_id != current_user.id:
        abort(403)
    return listing


def _parse_price(value):
    if value in (None, ""):
        return None
    try:
        price = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return price if price >= 0 else None


def _save_uploaded_images(listing, files):
    """Persist uploaded files. Returns list of error strings (empty if all fine)."""
    errors = []
    existing = len(listing.images)
    limit = current_app.config["MAX_IMAGES_PER_LISTING"]
    files = [f for f in files if f and f.filename]
    if existing + len(files) > limit:
        errors.append(f"You can upload at most {limit} images per listing.")
        return errors
    for idx, file in enumerate(files):
        try:
            filename = save_listing_image(file)
        except InvalidImage as e:
            errors.append(str(e))
            continue
        listing.images.append(ListingImage(filename=filename, position=existing + idx))
    return errors


@listings_bp.route("/browse")
def browse():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    condition = request.args.get("condition", "").strip()
    min_price = _parse_price(request.args.get("min_price"))
    max_price = _parse_price(request.args.get("max_price"))
    sort = request.args.get("sort", "newest")
    include_sold = request.args.get("include_sold") == "1"
    page = max(request.args.get("page", 1, type=int), 1)

    query = Listing.query
    if not include_sold:
        query = query.filter(Listing.status == "available")
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Listing.title.ilike(like), Listing.description.ilike(like), Listing.category.ilike(like)))
    if category and category in CATEGORIES:
        query = query.filter(Listing.category == category)
    if condition and condition in CONDITIONS:
        query = query.filter(Listing.condition == condition)
    if min_price is not None:
        query = query.filter(Listing.price >= min_price)
    if max_price is not None:
        query = query.filter(Listing.price <= max_price)

    if sort == "price_asc":
        query = query.order_by(Listing.price.asc(), Listing.created_at.desc())
    elif sort == "price_desc":
        query = query.order_by(Listing.price.desc(), Listing.created_at.desc())
    else:
        sort = "newest"
        query = query.order_by(Listing.created_at.desc())

    pagination = query.paginate(page=page, per_page=current_app.config["LISTINGS_PER_PAGE"], error_out=False)
    fav_ids = set()
    if current_user.is_authenticated and pagination.items:
        ids = [l.id for l in pagination.items]
        fav_ids = {
            f.listing_id
            for f in Favourite.query.filter(Favourite.user_id == current_user.id, Favourite.listing_id.in_(ids)).all()
        }

    active_filters = {
        "q": q,
        "category": category,
        "condition": condition,
        "min_price": request.args.get("min_price", ""),
        "max_price": request.args.get("max_price", ""),
        "sort": sort,
        "include_sold": "1" if include_sold else "",
    }
    return render_template(
        "listings/browse.html",
        pagination=pagination,
        listings=pagination.items,
        filters=active_filters,
        fav_ids=fav_ids,
        has_filters=any(v for k, v in active_filters.items() if k != "sort"),
    )


@listings_bp.route("/listings/<int:listing_id>")
def detail(listing_id):
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        abort(404)
    is_owner = current_user.is_authenticated and listing.seller_id == current_user.id
    is_fav = current_user.is_authenticated and current_user.has_favourited(listing.id)
    existing_conversation = None
    if current_user.is_authenticated and not is_owner:
        existing_conversation = Conversation.query.filter_by(listing_id=listing.id, buyer_id=current_user.id).first()
    similar = (
        Listing.query.filter(
            Listing.category == listing.category, Listing.id != listing.id, Listing.status == "available"
        )
        .order_by(Listing.created_at.desc())
        .limit(4)
        .all()
    )
    return render_template(
        "listings/detail.html",
        listing=listing,
        is_owner=is_owner,
        is_fav=is_fav,
        existing_conversation=existing_conversation,
        similar=similar,
    )


@listings_bp.route("/sell", methods=["GET", "POST"])
@login_required
def create():
    form = ListingForm()
    if request.method == "GET":
        form.college.data = current_user.college or current_app.config["DEFAULT_COLLEGE"]
    if form.validate_on_submit():
        files = [f for f in request.files.getlist("images") if f and f.filename]
        if not files:
            form.images.errors = list(form.images.errors) + ["Please upload at least one product image."]
            return render_template("listings/form.html", form=form, listing=None), 400
        listing = Listing(
            seller=current_user,
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            price=form.price.data,
            category=form.category.data,
            condition=form.condition.data,
            college=form.college.data.strip(),
            location=(form.location.data or "").strip() or None,
        )
        errors = _save_uploaded_images(listing, files)
        if errors:
            for img in listing.images:
                delete_image_file(img.filename)
            form.images.errors = list(form.images.errors) + errors
            return render_template("listings/form.html", form=form, listing=None), 400
        db.session.add(listing)
        db.session.commit()
        flash("Your listing is live!", "success")
        return redirect(url_for("listings.detail", listing_id=listing.id))
    status = 400 if request.method == "POST" else 200
    return render_template("listings/form.html", form=form, listing=None), status


@listings_bp.route("/listings/<int:listing_id>/edit", methods=["GET", "POST"])
@login_required
def edit(listing_id):
    listing = _get_owned_listing_or_403(listing_id)
    form = ListingForm(obj=listing)
    form.submit.label.text = "Save changes"
    if form.validate_on_submit():
        remove_ids = set(request.form.getlist("remove_images", type=int))
        remaining = [img for img in listing.images if img.id not in remove_ids]
        new_files = [f for f in request.files.getlist("images") if f and f.filename]
        if not remaining and not new_files:
            form.images.errors = list(form.images.errors) + ["A listing needs at least one image."]
            return render_template("listings/form.html", form=form, listing=listing), 400

        removed = [img for img in listing.images if img.id in remove_ids]
        for img in removed:
            listing.images.remove(img)
            db.session.delete(img)
        for pos, img in enumerate(listing.images):
            img.position = pos

        errors = _save_uploaded_images(listing, new_files)
        if errors:
            db.session.rollback()
            form.images.errors = list(form.images.errors) + errors
            return render_template("listings/form.html", form=form, listing=listing), 400

        listing.title = form.title.data.strip()
        listing.description = form.description.data.strip()
        listing.price = form.price.data
        listing.category = form.category.data
        listing.condition = form.condition.data
        listing.college = form.college.data.strip()
        listing.location = (form.location.data or "").strip() or None
        db.session.commit()
        for img in removed:
            delete_image_file(img.filename)
        flash("Listing updated.", "success")
        return redirect(url_for("listings.detail", listing_id=listing.id))
    status = 400 if request.method == "POST" else 200
    return render_template("listings/form.html", form=form, listing=listing), status


@listings_bp.route("/listings/<int:listing_id>/delete", methods=["POST"])
@login_required
def delete(listing_id):
    listing = _get_owned_listing_or_403(listing_id)
    filenames = [img.filename for img in listing.images]
    db.session.delete(listing)
    db.session.commit()
    for name in filenames:
        delete_image_file(name)
    flash("Listing deleted.", "info")
    return redirect(url_for("listings.my_listings"))


@listings_bp.route("/listings/<int:listing_id>/status", methods=["POST"])
@login_required
def toggle_status(listing_id):
    listing = _get_owned_listing_or_403(listing_id)
    target = request.form.get("status")
    if target not in ("available", "sold"):
        abort(400)
    listing.status = target
    listing.sold_at = datetime.utcnow() if target == "sold" else None
    db.session.commit()
    flash("Marked as sold. Buyers will see it's no longer available." if target == "sold" else "Listing is available again.", "success")
    return redirect(request.referrer or url_for("listings.detail", listing_id=listing.id))


@listings_bp.route("/my-listings")
@login_required
def my_listings():
    status = request.args.get("status", "all")
    query = Listing.query.filter_by(seller_id=current_user.id)
    if status in ("available", "sold"):
        query = query.filter_by(status=status)
    else:
        status = "all"
    listings = query.order_by(Listing.created_at.desc()).all()
    return render_template("listings/my_listings.html", listings=listings, status=status)
